import asyncio
from binance import Client, AsyncClient
from datetime import datetime, timedelta
import json
from Ikarus import binance_wrapper, algorithms, notifications, analyzers, observers, mongo_utils
import logging
from logging.handlers import TimedRotatingFileHandler
import pandas as pd
import sys
import numpy as np
from scripts import fplot as fp
import copy
import bson

credential_file = r'./test_credentials.json'
with open(credential_file, 'r') as cred_file:
    cred_info = json.load(cred_file)

# Global Variables
SYSTEM_STATUS = 0
STATUS_TIMEOUT = 0
test_time_scales = [Client.KLINE_INTERVAL_15MINUTE]
test_time_lengths_str = [96]
test_time_df = pd.DataFrame({"scale":test_time_scales, "length":test_time_lengths_str})
time_scale_mapping = dict(zip(test_time_scales, test_time_lengths_str))


def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()


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


async def get_closed_hto(df):
    # Read Database to get hist-trades and dump to a DataFrame
    hto_list = await mongocli.do_find('hist-trades',{'result.cause':'closed'})
    hto_closed = []
    for hto in hto_list:
        if 'oco' in hto['exit'].keys():  plannedExitType = 'oco'; plannedPriceName = 'limitPrice'
        elif 'limit' in hto['exit'].keys(): plannedExitType = 'limit'; plannedPriceName = 'price'

        hto_dict = {
            "_id": hto['_id'],
            "tradeid": hto['tradeid'],
            "enterTime": hto['result']['enter']['time'],
            "enterPrice": hto['enter']['limit']['price'],
            "exitTime": hto['result']['exit']['time'],
            "exitPrice": hto['exit'][plannedExitType][plannedPriceName],
            "sellPrice": hto['result']['exit']['price']
        }
        hto_closed.append(hto_dict)

    df = pd.DataFrame(hto_closed)
    return df


async def get_enter_expire_hto(df):
    # Read Database to get hist-trades and dump to a DataFrame
    hto_list = await mongocli.do_find('hist-trades',{'result.cause':'enter_expire'})
    hto_ent_exp_list = []
    for hto in hto_list:
        # NOTE: HIGH: We dont know it the exit type is limit or not
        hto_dict = {
            "_id": hto['_id'],
            "tradeid": hto['tradeid'],
            "enterExpire": hto['enter']['limit']['expire'],
            "enterPrice": hto['enter']['limit']['price'],
        }
        hto_ent_exp_list.append(hto_dict)

    df = pd.DataFrame(hto_ent_exp_list)
    return df


async def get_exit_expire_hto(df):
    # Read Database to get hist-trades and dump to a DataFrame
    
    hto_list = await mongocli.do_find('hist-trades',{'result.cause':'exit_expire'})
    hto_closed_list = []
    for hto in hto_list:
        if 'oco' in hto['exit'].keys():  plannedExitType = 'oco'; plannedPriceName = 'limitPrice'
        elif 'limit' in hto['exit'].keys(): plannedExitType = 'limit'; plannedPriceName = 'price'

        hto_dict = {
            "_id": hto['_id'],
            "tradeid": hto['tradeid'],
            "enterTime": hto['result']['enter']['time'],
            "enterPrice": hto['enter']['limit']['price'],
            "exitPrice": hto['exit'][plannedExitType][plannedPriceName],
            "sellPrice": hto['result']['exit']['price'],
            "exitExpire": hto['exit'][plannedExitType]['expire']
        }
        hto_closed_list.append(hto_dict)
    df = pd.DataFrame(hto_closed_list)

    return df


async def evaluate_stats():

    # Evaluate Statistics
    logger.info("---------------------------------------------------------")
    logger.info("---------------------- Statistics -----------------------")
    logger.info("---------------------------------------------------------")

    logger.info('Total enter_expire trades: {}'.format(await mongocli.count("hist-trades", {'result.cause':'enter_expire'})))
    logger.info('Total exit_expire trades: {}'.format(await mongocli.count("hist-trades", {'result.cause':'exit_expire'})))
    logger.info('Total closed trades: {}'.format(await mongocli.count("hist-trades", {'result.cause':'closed'})))
    
    exit_expire_pipe = [
        {"$match":{"result.cause":{"$eq":"exit_expire"}}},
        {"$group": {"_id": '', "sum": {"$sum": '$result.profit'}}},
    ]
    exit_expire_profit = await mongocli.do_find("hist-trades", exit_expire_pipe)
    logger.info('hist-trades.result.profit: exit_expire : {}'.format(exit_expire_profit['sum']))
    
    closed_pipe = [
        {"$match":{"result.cause":{"$eq":"closed"}}},
        {"$group": {"_id": '', "sum": {"$sum": '$result.profit'}}},
    ]
    closed_profit = await mongocli.do_find("hist-trades", closed_pipe)
    logger.info('hist-trades.result.profit: closed : {}'.format(closed_profit['sum']))

    last_balance = await mongocli.get_last_doc("observer")
    for balance in last_balance['balances']:
        if balance['asset'] == 'USDT':
            usdt_balance = balance['total']
            break
    logger.info('Final equity : {}'.format(usdt_balance))

    pass


async def write_updated_ltos_to_db(lto_dict, lto_dict_original):

    for pair, lto in lto_dict.items():
        # NOTE: Instead of doing update and then delete, I prefered the doing them in one iteration of objects due to latency concerns

        # If there is no change in the status, skip the current lto and continue to iterate
        if lto_dict_original[pair]['status'] == lto_dict[pair]['status']:
            continue

        # If the status is closed then, it should be inserted to [hist-trades] and deleted from the [live-trades]
        if lto['status'] == 'closed':
            # This if statement combines the "update the [live-trades]" and "delete the closed [live-trades]"
            result_insert = await mongocli.do_insert_one("hist-trades",lto)
            result_remove = await mongocli.do_delete_many("live-trades",{"_id":lto['_id']}) # "do_delete_many" does not hurt, since the _id is unique

        # If the status is open_exit then, previously it was either "open_enter" or "partially_closed_enter"
        # NOTE: Manual trade option is omitted, needs to be added
        elif lto['status'] == 'open_exit':
            result_update = await mongocli.do_update( 
                "live-trades",
                {'_id': lto['_id']},
                {'$set': {'status': lto['status'], 'result.enter':lto['result']['enter'] }})

        # NOTE: These two below are not applicable
        elif lto['status'] == 'partially_closed_enter':
            pass
        elif lto['status'] == 'partially_closed_exit':
            pass
        else:
            pass


async def update_ltos(lto_dict, data_dict, current_ts, df_balance):
    """
    Args:
        lto_dict (dict): will be updated (status, result, exit sections)
        data_dict (dict): used for getting the candle to see if trade status needs to change
        current_ts (ts): used for info sections of ltos
        df_balance (pd.DataFrame): When a lto go from 'open_exit' to 'closed' or 'open_enter' to 'open_exit'
        it needs to be updated in terms of 'free' and 'locked'
                                                        
        Broker Logic:
        for each lto
            1. open_enter
                a. limit
                    i. buy
                    ii. expire
            2. partially_closed_enter
                -
            3. open_exit
                a. limit
                    i. sell
                    ii. expire
                b. oco
                    i. sell
                    ii. stoploss
                    iii. expire
            4. partially_closed_exit
            -

    Returns:
        dict: lto_dict
    """

    for pair in set(lto_dict.keys()) & set(data_dict.keys()):
        pair_klines_dict = data_dict[pair]

        # 1.2.1: Check trades and update status
        # pair_klines_dict = pair_klines
        last_kline = pair_klines_dict['15m'].tail(1)

        if lto_dict[pair]['status'] == 'open_enter':
            # NOTE: There is 2 method to enter: 'limit' and 'market'. Since market executed directly, it is not expected to have market at this stage
            if 'limit' in lto_dict[pair]['enter'].keys():

                # Check if the open enter trade is filled else if the trade is expired
                if float(last_kline['low']) < lto_dict[pair]['enter']['limit']['price']:

                    # NOTE: Since this is testing, no dust created, perfect conversion
                    # TODO: If the enter is successfull then the exit order should be placed. This is only required in DEPLOY
                    lto_dict[pair]['status'] = 'waiting_exit'
                    lto_dict[pair]['result']['enter']['type'] = 'limit'
                    lto_dict[pair]['result']['enter']['time'] = bson.Int64(last_kline.index.values)
                    lto_dict[pair]['result']['enter']['price'] = lto_dict[pair]['enter']['limit']['price']
                    lto_dict[pair]['result']['enter']['amount'] = lto_dict[pair]['enter']['limit']['amount']
                    lto_dict[pair]['result']['enter']['quantity'] = lto_dict[pair]['enter']['limit']['quantity']

                    # Remove the bought amount from the 'locked' and 'ref_balance' columns
                    df_balance.loc['USDT', 'locked'] -= lto_dict[pair]['enter']['limit']['amount']
                    df_balance.loc['USDT', 'ref_balance'] = df_balance.loc['USDT', 'locked'] +  df_balance.loc['USDT', 'free']
                    # TODO sync the ref_balance and total
                    # Update df_balance: add the quantity to the base_cur or create a row for base_cur
                    base_cur = pair.replace('USDT','')
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
                    df_balance.loc['USDT','free'] += lto_dict[pair]['result']['exit']['amount']
                    df_balance.loc['USDT','total'] = df_balance.loc['USDT','free'] + df_balance.loc['USDT','locked']
                    df_balance.loc['USDT','ref_balance'] = df_balance.loc['USDT','total']
                    # NOTE: For the quote_currency total and the ref_balance is the same

                elif int(lto_dict[pair]['exit']['limit']['expire']) <= bson.Int64(last_kline.index.values):
                    lto_dict[pair]['status'] = 'exit_expire'
                    
                else:
                    pass

            elif 'oco' in lto_dict[pair]['exit'].keys():
                # NOTE: Think about the worst case and check the stop loss first.

                if float(last_kline['low']) < lto_dict[pair]['exit']['oco']['stopPrice']:
                    # Stop Loss takens
                    lto_dict[pair]['status'] = 'closed'
                    lto_dict[pair]['result']['cause'] = 'closed'
                    # TODO: NEXT: This looks closed but actually oco_Stoploss taken, so visualization should consider the type instead of cause maybe
                    lto_dict[pair]['result']['exit']['type'] = 'oco_stoploss'
                    lto_dict[pair]['result']['exit']['time'] = bson.Int64(last_kline.index.values)
                    lto_dict[pair]['result']['exit']['price'] = lto_dict[pair]['exit']['oco']['stopLimitPrice']
                    lto_dict[pair]['result']['exit']['amount'] = lto_dict[pair]['exit']['oco']['amount']
                    lto_dict[pair]['result']['exit']['quantity'] = lto_dict[pair]['exit']['oco']['quantity']

                    lto_dict[pair]['result']['profit'] = lto_dict[pair]['result']['exit']['amount'] - lto_dict[pair]['result']['enter']['amount']
                    lto_dict[pair]['result']['liveTime'] = lto_dict[pair]['result']['exit']['time'] - lto_dict[pair]['result']['enter']['time']

                    # Update df_balance: # Update df_balance: write the amount of the exit
                    # TODO: Gather up all the df_balance sections and put them in a function
                    df_balance.loc['USDT','free'] += lto_dict[pair]['result']['exit']['amount']
                    df_balance.loc['USDT','total'] = df_balance.loc['USDT','free'] + df_balance.loc['USDT','locked']
                    df_balance.loc['USDT','ref_balance'] = df_balance.loc['USDT','total']
                    pass
                
                elif float(last_kline['high']) > lto_dict[pair]['exit']['oco']['limitPrice']:
                    # Limit taken

                    lto_dict[pair]['status'] = 'closed'
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
                    df_balance.loc['USDT','free'] += lto_dict[pair]['result']['exit']['amount']
                    df_balance.loc['USDT','total'] = df_balance.loc['USDT','free'] + df_balance.loc['USDT','locked']
                    df_balance.loc['USDT','ref_balance'] = df_balance.loc['USDT','total']
                    # NOTE: For the quote_currency total and the ref_balance is the same
                    pass

                elif int(lto_dict[pair]['exit']['oco']['expire']) <= bson.Int64(last_kline.index.values):
                    lto_dict[pair]['status'] = 'exit_expire'

                else:
                    pass

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


async def application(bwrapper, pair_list, df_list):

    #################### Phase 1: Perform pre-calculation tasks ####################
    #current_ts = int(df_list[0].index[-1])
    
    # The close time of the last_kline + 1ms, corresponds to the open_tme of the future kline which is actually the kline we are in. 
    # If the execution cycle takes 2 second, then the order execution and the updates will be done
    # 2 second after the new kline started. But the analysis will be done based on the last closed kline
    current_ts = int(df_list[0]['close_time'].iloc[-1] + 1) 

    # 1.1 Get live trade objects (LTOs)
    lto_list = await mongocli.do_find('live-trades',{})

    lto_dict = dict()
    for lto in lto_list:
        lto_dict[lto['pair']] = lto

    lto_dict_original = copy.deepcopy(lto_dict)

    # 1.2 Get balance and datadict
    info = await mongocli.get_last_doc('observer',{})
    # NOTE:info given to the get_current_balance only for test-engine.py
    tasks_pre_calc = bwrapper.get_current_balance(info), bwrapper.get_data_dict(pair_list, test_time_df, df_list)
    df_balance, data_dict = await asyncio.gather(*tasks_pre_calc)

    # 1.3: Query the status of LTOs from the Broker
    # 1.4: Update the LTOs
    lto_dict = await update_ltos(lto_dict, data_dict, current_ts, df_balance)

    # TODO: Based on the updates on lto_dict, update the df_balance [CHECKJ]


    # NOTE: All the insert/delete/update operations can be handled after the 'execute_decision'
    #       No need to do so before the algorihm review the ongoing process and make a decision


    #################### Phase 2: Perform calculation tasks ####################
    analyzer, algorithm = analyzers.Analyzer(), algorithms.BackTestAlgorithm()

    # 2.1: Analyzer only provide the simplified informations, it does not make any decision
    analysis_dict = await asyncio.create_task(analyzer.sample_analyzer(data_dict))

    # 2.2: Algorithm is the only authority to make decision
    # NOTE: Algorithm may make a new decision about an lto (handling the exit_expire)
    #       In this case lto can be copied directly from lto_dict to the trade_dict and executed.
    #       Then lto record in MongoDB get updated. Deleted from the [live-trades] and writen the updated version to [hist-trades] 
    #       
    #       Possible cases to update an lto:
    #       - status: enter_expire
    #           - cancel: Delete the to from [live-trades], fill the 'result', write to the [hist-trades]
    #       - status:exit_expire
    #           - TODO: market_sell: Delete the to from [live-trades], fill the 'result', write to the [hist-trades]
    #           - extend the expire time: Update the to in [live-trades]
    #       - drawdown alert from analysis

    # NOTE: Execution of multiple algorithm is possible, if 'algorithm': 'sample_oco_algorithm' like items added to the to's
    trade_dict = await asyncio.create_task(algorithm.sample_algorithm(analysis_dict, lto_dict, df_balance, current_ts)) # Send the last timestamp index

    # 2.3: Execute the trade_dict if any
    if len(trade_dict) or len(lto_dict):
        # 2.3.1: Send tos to broker
        exec_status, df_balance, lto_dict = await asyncio.create_task(bwrapper.execute_decision(trade_dict, df_balance, lto_dict, data_dict))
        # TODO: Handle exec_status to do sth in case of failure (like sending notification)
        if len(trade_dict):
            # 2.3.2: Write trade_dict to [live-trades] (assume it is executed successfully)
            # NOTE: If a to contains market-exit then it should go to [hist-trades]
            result = await mongocli.do_insert_many("live-trades",trade_dict)
        

    #################### Phase 3: Perform post-calculation tasks ####################

    # 1.5: Write the LTOs to [live-trades] and [hist-trades]
    # TODO: Move the function after the new trade object execution
    await write_updated_ltos_to_db(lto_dict, lto_dict_original)

    # TODO: Remove 1.6 No need to delete
    # 1.6: Clean-up lto_dict from the "closed" ones
    for pair in lto_dict_original.keys():
        if lto_dict[pair]['status'] == 'closed':
            del lto_dict[pair]


    observation_obj = await observer.sample_observer(df_balance)

    await mongocli.do_insert_one("observer",observation_obj.get())   
    return trade_dict


async def main():

    # NOTE: Temporary hack for yesting without internet connection
    #client = await AsyncClient.create(api_key=cred_info['Binance']['Production']['PUBLIC-KEY'],
    #                                  api_secret=cred_info['Binance']['Production']['SECRET-KEY'])

    client = 'mock_client'

    bwrapper = binance_wrapper.TestBinanceWrapper(client, config['commission'])

    # Init the df_tickers to not to call binance API in each iteration
    binance_wrapper.TestBinanceWrapper.df_tickers = await bwrapper.get_all_tickers()

    # Initiate the cash in the [observer]
    observation_item = {
        'balances': config['balances']
    }
    await mongocli.do_insert_one("observer",observation_item)   

    # Get the pair_list
    pair_list = []

    # Get the df_csv_list to aggregate
    df_csv_list = []

    for file in config['files']:
        filename = file.split('\\')[-1]
        pair_list.append(filename.split('_')[0].upper())
        df = pd.read_csv(file)
        df = df.set_index(['open_time'])
        df_csv_list.append(df)

    #for 15m there exist 96 points
    # so start iterating from the 96 until len(df)
    #print(time_scale_mapping["15m"],len(df))

    total_len = len(df_csv_list[0])-time_scale_mapping["15m"]
    printProgressBar(0, total_len, prefix = 'Progress:', suffix = 'Complete', length = 50)
    for i in range(total_len):
        logger.info(f'Iteration {i}:')
        printProgressBar(i + 1, total_len, prefix = 'Progress:', suffix = 'Complete', length = 50)
        # Create the df_list
        df_list = []
        for df in df_csv_list:
            df_list.append(df.iloc[i:i+time_scale_mapping["15m"]])
        await application(bwrapper, pair_list, df_list)

    df_closed_hto = await get_closed_hto(df_csv_list[0])
    df_enter_expire = await get_enter_expire_hto(df_csv_list[0])
    df_exit_expire = await get_exit_expire_hto(df_csv_list[0])

    # TODO: Combine 3 call above

    # Dump df_csv_list[0] to a file for debug purposes
    #f = open('out','w'); f.write(df_csv_list[0].to_string()); f.close()

    # Evaluate the statistics
    await evaluate_stats()

    # Visualize the test session
    fp.buy_sell(df_csv_list[0], df_closed_hto, df_enter_expire, df_exit_expire)

if __name__ == '__main__':
    
    print(str(sys.argv[1]))
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    logger = logging.getLogger('app')
    mongocli = mongo_utils.MongoClient(config['mongodb']['host'], 
        config['mongodb']['port'], 
        config['tag'],
        clean=True)

    # Initialize and configure objects
    setup_logger(config['log-level'])
    observer = observers.Observer()

    logger.info("---------------------------------------------------------")
    logger.info("------------------- Engine Restarted --------------------")
    logger.info("---------------------------------------------------------")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    print(f"Test Session <{config['tag']}> completed")