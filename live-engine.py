import asyncio
from binance import AsyncClient
from datetime import datetime
import json
from Ikarus import binance_wrapper, live_strategies, notifications, analyzers, observers, mongo_utils, lto_manipulator
import logging
from logging.handlers import TimedRotatingFileHandler
import pandas as pd
import sys
import copy
import bson
import time

# Global Variables
SYSTEM_STATUS = 0
STATUS_TIMEOUT = 0

def generate_scales_in_minute(config_dict):
    scales_to_minute = {'m':1, 'h':60, 'd':3600, 'w':25200}  # Hardcoded scales in minute
    scales_in_minute = []
    for scale in config_dict['data_input']['scale']:
        scales_in_minute.append(int(scale[:-1]) * scales_to_minute[scale[-1]])

    config_dict['data_input']['scales_in_minute'] = scales_in_minute

    return config_dict

def setup_logger(_log_lvl):
    global logger
    log_filename = 'log/ikarus-app.log'
    logger = logging.getLogger('app')
    logger.setLevel(logging.DEBUG)

    rfh = TimedRotatingFileHandler(filename=log_filename,
                                   when='H',
                                   interval=1,
                                   backupCount=5)

    rfh.setLevel(_log_lvl)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('[{}] [{}] [{}] [{}]'.format('%(asctime)s','%(name)26s','%(levelname)8s', '%(message)s'))
    formatter.converter = time.gmtime # Use the UTC Time
    rfh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(rfh)
    logger.addHandler(ch)

    logger.info('logger has been set')


async def wait_until(dt):
    now = int(datetime.timestamp(datetime.now()))
    sleep_time = dt - now
    print("dt:{}, now:{}, sleeptime:{}".format(dt,now,sleep_time))
    await asyncio.sleep(dt - now)


async def run_at(dt, coro):
    await wait_until(dt)
    return await coro


async def write_updated_ltos_to_db(lto_list, lto_list_original):

    for lto in lto_list:

        # NOTE: Check for status change is removed since some internal changes might have been performed on status and needs to be reflected to history
        # If the status is closed then, it should be inserted to [hist-trades] and deleted from the [live-trades]
        if lto['status'] == 'closed':
            # This if statement combines the "update the [live-trades]" and "delete the closed [live-trades]"
            result_insert = await mongocli.do_insert_one("hist-trades",lto)
            result_remove = await mongocli.do_delete_many("live-trades",{"_id":lto['_id']}) # "do_delete_many" does not hurt, since the _id is unique

        # NOTE: Manual trade option is omitted, needs to be added
        elif lto['status'] == 'open_exit':
            # - The status might be changed from 'open_enter' or 'partially_closed_enter' to 'open_exit' (changes in result.enter and history)
            # - The open_exit might be expired and postponed with some other changes in 'exit' item (changes in exit and history)
            result_update = await mongocli.do_update( 
                "live-trades",
                {'_id': lto['_id']},
                {'$set': {'status': 
                        lto['status'],
                        'exit':lto['exit'],
                        'result.enter':lto['result']['enter'],
                        'history':lto['history'] 
                    }})
                
        elif lto['status'] == 'open_enter':
            # - 'open_enter' might be expired and postponed with some additional changes in 'enter' item (changes in enter and history)
            result_update = await mongocli.do_update( 
                "live-trades",
                {'_id': lto['_id']},
                {'$set': {'status': lto['status'], 'enter':lto['enter'], 'history':lto['history'] }})

        # NOTE: These two below are not applicable
        elif lto['status'] == 'partially_closed_enter':
            pass
        elif lto['status'] == 'partially_closed_exit':
            pass
        else:
            pass


async def update_ltos(lto_list, orders_dict, data_dict):
    """
    Args:
        lto_dict (dict): will be updated (status, result, exit sections)
        df_balance (pd.DataFrame): When a lto go from 'open_exit' to 'closed' or 'open_enter' to 'open_exit'
        it needs to be updated in terms of 'free' and 'locked'                                               

    Returns:
        dict: lto_dict
    """

    # NOTE: In broker, an OCO order actually 2 different orders. The solution might be:
    #       - Keep the limit order as the trade id.
    #       - If the limit_maker is FILLED then we are fine
    #       - If the limit_maker İS EXPIRED then read the tradeid of to oco_stoploss and do what needs to be done
    #       - If the limit_maker İS CANCELED they bot oco orders canceld and this is an external touch
    #       : Keep the limit_maker as the 'tradeid' of the lto and keep the oco_stoploss in that lto. If needed reach it.

    # NOTE: Each lto with enter/exit type 'limit' has 1 order in orders_dict. However, each OCO exit has 2 orders in orders dict.
    #       len(orders_dict) >= len(lto_dict)

    # NOTE: Expiration: Normally bson.Int64(last_kline.index.values): denotes the 'open_time' of last closed kline.
    #       However, in live-trading the last kline is the newly opened kline. Keep that in mind.

    # TODO: NEXT: Find a way to create more meaningfull erro messages
    for i in range(len(lto_list)):
        pair = lto_list[i]['pair']

        assert len(data_dict[pair].keys()) == 1, "Multiple time scale is not supported"
        scale = list(data_dict[pair].keys())[0]
        #new_candle_open_time = bson.Int64(data_dict[pair][scale].tail(1).index.values)  # current_candle open_time
        last_closed_candle_open_time = bson.Int64(data_dict[pair][scale].tail(2).index.values[0])  # current_candle open_time
        # NOTE: last_closed_candle_open_time is used because for the anything that happens: it happend in the last closed kline

        # 1.2.1: Check trades and update status

        # TODO: A mock might be needed to simulate live orders
        if lto_list[i]['status'] == 'open_enter':
            # NOTE: There is 2 method to enter: 'limit' and 'market'. Since market executed directly, it is not expected to have market at this stage
            if 'limit' in lto_list[i]['enter'].keys():
                
                enter_orderId = lto_list[i]['enter']['limit']['orderId'] # Get the orderId of the enter module
                # Check if the open enter trade is filled else if the trade is expired
                if orders_dict[enter_orderId]['status'] == 'FILLED':

                    # TODO: If the enter is successfull then the exit order should be placed. This is only required in DEPLOY
                    lto_list[i]['status'] = 'waiting_exit'
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['enter']['type'] = 'limit'
                    lto_list[i]['result']['enter']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['enter']['price'] = float(orders_dict[enter_orderId]['price'])
                    lto_list[i]['result']['enter']['quantity'] = float(orders_dict[enter_orderId]['executedQty'])
                    lto_list[i]['result']['enter']['amount'] = float(lto_list[i]['result']['enter']['price'] * lto_list[i]['result']['enter']['quantity'])

                elif int(lto_list[i]['enter']['limit']['expire']) <= last_closed_candle_open_time:
                    # Report the expiration to algorithm
                    lto_list[i]['status'] = 'enter_expire'
                    lto_list[i]['history'].append(lto_list[i]['status'])

            else:
                # TODO: Internal Error
                pass

        elif lto_list[i]['status'] == 'partially_closed_enter':
            # Ignore for the tests
            pass

        elif lto_list[i]['status'] == 'open_exit':

            if 'limit' in lto_list[i]['exit'].keys():
                exit_orderId = lto_list[i]['exit']['limit']['orderId'] # Get the orderId of the enter module
                # Check if the open sell trade is filled or stoploss is taken
                if orders_dict[exit_orderId]['status'] == 'FILLED':

                    lto_list[i]['status'] = 'closed'
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['cause'] = 'closed'

                    lto_list[i]['result']['exit']['type'] = 'limit'
                    lto_list[i]['result']['exit']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['exit']['price'] = float(orders_dict[exit_orderId]['price'])
                    lto_list[i]['result']['exit']['price'] = float(orders_dict[exit_orderId]['executedQty'])
                    lto_list[i]['result']['exit']['amount'] = float(lto_list[i]['result']['exit']['price'] * lto_list[i]['result']['exit']['price'])

                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] - lto_list[i]['result']['enter']['amount']
                    lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']


                elif int(lto_list[i]['exit']['limit']['expire']) <= last_closed_candle_open_time:
                    lto_list[i]['status'] = 'exit_expire'
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    
                else:
                    pass

            elif 'oco' in lto_list[i]['exit'].keys():
                oco_limit_orderId = lto_list[i]['exit']['oco']['orderId'] # Get the orderId of the enter module
                oco_stopLoss_orderId = lto_list[i]['exit']['oco']['stopLoss_orderId'] # Get the orderId of the enter module

                if orders_dict[oco_limit_orderId]['status'] == 'EXPIRED':

                    # Stop Loss takens
                    lto_list[i]['status'] = 'closed'
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['cause'] = 'closed'
                    lto_list[i]['result']['exit']['type'] = 'oco_stoploss'
                    lto_list[i]['result']['exit']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['exit']['price'] = float(orders_dict[oco_stopLoss_orderId]['price'])
                    lto_list[i]['result']['exit']['quantity'] = float(orders_dict[oco_stopLoss_orderId]['executedQty'])
                    lto_list[i]['result']['exit']['amount'] = float(lto_list[i]['result']['exit']['price'] * lto_list[i]['result']['exit']['quantity'])

                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] - lto_list[i]['result']['enter']['amount']
                    lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']
                
                elif orders_dict[oco_limit_orderId]['status'] == 'FILLED':

                    # Limit taken
                    lto_list[i]['status'] = 'closed'
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['cause'] = 'closed'

                    lto_list[i]['result']['exit']['type'] = 'oco_limit'
                    lto_list[i]['result']['exit']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['exit']['price'] = float(orders_dict[oco_limit_orderId]['price'])
                    lto_list[i]['result']['exit']['quantity'] = float(orders_dict[oco_limit_orderId]['executedQty'])
                    lto_list[i]['result']['exit']['amount'] = float(lto_list[i]['result']['exit']['price'] * lto_list[i]['result']['exit']['quantity'])


                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] - lto_list[i]['result']['enter']['amount']
                    lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']

                elif int(lto_list[i]['exit']['oco']['expire']) <= last_closed_candle_open_time:
                    lto_list[i]['status'] = 'exit_expire'
                    lto_list[i]['history'].append(lto_list[i]['status'])

                else:
                    pass

            else:
                # TODO: Internal Error
                pass
                
        elif lto_list[i]['status'] == 'partially_closed_exit':
            # Ignore for the tests
            pass

        else:
            # TODO: Internal Error
            pass

    return lto_list


async def application(bwrapper, telbot):
    pair_list = config['data_input']['pairs']
    
    #################### Phase 1: Perform pre-calculation tasks ####################
    logger.debug('Phase 1 started')
    # 1.1 Get live trade objects (LTOs)
    lto_list = await mongocli.do_find('live-trades',{})

    lto_list_original = copy.deepcopy(lto_list)

    # 1.2 Get datadict and orders
    pre_calc_1_coroutines = [ bwrapper.get_data_dict(pair_list, input_data_config),
                              bwrapper.get_lto_orders(lto_list)]

    data_dict, orders = await asyncio.gather(*pre_calc_1_coroutines)

    # NOTE: Only works once
    if len(lto_list):
        orders = await lto_manipulator.change_order_to_filled(lto_list[0], orders)

    # 1.3: Get df_balance, lto_dict, analysis_dict
    pre_calc_2_coroutines = [ bwrapper.get_current_balance(),
                              update_ltos(lto_list, orders, data_dict),
                              analyzer.sample_analyzer(data_dict)]

    df_balance, lto_list, analysis_dict = await asyncio.gather(*pre_calc_2_coroutines)

    #################### Phase 2: Perform calculation tasks ####################
    logger.debug('Phase 2 started')

    # NOTE: current_ts is the open time of the current live candle (open time)
    # NOTE: current_ts is equal to the beginning of the the current minute (assuming that a cycle will not take more than a minute)
    current_ts = int(time.time())       # Get the timestamp in gmt=0
    current_ts -= int(current_ts % 60)  # Round the current_ts to backward (to the beginning of the current minute)
    current_ts *= 1000                  # Make the resolution milisecond
    nto_list = await strategy.run(analysis_dict, lto_list, df_balance, current_ts)

    # 2.3: Execute LTOs and NTOs if any
    if len(nto_list) or len(lto_list):
        # 2.3.1: Execute the TOs
        nto_list, lto_list = await asyncio.create_task(bwrapper.execute_decision(nto_list, lto_list))
        # TODO: Handle exec_status to do sth in case of failure (like sending notification)

    
    #################### Phase 3: Perform post-calculation tasks ####################
    logger.debug('Phase 3 started')

    if len(nto_list):
        # 3.1: Write trade_dict to [live-trades] (assume it is executed successfully)
        await mongocli.do_insert_many("live-trades", nto_list)     

    # 3.2: Write the LTOs and NTOs to [live-trades] and [hist-trades]
    await write_updated_ltos_to_db(lto_list, lto_list_original)

    # 3.3: Get the observer

    # 3.3.1 Get df_balance
    df_balance = await bwrapper.get_current_balance()

    # 3.3.2 Insert df_balance to [observer]
    observation_obj = await observer.sample_observer(df_balance)
    await mongocli.do_insert_one("observer",observation_obj.get())

    return True


async def main(smallest_interval):
    global SYSTEM_STATUS, STATUS_TIMEOUT

    client = await AsyncClient.create(api_key=cred_info['Binance']['Production']['PUBLIC-KEY'],
                                      api_secret=cred_info['Binance']['Production']['SECRET-KEY'])

    strategy.symbol_info = await client.get_symbol_info(config['data_input']['pairs'][0]) # NOTE: Multiple pair not supported
    bwrapper = binance_wrapper.BinanceWrapper(client, config)
    telbot = notifications.TelegramBot(cred_info['Telegram']['Token'], cred_info['Telegram']['ChatId'])

    while True:
        try:
            sys_stat = await asyncio.wait_for(client.get_system_status(), timeout=5)
            server_time = await client.get_server_time()
            # sys_stat ve server time can be gathered
            logger.info(f'System time: {server_time["serverTime"]}')
            # Check system status
            if sys_stat['status'] != 0:
                if SYSTEM_STATUS != 1:
                    SYSTEM_STATUS = 1
                    #telbot.send('Exception: SYSTEM_STATUS')
                #await asyncio.sleep(period)
                # TODO: If status is not 0 than ping the server with a certain time-interval
                # TODO: NOTIFICATION: Send notification when the connection changed to up or down
                # TODO: LOG:
                continue
            else:
                SYSTEM_STATUS = 0

            STATUS_TIMEOUT = 0
            
            
            # NOTE: The smallest time interval is 1 minute
            start_ts = int(server_time['serverTime']/1000)
            # NOTE: The logic below, executes the app default per minute. This should be generalized
            start_ts = start_ts - (start_ts % 60) + smallest_interval*60 + 1  # (x minute) * (60 sec) + (1 second) ahead
            logger.info(f'Cycle start time: {start_ts}')
            result = await asyncio.create_task(run_at(start_ts, application(bwrapper, telbot)))
            
            '''
            # NOTE: The logic below is for gathering data every 'period' seconds (Good for testing and not waiting)
            await asyncio.gather(
                asyncio.sleep(10),
                application(bwrapper, telbot),
            )
            '''
        except Exception as e:
            if STATUS_TIMEOUT != 1:
                logger.error(str(e))
                STATUS_TIMEOUT = 1
                #telbot.send('Exception: STATUS_TIMEOUT')

    await client.close_connection()

if __name__ == "__main__":

    # TODO: A paper-testing script might be need to develop, live-trade viualization and reveal unseen bugs
    #       lto_update, bwrapper.execute sections can be directly taken from backtest-engine
    
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    logger = logging.getLogger('app')
    mongocli = mongo_utils.MongoClient(config['mongodb']['host'], 
        config['mongodb']['port'], 
        config['tag'],
        clean=True) # NOTE: Normally it is False

    input_data_config = pd.DataFrame({
        "scale":config['data_input']['scale'],
        "length_str":config['data_input']['length_str'],
        "length_int":config['data_input']['length_int']})

    # Initialize and configure objects
    setup_logger(config['log-level'])

    # Add scales_in_minute to the config to be used in strategy etc.
    config = generate_scales_in_minute(config)

    # Setup initial objects
    observer = observers.Observer()
    analyzer = analyzers.Analyzer(config)
    strategy = live_strategies.AlwaysEnter(config)

    logger.info("---------------------------------------------------------")
    logger.info("------------------- Engine Restarted --------------------")
    logger.info("---------------------------------------------------------")
    loop = asyncio.get_event_loop()

    loop.run_until_complete( main( min( config['data_input']['scales_in_minute'])))
    print("Completed")