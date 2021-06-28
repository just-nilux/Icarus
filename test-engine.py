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
            "enterPrice": hto['enter']['limitBuy']['price'],
            "exitTime": hto['exit']['exitTime'],
            "exitPrice": hto['exit']['limitSell']['price']
        }

    return pd.DataFrame(hto_dict)


async def application(bwrapper, pair_list, df_list):

    # Phase 1: Perform pre-calculation tasks

    current_ts = df_list[0].index[-1]
    # 1.1 Get live trade objects (LTOs)
    lto_list = await mongocli.do_find('live-trades',{})

    # Create lto_dict to be updated and then to be processed in algorithm
    lto_dict = dict()
    for lto in lto_list:
        lto_dict[lto['pair']] = lto

    # lto_dict_original is required to check if the lto_dict is changed
    lto_dict_original = copy.deepcopy(lto_dict)

    tasks_pre_calc = bwrapper.get_current_balance(), bwrapper.get_data_dict(pair_list, test_time_df, df_list)
    balance, data_dict = await asyncio.gather(*tasks_pre_calc)

    # TODO: 1.2: Query the status of LTOs from the Broker
    #            - for testing purposes, a mock-broker can be used (checking if the order is fulfilled or not)
    # TODO: 1.3: Update the LTOs
    #            - add statistics to the results
    # !!! Only for testing purposes !!!
    for pair in set(lto_dict.keys()) & set(data_dict.keys()):
        pair_klines = data_dict[pair]

        # There might be 2 group of open trades:
        # enter: 
        #       waiting for limitBuy to fill
        #       or to be expired
        # exit: 
        #       waiting for limitSell to fill
        #       waiting for stopLoss to fill
        #       or to be expired

        # 1.2.1: Check trades and update status
        pair_klines_dict = pair_klines.get()
        last_kline = pair_klines_dict['15m'].tail(1)

        # TODO: check the expired ones
        if lto_dict[pair]['status'] == 'open_enter':

            # Check if the open enter trade is filled else if the trade is expired
            if float(last_kline['low']) < lto_dict[pair]['enter']['limitBuy']['price']:
                # TODO NEXT: check this update
                lto_dict[pair]['status'] = 'open_exit'
                lto_dict[pair]['enter']['enterTime'] =  int(df_list[0].index[-1])

            elif lto_dict[pair]['enter']['expire'] >= current_ts:
                lto_dict[pair]['status'] = 'closed'
                lto_dict[pair]['result']['cause'] = 'enter_expire'
                lto_dict[pair]['result']['closedTime'] = bson.Int64(current_ts)
                #lto_dict[pair]['result']['liveTime'] = lto_dict[pair]['tradeid']-current_ts
                pass

        elif lto_dict[pair]['status'] == 'partially_closed_enter':
            # Ignore for the tests
            pass
        elif lto_dict[pair]['status'] == 'open_exit':

            # Check if the open sell trade is filled or stoploss is taken
            if float(last_kline['high']) < lto_dict[pair]['exit']['limitSell']['price']:

                # TODO: In this case the result section needs to be fulfilled
                lto_dict[pair]['status'] = 'closed'
                lto_dict[pair]['result']['cause'] = 'closed'
                lto_dict[pair]['exit']['exitTime'] =  int(df_list[0].index[-1])

            elif lto_dict[pair]['exit']['expire'] >= current_ts:
                lto_dict[pair]['status'] = 'closed'
                lto_dict[pair]['result']['cause'] = 'enter_expire'
                lto_dict[pair]['result']['closedTime'] = bson.Int64(current_ts)
                # TODO: Needs to be decided when the exit expire happend: 
                #       simple solution: market sell (no matter the price)

        elif lto_dict[pair]['status'] == 'partially_closed_exit':
            # Ignore for the tests
            pass
        else:
            pass

    # TODO: 1.4: Write the LTOs to [live-trades] and [hist-trades]
    # NOTE: Move the function after the new trade object execution
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

    # Clean-up lto_dict from the "closed" ones
    for pair in lto_dict_original.keys():
        del lto_dict[pair]

    # Phase 2: Perform calculation tasks
    analyzer, algorithm = analyzers.Analyzer(), algorithms.BackTestAlgorithm()

    # 2.1: Analyzer only provide the simplified informations, it does not make any decision
    analysis_dict = await asyncio.create_task(analyzer.sample_analyzer(data_dict))

    # 2.2: Algorithm is the only authority to make decision
    # It requires to feed analysis_dict and lto_dict so that it may decide to:
    # - not to enter a new trade if there is already an open trade
    # - cancel the trade if an drawdown is detected
    trade_dict = await asyncio.create_task(algorithm.sample_algorithm(analysis_dict, lto_dict, current_ts)) # Send last timestamp index

    if len(trade_dict):
        exec_status = await asyncio.create_task(bwrapper.execute_decision(trade_dict))
        # TODO: Handle exec_status to do sth in case of failure (like sending notification)

        # Write trade_dict to [live-trades] (assume it is executed successfully)
        result = await mongocli.do_insert_many("live-trades",trade_dict)



    # Phase 3: Perform post-calculation tasks
    logger.info('post-calculation phase started')
    observation_obj = await observer.sample_observer(balance)

    await mongocli.do_insert_one("observer",observation_obj.get())   
    return trade_dict


async def main():

    bwrapper = binance_wrapper.TestBinanceWrapper(config['cash'], config['commission'])

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
        
        trade_dict = await application(bwrapper, pair_list, df_list)

        '''
        if len(trade_dict):
            tradeid = float(trade_dict[pair_list[0]].get('tradeid'))

            # Add buy and sell points to the DataFrame
            df_csv_list[0].loc[tradeid, 'buy'] = float(trade_dict[pair_list[0]].get(['enter','limitBuy','price']))
            df_csv_list[0].loc[tradeid, 'sell'] = float(trade_dict[pair_list[0]].get(['exit','limitSell','price']))
        '''

    df_csv_list[0]['decision_ts'] = np.nan      # ts when the enter decision is made
    df_csv_list[0]['buy'] = np.nan              # buy price
    df_csv_list[0]['sell'] = np.nan             # sell price

    # Read Database to get hist-trades
    hto_closed_list = await mongocli.do_find('hist-trades',{"result.cause":"closed"})
    hto_list = []
    for hto in hto_closed_list:
        hto_dict = {
            "_id": hto['_id'],
            "tradeid": hto['tradeid'],
            "enterTime": hto['enter']['enterTime'],
            "enterPrice": hto['enter']['limitBuy']['price'],
            "exitTime": hto['exit']['exitTime'],
            "exitPrice": hto['exit']['limitSell']['price']
        }
        hto_list.append(hto_dict)

    df_hto = pd.DataFrame(hto_list)

    for idx in df_csv_list[0].index:
        if idx in df_hto['tradeid']:
            # TODO NEXT: 
            df_csv_list[0].loc[idx, 'decision_ts'] = "df_hot buy price level"
        pass

        if idx in df_hto['enterTime']:
            pass

        if idx in df_hto['exitTime']:
            pass       

    count_obs = await mongocli.count("observer")
    logger.info(f'Total observer item: {count_obs}') 


    # Statistics
    count_obs = await mongocli.count("observer")
    logger.info(f'Total observer item: {count_obs}') 

    fp.buy_sell(df_csv_list[0])

if __name__ == '__main__':
    
    print(str(sys.argv[1]))
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    logger = logging.getLogger('app')
    mongocli = mongo_utils.MongoClient(config['mongodb']['host'], config['mongodb']['port'], config['tag'])

    # Initialize and configure objects
    setup_logger(config['log-level'])
    observer = observers.Observer()

    logger.info("---------------------------------------------------------")
    logger.info("------------------- Engine Restarted --------------------")
    logger.info("---------------------------------------------------------")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    print(f"Test Session <{config['tag']}> completed")