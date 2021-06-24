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


async def application(bwrapper, pair_list, df_list):

    # Phase 1: Perform pre-calculation tasks

    # 1.1 Get live trade objects (LTOs)
    lto_list = await mongocli.do_find('live-trades',{})

    # Create lto_dict to be updated and then to be processed in algorithm
    lto_dict = dict()
    for lto in lto_list:
        lto_dict[lto['pair']] = lto

    # original_lto_dict is required to check if the lto_dict is changed
    original_lto_dict = lto_dict

    tasks_pre_calc = bwrapper.get_current_balance(), bwrapper.get_data_dict(pair_list, test_time_df, df_list)
    balance, data_dict = await asyncio.gather(*tasks_pre_calc)

    # TODO: 1.2: Query the status of LTOs from the Broker
    #            - for testing purposes, a mock-broker can be used (checking if the order is fulfilled or not)
    # !!! Only for testing purposes !!!
    for pair in set(lto_dict.keys()) & set(data_dict.keys()):
        pair_klines = data_dict[pair]

        # There might be 2 group of open trades:
        # enter: 
        #       waiting for limitBuy to fill
        # exit: 
        #       waiting for limitSell to fill
        #       waiting for stopLoss to fill

        # 1.2.1: Check trades and update status
        last_kline = pair_klines['15m'].tail(1)

        # TODO: check the expired ones
        if lto_dict[pair]['status'] == 'open_enter':

            # Check if the open buy trade is filled
            if last_kline['low'] < lto_dict[pair]['enter']['limitBuy']['price']:
                lto_dict[pair]['status'] = 'open_exit'
                lto_dict[pair]['enter']['enterTime'] =  int(df_list[0].index[-1])
            

        elif lto_dict[pair]['status'] == 'partially_closed_enter':
            # Ignore for the tests
            pass
        elif lto_dict[pair]['status'] == 'open_exit':

            # Check if the open sell trade is filled or stoploss is taken
            if last_kline['high'] < lto_dict[pair]['exit']['limitSell']['price']:
                lto_dict[pair]['status'] = 'closed'
                lto_dict[pair]['exit']['exitTime'] =  int(df_list[0].index[-1])

        elif lto_dict[pair]['status'] == 'partially_closed_exit':
            # Ignore for the tests
            pass
        else:
            pass

    # TODO: 1.3: Update the LTOs
    #            - add statistics to the results
    # TODO: 1.4: Write the LTOs to [live-trades] and [hist-trades]
    # TODO: Move the function after the new trade object execution
    for pair, lto in lto_dict.items():
        
        # If there is no change in the status, continue to iterate
        if original_lto_dict[pair]['status'] == lto_dict[pair]['status']:
            continue

        if lto['status'] == 'closed':

            # Send closed lto's to the [hist-trades]
            result_insert = await mongocli.do_insert("hist-trades",lto)
            result_remove = await mongocli.do_remove("live-trades",{"_id":lto['_id']})
            del lto_dict['pair']

        elif lto['status'] == 'open_exit':
            # Check if the previous state is open exit. If so, update, otherwise continue
            result_update = await mongocli.do_update("live-trades",lto)
            pass
        elif lto['status'] == 'partially_closed_enter':
            pass
        elif lto['status'] == 'partially_closed_exit':
            pass
        else:
            pass


    # Phase 2: Perform calculation tasks
    analyzer, algorithm = analyzers.Analyzer(), algorithms.BackTestAlgorithm()

    # 2.1: Analyzer only provide the simplified informations, it does not make any decision
    analysis_dict = await asyncio.create_task(analyzer.sample_analyzer(data_dict))

    # 2.2: Algorithm is the only authority to make decision
    # It requires to feed analysis_dict and lto_dict so that it may decide to:
    # - not to enter a new trade if there is already an open trade
    # - cancel the trade if an drawdown is detected
    trade_dict = await asyncio.create_task(algorithm.sample_algorithm(analysis_dict, lto_dict, df_list[0].index[-1])) # Send last timestamp index

    if len(trade_dict):
        exec_status = await asyncio.create_task(bwrapper.execute_decision(trade_dict))
        # TODO: Handle exec_status to do sth in case of failure (like sending notification)

        # Write trade_dict to [live-trades] (assume it is executed successfully)
        result = await mongocli.do_insert_many("live-trades",trade_dict)



    # Phase 3: Perform post-calculation tasks
    logger.info('post-calculation phase started')
    observation_obj = await observer.sample_observer(balance)

    await mongocli.do_insert("observer",observation_obj.get())   
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

    df_csv_list[0]['buy'] = np.nan
    df_csv_list[0]['sell'] = np.nan

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

        if len(trade_dict):
            tradeid = float(trade_dict[pair_list[0]].get('tradeid'))

            # Add buy and sell points to the DataFrame
            df_csv_list[0].loc[tradeid, 'buy'] = float(trade_dict[pair_list[0]].get(['enter','limitBuy','price']))
            df_csv_list[0].loc[tradeid, 'sell'] = float(trade_dict[pair_list[0]].get(['exit','limitSell','price']))



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