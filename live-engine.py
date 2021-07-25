import asyncio
from binance import Client, AsyncClient, BinanceSocketManager
from datetime import datetime, timedelta
import json
from Ikarus import binance_wrapper, live_strategies, backtest_strategies, notifications, analyzers, observers, mongo_utils, objects
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

def setup_logger(_log_lvl):
    global logger
    log_filename = 'log/test-ikarus-app.log'
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


async def update_ltos(lto_dict, orders_dict, data_dict):
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

    for tradeid in lto_dict.keys():
        pair = lto_dict[tradeid]['pair']

        # TODO: '15m' should not be hardcoded
        last_kline = data_dict[pair]['15m'].tail(1)
        # 1.2.1: Check trades and update status
        # pair_klines_dict = pair_klines
        # TODO NEXT: Continue to integrate this section
        # TODO: A mocl might be needed to simulate live orders
        if lto_dict[tradeid]['status'] == 'open_enter':
            # NOTE: There is 2 method to enter: 'limit' and 'market'. Since market executed directly, it is not expected to have market at this stage
            if 'limit' in lto_dict[tradeid]['enter'].keys():

                # Check if the open enter trade is filled else if the trade is expired
                if orders_dict[tradeid]['status'] == 'FILLED':

                    # NOTE: Since this is testing, no dust created, perfect conversion
                    # TODO: If the enter is successfull then the exit order should be placed. This is only required in DEPLOY
                    lto_dict[tradeid]['status'] = 'waiting_exit'
                    lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])
                    lto_dict[tradeid]['result']['enter']['type'] = 'limit'
                    lto_dict[tradeid]['result']['enter']['time'] = bson.Int64(last_kline.index.values)
                    lto_dict[tradeid]['result']['enter']['price'] = orders_dict[tradeid]['price']
                    lto_dict[tradeid]['result']['enter']['quantity'] = orders_dict[tradeid]['executedQty']
                    lto_dict[tradeid]['result']['enter']['amount'] = orders_dict[tradeid]['price'] * orders_dict[tradeid]['executedQty']

                elif int(lto_dict[tradeid]['enter']['limit']['expire']) <= bson.Int64(last_kline.index.values):
                    # Report the expiration to algorithm
                    lto_dict[tradeid]['status'] = 'enter_expire'
                    lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])

            else:
                # TODO: Internal Error
                pass

        elif lto_dict[tradeid]['status'] == 'partially_closed_enter':
            # Ignore for the tests
            pass

        elif lto_dict[tradeid]['status'] == 'open_exit':

            if 'limit' in lto_dict[tradeid]['exit'].keys():

                # Check if the open sell trade is filled or stoploss is taken
                if orders_dict[tradeid]['status'] == 'FILLED':

                    lto_dict[tradeid]['status'] = 'closed'
                    lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])
                    lto_dict[tradeid]['result']['cause'] = 'closed'

                    lto_dict[tradeid]['result']['exit']['type'] = 'limit'
                    lto_dict[tradeid]['result']['exit']['time'] = bson.Int64(last_kline.index.values)
                    lto_dict[tradeid]['result']['exit']['price'] = orders_dict[tradeid]['price']
                    lto_dict[tradeid]['result']['exit']['amount'] = orders_dict[tradeid]['executedQty']
                    lto_dict[tradeid]['result']['exit']['quantity'] = orders_dict[tradeid]['price'] * orders_dict[tradeid]['executedQty']

                    lto_dict[tradeid]['result']['profit'] = lto_dict[tradeid]['result']['exit']['amount'] - lto_dict[tradeid]['result']['enter']['amount']
                    lto_dict[tradeid]['result']['liveTime'] = lto_dict[tradeid]['result']['exit']['time'] - lto_dict[tradeid]['result']['enter']['time']


                elif int(lto_dict[tradeid]['exit']['limit']['expire']) <= bson.Int64(last_kline.index.values):
                    lto_dict[tradeid]['status'] = 'exit_expire'
                    lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])
                    
                else:
                    pass

            elif 'oco' in lto_dict[tradeid]['exit'].keys():

                if orders_dict[tradeid]['status'] == 'EXPIRED':

                    stoploss_tradeid = lto_dict[tradeid]['exit']['stoploss_tradeid']

                    # Stop Loss takens
                    lto_dict[tradeid]['status'] = 'closed'
                    lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])
                    lto_dict[tradeid]['result']['cause'] = 'closed'
                    lto_dict[tradeid]['result']['exit']['type'] = 'oco_stoploss'
                    lto_dict[tradeid]['result']['exit']['time'] = bson.Int64(last_kline.index.values)
                    lto_dict[tradeid]['result']['exit']['price'] = orders_dict[stoploss_tradeid]['price']
                    lto_dict[tradeid]['result']['exit']['quantity'] = orders_dict[stoploss_tradeid]['executedQty']
                    lto_dict[tradeid]['result']['exit']['amount'] = orders_dict[stoploss_tradeid]['price'] * orders_dict[stoploss_tradeid]['executedQty']

                    lto_dict[tradeid]['result']['profit'] = lto_dict[tradeid]['result']['exit']['amount'] - lto_dict[tradeid]['result']['enter']['amount']
                    lto_dict[tradeid]['result']['liveTime'] = lto_dict[tradeid]['result']['exit']['time'] - lto_dict[tradeid]['result']['enter']['time']
                
                elif orders_dict[tradeid]['status'] == 'FILLED':

                    # Limit taken
                    lto_dict[tradeid]['status'] = 'closed'
                    lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])
                    lto_dict[tradeid]['result']['cause'] = 'closed'

                    lto_dict[tradeid]['result']['exit']['type'] = 'oco_limit'
                    lto_dict[tradeid]['result']['exit']['time'] = bson.Int64(last_kline.index.values)
                    lto_dict[tradeid]['result']['exit']['price'] = orders_dict[tradeid]['price']
                    lto_dict[tradeid]['result']['exit']['quantity'] = orders_dict[tradeid]['executedQty']
                    lto_dict[tradeid]['result']['exit']['amount'] = orders_dict[tradeid]['price'] * orders_dict[tradeid]['executedQty']


                    lto_dict[tradeid]['result']['profit'] = lto_dict[tradeid]['result']['exit']['amount'] - lto_dict[tradeid]['result']['enter']['amount']
                    lto_dict[tradeid]['result']['liveTime'] = lto_dict[tradeid]['result']['exit']['time'] - lto_dict[tradeid]['result']['enter']['time']

                elif int(lto_dict[tradeid]['exit']['oco']['expire']) <= bson.Int64(last_kline.index.values):
                    lto_dict[tradeid]['status'] = 'exit_expire'
                    lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])

                else:
                    pass

            else:
                # TODO: Internal Error
                pass
                
        elif lto_dict[tradeid]['status'] == 'partially_closed_exit':
            # Ignore for the tests
            pass

        else:
            # TODO: Internal Error
            pass

    return lto_dict


async def application(bwrapper, telbot):
    pair_list = config['data_input']['pairs']
    
    #################### Phase 1: Perform pre-calculation tasks ####################

    # 1.1 Get live trade objects (LTOs)
    lto_list = await mongocli.do_find('live-trades',{})
    lto_dict = dict()
    for lto in lto_list:
        lto_dict[lto['tradeid']] = lto

    # 1.2 Get datadict and orders
    pre_calc_1_coroutines = [ bwrapper.get_data_dict(pair_list, input_data_config),
                              bwrapper.get_lto_orders(lto_dict)]

    data_dict, orders = await asyncio.gather(*pre_calc_1_coroutines)

    # 1.3: Get df_balance, lto_dict, analysis_dict
    pre_calc_2_coroutines = [ bwrapper.get_current_balance(),
                              update_ltos(lto_dict, orders, data_dict),
                              analyzer.sample_analyzer(data_dict)]

    df_balance, lto_dict, analysis_dict = await asyncio.gather(*pre_calc_2_coroutines)

    #################### Phase 2: Perform calculation tasks ####################
    # TODO: Either create task for each coroutine or only await them.

    # NOTE: current_ts is the open time of the current live candle (open time)
    # NOTE: current_ts is equal to the beginning of the the current minute (assuming that a cycle will not take more than a minute)
    current_ts = int(time.time())   # Get the timestamp in gmt=0
    current_ts -= int(current_ts % 60) # Round the current_ts to backward (to the beginning of the current minute)
    trade_dict = await asyncio.create_task(strategy.run(analysis_dict, lto_dict, df_balance, current_ts))

    if len(trade_dict):
        exec_status = await asyncio.create_task(bwrapper.execute_decision(trade_dict))
        # TODO: |trade_obj life cycle|1|: Write trade dict to the "live-trades" (write for the first time)
        # TODO: Handle exec_status to do sth in case of failure (like sending notification)
        # await mongocli.insert_many("live-trades",trade_dict)

    
    # Phase 3: Perform post-calculation tasks
    logger.info('post-calculation phase started')
    observation_obj = await observer.sample_observer(df_balance)
    await mongocli.do_insert_one("observer",observation_obj.get())   

    logger.debug('Application ended')
    return True


async def main(period):
    global SYSTEM_STATUS, STATUS_TIMEOUT

    client = await AsyncClient.create(api_key=cred_info['Binance']['Production']['PUBLIC-KEY'],
                                      api_secret=cred_info['Binance']['Production']['SECRET-KEY'])

    # bm = BinanceSocketManager(client)
    bwrapper = binance_wrapper.BinanceWrapper(client, config)

    telbot = notifications.TelegramBot(cred_info['Telegram']['Token'], cred_info['Telegram']['ChatId'])
    while True:
        try:
            sys_stat = await asyncio.wait_for(client.get_system_status(), timeout=5)
            server_time = await client.get_server_time()
            # sys_stat ve server time gather() edilebilir

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
            '''
            # NOTE: The smallest time interval is 1 minute
            start_ts = int(server_time['serverTime']/1000)
            start_ts = start_ts - (start_ts % 60) + 61  # 1 minute 1 second ahead
            result = await asyncio.create_task(run_at(start_ts, application(bwrapper, client, telbot)))
            '''

            # NOTE: The logic below is for gathering data every 'period' seconds (Good for testing and not waiting)
            await asyncio.gather(
                #asyncio.sleep(period),
                application(bwrapper, telbot),
            )

        except Exception as e:
            if STATUS_TIMEOUT != 1:
                logger.error(str(e))
                STATUS_TIMEOUT = 1
                #telbot.send('Exception: STATUS_TIMEOUT')

    await client.close_connection()

if __name__ == "__main__":

    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    logger = logging.getLogger('app')
    mongocli = mongo_utils.MongoClient(config['mongodb']['host'], 
        config['mongodb']['port'], 
        config['tag'],
        clean=True)

    input_data_config = pd.DataFrame({
        "scale":config['data_input']['scale'],
        "length_str":config['data_input']['length_str'],
        "length_int":config['data_input']['length_int']})

    # Initialize and configure objects
    setup_logger(config['log-level'])

    # Setup initial objects
    observer = observers.Observer()
    analyzer = analyzers.Analyzer(config)
    strategy = backtest_strategies.OCOBackTest(config)

    logger.info("---------------------------------------------------------")
    logger.info("------------------- Engine Restarted --------------------")
    logger.info("---------------------------------------------------------")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(5))
    print("Completed")