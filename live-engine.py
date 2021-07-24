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

# Global Variables
SYSTEM_STATUS = 0
STATUS_TIMEOUT = 0
#test_time_scales = [Client.KLINE_INTERVAL_15MINUTE]
#test_time_lengths_str = ["1 week"]
#test_time_df = pd.DataFrame({"scale":test_time_scales, "length":test_time_lengths_str})

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


async def update_ltos(lto_dict, orders, df_balance):
    """
    Args:
        lto_dict (dict): will be updated (status, result, exit sections)
        df_balance (pd.DataFrame): When a lto go from 'open_exit' to 'closed' or 'open_enter' to 'open_exit'
        it needs to be updated in terms of 'free' and 'locked'                                               

    Returns:
        dict: lto_dict
    """

    # NOTE: 'orders' and 'lto_dict' should have 1 to 1 mapping. Normally it does not matter 
    #       if the iteration is over orders or 'lto_dict'. However, for the consistency, the
    #       iteration goes over lto_dict and the orders are checked based on the items in lto_dict

    for pair in lto_dict.keys():

        if lto_dict[pair]['status'] == 'open_enter':
            # NOTE: There is 2 method to enter: 'limit' and 'market'. Since market executed directly, it is not expected to have market at this stage
            if 'limit' in lto_dict[pair]['enter'].keys():

                orders
                # Check if the open enter trade is filled else if the trade is expired
                if float(last_kline['low']) < lto_dict[pair]['enter']['limit']['price']:

                    # NOTE: Since this is testing, no dust created, perfect conversion
                    # TODO: If the enter is successfull then the exit order should be placed. This is only required in DEPLOY
                    lto_dict[pair]['status'] = 'waiting_exit'
                    lto_dict[pair]['history'].append(lto_dict[pair]['status'])
                    lto_dict[pair]['result']['enter']['type'] = 'limit'
                    lto_dict[pair]['result']['enter']['time'] = bson.Int64(last_kline.index.values)
                    lto_dict[pair]['result']['enter']['price'] = lto_dict[pair]['enter']['limit']['price']
                    lto_dict[pair]['result']['enter']['amount'] = lto_dict[pair]['enter']['limit']['amount']
                    lto_dict[pair]['result']['enter']['quantity'] = lto_dict[pair]['enter']['limit']['quantity']

                    # Remove the bought amount from the 'locked' and 'ref_balance' columns
                    df_balance.loc[config['broker']['quote_currency'], 'locked'] -= lto_dict[pair]['enter']['limit']['amount']
                    df_balance.loc[config['broker']['quote_currency'], 'ref_balance'] = df_balance.loc[config['broker']['quote_currency'], 'locked'] +  df_balance.loc[config['broker']['quote_currency'], 'free']
                    # TODO sync the ref_balance and total
                    # Update df_balance: add the quantity to the base_cur or create a row for base_cur
                    base_cur = pair.replace(config['broker']['quote_currency'],'')
                    if pair in list(df_balance.index):
                        df_balance.loc[base_cur, 'locked' ] += lto_dict[pair]['result']['enter']['quantity']
                    else:
                        # Previously there was no base_currency, so we create a row for it
                        # free  locked    total      pair   price  ref_balance
                        df_balance.loc[base_cur] = [0.0, lto_dict[pair]['result']['enter']['quantity'], 0, pair, 0, 0]
                        df_balance.loc[base_cur, 'total'] = df_balance.loc[base_cur,'free'] + df_balance.loc[base_cur,'locked']
                        # NOTE: TEST: 'price' and 'ref_balance' is omitted #NOTE ADD total not the ref_balance for the base_cur

                elif int(lto_dict[pair]['enter']['limit']['expire']) <= bson.Int64(last_kline.index.values):
                    # Report the expiration to algorithm
                    lto_dict[pair]['status'] = 'enter_expire'
                    lto_dict[pair]['history'].append(lto_dict[pair]['status'])

            else:
                # TODO: Internal Error
                pass

        elif lto_dict[pair]['status'] == 'partially_closed_enter':
            # Ignore for the tests
            pass

        elif lto_dict[pair]['status'] == 'open_exit':

            if 'limit' in lto_dict[pair]['exit'].keys():

                # Check if the open sell trade is filled or stoploss is taken
                if float(last_kline['high']) > lto_dict[pair]['exit']['limit']['price']:

                    lto_dict[pair]['status'] = 'closed'
                    lto_dict[pair]['history'].append(lto_dict[pair]['status'])
                    lto_dict[pair]['result']['cause'] = 'closed'

                    lto_dict[pair]['result']['exit']['type'] = 'limit'
                    lto_dict[pair]['result']['exit']['time'] = bson.Int64(last_kline.index.values)
                    lto_dict[pair]['result']['exit']['price'] = lto_dict[pair]['exit']['limit']['price']
                    lto_dict[pair]['result']['exit']['amount'] = lto_dict[pair]['exit']['limit']['amount']
                    lto_dict[pair]['result']['exit']['quantity'] = lto_dict[pair]['exit']['limit']['quantity']

                    lto_dict[pair]['result']['profit'] = lto_dict[pair]['result']['exit']['amount'] - lto_dict[pair]['result']['enter']['amount']
                    lto_dict[pair]['result']['liveTime'] = lto_dict[pair]['result']['exit']['time'] - lto_dict[pair]['result']['enter']['time']

                    # Update df_balance: # Update df_balance: write the amount of the exit
                    # TODO: Gather up all the df_balance sections and put them in a function
                    df_balance.loc[config['broker']['quote_currency'],'free'] += lto_dict[pair]['result']['exit']['amount']
                    df_balance.loc[config['broker']['quote_currency'],'total'] = df_balance.loc[config['broker']['quote_currency'],'free'] + df_balance.loc[config['broker']['quote_currency'],'locked']
                    df_balance.loc[config['broker']['quote_currency'],'ref_balance'] = df_balance.loc[config['broker']['quote_currency'],'total']
                    # NOTE: For the quote_currency total and the ref_balance is the same

                elif int(lto_dict[pair]['exit']['limit']['expire']) <= bson.Int64(last_kline.index.values):
                    lto_dict[pair]['status'] = 'exit_expire'
                    lto_dict[pair]['history'].append(lto_dict[pair]['status'])
                    
                else:
                    pass

            elif 'oco' in lto_dict[pair]['exit'].keys():
                # NOTE: Think about the worst case and check the stop loss first.

                if float(last_kline['low']) < lto_dict[pair]['exit']['oco']['stopPrice']:
                    # Stop Loss takens
                    lto_dict[pair]['status'] = 'closed'
                    lto_dict[pair]['history'].append(lto_dict[pair]['status'])
                    lto_dict[pair]['result']['cause'] = 'closed'
                    lto_dict[pair]['result']['exit']['type'] = 'oco_stoploss'
                    lto_dict[pair]['result']['exit']['time'] = bson.Int64(last_kline.index.values)
                    lto_dict[pair]['result']['exit']['price'] = lto_dict[pair]['exit']['oco']['stopLimitPrice']
                    lto_dict[pair]['result']['exit']['amount'] = lto_dict[pair]['exit']['oco']['amount']
                    lto_dict[pair]['result']['exit']['quantity'] = lto_dict[pair]['exit']['oco']['quantity']

                    lto_dict[pair]['result']['profit'] = lto_dict[pair]['result']['exit']['amount'] - lto_dict[pair]['result']['enter']['amount']
                    lto_dict[pair]['result']['liveTime'] = lto_dict[pair]['result']['exit']['time'] - lto_dict[pair]['result']['enter']['time']

                    # Update df_balance: # Update df_balance: write the amount of the exit
                    # TODO: Gather up all the df_balance sections and put them in a function
                    df_balance.loc[config['broker']['quote_currency'],'free'] += lto_dict[pair]['result']['exit']['amount']
                    df_balance.loc[config['broker']['quote_currency'],'total'] = df_balance.loc[config['broker']['quote_currency'],'free'] + df_balance.loc[config['broker']['quote_currency'],'locked']
                    df_balance.loc[config['broker']['quote_currency'],'ref_balance'] = df_balance.loc[config['broker']['quote_currency'],'total']
                    pass
                
                elif float(last_kline['high']) > lto_dict[pair]['exit']['oco']['limitPrice']:
                    # Limit taken

                    lto_dict[pair]['status'] = 'closed'
                    lto_dict[pair]['history'].append(lto_dict[pair]['status'])
                    lto_dict[pair]['result']['cause'] = 'closed'

                    lto_dict[pair]['result']['exit']['type'] = 'oco_limit'
                    lto_dict[pair]['result']['exit']['time'] = bson.Int64(last_kline.index.values)
                    lto_dict[pair]['result']['exit']['price'] = lto_dict[pair]['exit']['oco']['limitPrice']
                    lto_dict[pair]['result']['exit']['amount'] = lto_dict[pair]['exit']['oco']['amount']
                    lto_dict[pair]['result']['exit']['quantity'] = lto_dict[pair]['exit']['oco']['quantity']

                    lto_dict[pair]['result']['profit'] = lto_dict[pair]['result']['exit']['amount'] - lto_dict[pair]['result']['enter']['amount']
                    lto_dict[pair]['result']['liveTime'] = lto_dict[pair]['result']['exit']['time'] - lto_dict[pair]['result']['enter']['time']

                    # Update df_balance: # Update df_balance: write the amount of the exit
                    # TODO: Gather up all the df_balance sections and put them in a function
                    df_balance.loc[config['broker']['quote_currency'],'free'] += lto_dict[pair]['result']['exit']['amount']
                    df_balance.loc[config['broker']['quote_currency'],'total'] = df_balance.loc[config['broker']['quote_currency'],'free'] + df_balance.loc[config['broker']['quote_currency'],'locked']
                    df_balance.loc[config['broker']['quote_currency'],'ref_balance'] = df_balance.loc[config['broker']['quote_currency'],'total']
                    # NOTE: For the quote_currency total and the ref_balance is the same
                    pass

                elif int(lto_dict[pair]['exit']['oco']['expire']) <= bson.Int64(last_kline.index.values):
                    lto_dict[pair]['status'] = 'exit_expire'
                    lto_dict[pair]['history'].append(lto_dict[pair]['status'])

                else:
                    pass

            else:
                # TODO: Internal Error
                pass
                
        elif lto_dict[pair]['status'] == 'partially_closed_exit':
            # Ignore for the tests
            pass

        else:
            # TODO: Internal Error
            pass

    return lto_dict


async def application(bwrapper, telbot):
    pair_list = config['data_input']['pairs']
    
    #################### Phase 1: Perform pre-calculation tasks ####################

    # TODO: |trade_obj life cycle|2|: Read active trades from the database col: "live-trades"
    #       - Check if the buy order is taken, then execute the sell order from the ["live-trades"]["Exit"]
    # TODO: |trade_obj life cycle|3|: Check order status from broker
    #       - Get the open trades from broker and keep them as they are (json)
    # TODO: |trade_obj life cycle|4|: Update database based on the changes in order status
    #       - Send closed orders to "hist-trades" from "live-trades"

    # 1.1 Get live trade objects (LTOs)
    lto_list = await mongocli.do_find('live-trades',{})
    lto_dict = dict()
    for lto in lto_list:
        lto_dict[lto['pair']] = lto
    lto_dict_original = copy.deepcopy(lto_dict)

    # 1.2 Get balance, datadict and orders
    pre_calc_coroutines = [ bwrapper.get_current_balance(), 
                            bwrapper.get_data_dict(pair_list, input_data_config),
                            bwrapper.get_lto_orders(lto_dict)]

    df_balance, data_dict, orders = await asyncio.gather(*pre_calc_coroutines)

    # 1.3: Update the LTOs
    lto_dict = await update_ltos(lto_dict, orders, df_balance)

    #################### Phase 2: Perform calculation tasks ####################
    # TODO: Either create task for each coroutine or only await them.

    # 2.1: Analyzer only provide the simplified informations, it does not make any decision
    analysis_dict = await asyncio.create_task(analyzer.sample_analyzer(data_dict))
    trade_dict = await asyncio.create_task(strategy.run(analysis_dict, lto_dict, df_balance, current_ts))

    if len(trade_dict):
        exec_status = await asyncio.create_task(bwrapper.execute_decision(trade_dict))
        # TODO: |trade_obj life cycle|1|: Write trade dict to the "live-trades" (write for the first time)
        # TODO: Handle exec_status to do sth in case of failure (like sending notification)
        # await mongocli.insert_many("live-trades",trade_dict)

    
    # Phase 3: Perform post-calculation tasks
    logger.info('post-calculation phase started')
    observation_obj = await observer.sample_observer(balance)
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