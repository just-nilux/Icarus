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


async def lto_update(lto_dict, df_list, current_ts):
    """
    Do updates in the lto_dict

    Args:
        lto_dict (dict): Dictionaries of trade-objects
        df_list ([type]): [description]
        current_ts (int): Current Timestamp

    Returns:
        lto_dict: updated lto_dict
    """
    return lto_dict


async def hto_decompose():
    hto_closed_list = await mongocli.do_find('hist-trades',{"result.cause":"closed"})

    hto_dict = dict()
    for hto in hto_closed_list:
        hto_dict = {
            "_id": hto['_id'],
            "enterTime": hto['enter']['enterTime'],
            "enterPrice": hto['enter']['limit']['price'],
            "exitTime": hto['exit']['exitTime'],
            "exitPrice": hto['exit']['limit']['price']
        }

    return pd.DataFrame(hto_dict)


async def get_closed_hto(df):
    # Read Database to get hist-trades and dump to a DataFrame
    hto_list = await mongocli.do_find('hist-trades',{'result.cause':'closed'})
    hto_closed_list = []
    for hto in hto_list:
        hto_dict = {
            "_id": hto['_id'],
            "tradeid": hto['tradeid'],
            "enterTime": hto['enter']['enterTime'],
            "enterPrice": hto['enter']['limit']['price'],
            "exitTime": hto['exit']['exitTime'],
            "exitPrice": hto['exit']['limit']['price'],
            "sellPrice": hto['result']['sellPrice']
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
                {'$set': {'status': lto['status'], 'enter.enterTime':lto['enter']['enterTime'] }})

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
                                                        

    Returns:
        dict: lto_dict
    """
    for pair in set(lto_dict.keys()) & set(data_dict.keys()):
        pair_klines = data_dict[pair]

        # There might be 2 group of open trades:
        # enter: 
        #       waiting for limit to fill
        #       or to be expired
        # exit: 
        #       waiting for limit to fill
        #       waiting for stopLoss to fill
        #       or to be expired

        # 1.2.1: Check trades and update status
        pair_klines_dict = pair_klines.get()
        last_kline = pair_klines_dict['15m'].tail(1)

        if lto_dict[pair]['status'] == 'open_enter':
            # NOTE: There is 2 method to enter: 'limit' and 'market'. If market item exist, limit is ignored

            # TODO: NEXT: Implement the following logic:
            '''
            if 'market' in lto_dict[pair]['enter'].keys():
                # TODO: Think where to execute market buy logic
            elif 'limit' in lto_dict[pair]['enter'].keys():
                # Perform limitbuy and expire logic
                pass
            else:
                #Error CASE
                pass
            '''
            # Check if the open enter trade is filled else if the trade is expired
            if float(last_kline['low']) < lto_dict[pair]['enter']['limit']['price']:
                # NOTE: Since this is testing, no dust created, perfect conversion
                lto_dict[pair]['status'] = 'open_exit'
                lto_dict[pair]['enter']['enterTime'] = bson.Int64(current_ts)

                # Remove the bought amount from the 'locked' and 'ref_balance' columns
                df_balance.loc['USDT', 'locked'] -= lto_dict[pair]['enter']['limit']['amount']
                df_balance.loc['USDT', 'ref_balance'] = df_balance.loc['USDT', 'locked'] +  df_balance.loc['USDT', 'free']
                # TODO sync the ref_balance and total
                # Update df_balance: add the quantity to the base_cur or create a row for base_cur
                base_cur = pair.replace('USDT','')
                if pair in list(df_balance.index):
                    # TODO: APP: we need to place a sell order immediatly
                    df_balance.loc[base_cur, 'locked' ] += lto_dict[pair]['enter']['limit']['quantity']
                else:
                    # Previously there was no base_currency, so we create a row for it
                    # free  locked    total      pair   price  ref_balance
                    df_balance.loc[base_cur] = [0.0, lto_dict[pair]['exit']['limit']['quantity'], 0, pair, 0, 0]
                    df_balance.loc[base_cur, 'total'] = df_balance.loc[base_cur,'free'] + df_balance.loc[base_cur,'locked']
                    # NOTE: TEST: 'price' and 'ref_balance' is omitted #NOTE ADD total not the ref_balance for the base_cur

            elif int(lto_dict[pair]['enter']['limit']['expire']) <= current_ts:
                lto_dict[pair]['status'] = 'closed'
                lto_dict[pair]['result']['cause'] = 'enter_expire'
                lto_dict[pair]['result']['closedTime'] = bson.Int64(current_ts)
                # NOTE: No liveTime or closedTime calculated since, the trade was never alive

                # Update df_balance: return the 'amount' of the enter
                df_balance.loc['USDT','free'] += lto_dict[pair]['enter']['limit']['amount']
                df_balance.loc['USDT','locked'] -= lto_dict[pair]['enter']['limit']['amount']

                pass

        elif lto_dict[pair]['status'] == 'partially_closed_enter':
            # Ignore for the tests
            pass
        elif lto_dict[pair]['status'] == 'open_exit':
            # TODO: In order to decide that the sell completed, check the quantity if exist( will be handled in the TODO below)
            #       df_balance needs to be updated in terms of 'free' and 'locked'
            #       This is just for testing purposes, might not be needed for it as well

            # Check if the open sell trade is filled or stoploss is taken
            if float(last_kline['high']) > lto_dict[pair]['exit']['limit']['price']:

                lto_dict[pair]['status'] = 'closed'
                lto_dict[pair]['exit']['exitTime'] = bson.Int64(current_ts)

                lto_dict[pair]['result']['cause'] = 'closed'
                lto_dict[pair]['result']['closedTime'] = bson.Int64(current_ts)
                lto_dict[pair]['result']['buyPrice'] = lto_dict[pair]['enter']['limit']['price']
                lto_dict[pair]['result']['buyAmount'] = lto_dict[pair]['enter']['limit']['amount']
                lto_dict[pair]['result']['sellPrice'] = lto_dict[pair]['exit']['limit']['price']
                lto_dict[pair]['result']['sellAmount'] = lto_dict[pair]['exit']['limit']['amount']
                lto_dict[pair]['result']['profit'] = lto_dict[pair]['result']['sellAmount'] - lto_dict[pair]['result']['buyAmount']
                lto_dict[pair]['result']['liveTime'] = lto_dict[pair]['result']['closedTime'] - lto_dict[pair]['enter']['enterTime']

                # Update df_balance: # Update df_balance: write the amount of the exit
                # TODO: Gather up all the df_balance sections and put them in a function
                df_balance.loc['USDT','free'] += lto_dict[pair]['result']['sellAmount']
                df_balance.loc['USDT','total'] = df_balance.loc['USDT','free'] + df_balance.loc['USDT','locked']
                df_balance.loc['USDT','ref_balance'] = df_balance.loc['USDT','total']
                # NOTE: For the quote_currency total and the ref_balance is the same

            elif int(lto_dict[pair]['exit']['limit']['expire']) <= current_ts:
                lto_dict[pair]['status'] = 'closed'
                lto_dict[pair]['result']['cause'] = 'exit_expire'
                lto_dict[pair]['result']['closedTime'] = bson.Int64(current_ts)
                # TODO: Needs to be decided when the exit expire happend: 
                #       simple solution: market sell (no matter the price)

                # NOTE: TEST: Simulation of the market sell is normally the open price of the future candle,
                #             For the sake of simplicity closed price of the last candle is used in the market sell
                #             by assumming that the 'close' price is pretty close to the 'open' of the future
                # NOTE: TEST: This section can be improved

                lto_dict[pair]['result']['buyPrice'] = lto_dict[pair]['enter']['limit']['price']
                lto_dict[pair]['result']['buyAmount'] = lto_dict[pair]['enter']['limit']['amount']
                lto_dict[pair]['result']['sellPrice'] = float(last_kline['close'])
                lto_dict[pair]['result']['sellAmount'] = lto_dict[pair]['result']['sellPrice'] * lto_dict[pair]['exit']['limit']['quantity']
                # TODO: Add buy and sell sections to result to have the items price, quantity and amount for both

                lto_dict[pair]['result']['profit'] = lto_dict[pair]['result']['sellAmount'] - lto_dict[pair]['result']['buyAmount']
                # TODO: Add enter and exit times to result section and remove from enter and exit items. Evalutate liveTime based on that

                # Update df_balance: write the amount of the exit
                df_balance.loc['USDT','free'] += lto_dict[pair]['result']['sellAmount']
                df_balance.loc['USDT','total'] = df_balance.loc['USDT','free'] + df_balance.loc['USDT','locked']
                df_balance.loc['USDT','ref_balance'] = df_balance.loc['USDT','total']
                # NOTE: For the quote_currency total and the ref_balance is the same

        elif lto_dict[pair]['status'] == 'partially_closed_exit':
            # Ignore for the tests
            pass
        else:
            pass
    return lto_dict


async def application(bwrapper, pair_list, df_list):

    #################### Phase 1: Perform pre-calculation tasks ####################
    current_ts = int(df_list[0].index[-1])
    
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

    # TODO: Based on the updates on lto_dict, update the df_balance

    # 1.5: Write the LTOs to [live-trades] and [hist-trades]
    # NOTE: Move the function after the new trade object execution
    await write_updated_ltos_to_db(lto_dict, lto_dict_original)

    # 1.6: Clean-up lto_dict from the "closed" ones
    for pair in lto_dict_original.keys():
        if lto_dict[pair]['status'] == 'closed':
            del lto_dict[pair]

    #################### Phase 2: Perform calculation tasks ####################
    analyzer, algorithm = analyzers.Analyzer(), algorithms.BackTestAlgorithm()

    # 2.1: Analyzer only provide the simplified informations, it does not make any decision
    analysis_dict = await asyncio.create_task(analyzer.sample_analyzer(data_dict))

    # 2.2: Algorithm is the only authority to make decision

    trade_dict = await asyncio.create_task(algorithm.sample_algorithm(analysis_dict, lto_dict, df_balance, current_ts)) # Send last timestamp index

    # 2.3: Execute the trade_dict if any
    if len(trade_dict):
        # 2.3.1: Send tos to broker
        exec_status, df_balance = await asyncio.create_task(bwrapper.execute_decision(trade_dict,df_balance))
        # TODO: Handle exec_status to do sth in case of failure (like sending notification)

        # 2.3.2: Write trade_dict to [live-trades] (assume it is executed successfully)
        result = await mongocli.do_insert_many("live-trades",trade_dict)
        


    #################### Phase 3: Perform post-calculation tasks ####################
    observation_obj = await observer.sample_observer(df_balance)

    await mongocli.do_insert_one("observer",observation_obj.get())   
    return trade_dict


async def main():

    client = await AsyncClient.create(api_key=cred_info['Binance']['Production']['PUBLIC-KEY'],
                                      api_secret=cred_info['Binance']['Production']['SECRET-KEY'])

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
    # TODO: Added enter_expired and exit_expired ones


    # Dump df_csv_list[0] to a file for debug purposes
    f = open('out','w'); f.write(df_csv_list[0].to_string()); f.close()

    # Evaluate the statistics
    await evaluate_stats()

    # Visualize the test session
    fp.buy_sell(df_csv_list[0], df_closed_hto)

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