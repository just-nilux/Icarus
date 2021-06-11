import asyncio
from binance import Client, AsyncClient
from datetime import datetime, timedelta
import json
from Ikarus import binance_wrapper, algorithms, notifications, analyzers, observers, mongo_utils
import logging
from logging.handlers import TimedRotatingFileHandler
import pandas as pd
import argparse

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

logger = logging.getLogger('app')
mongocli = mongo_utils.MongoClient("localhost", 27017)

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

def setup_logger():
    global logger
    log_filename = 'log/test-ikarus-app.log'
    logger = logging.getLogger('app')
    logger.setLevel(logging.DEBUG)

    rfh = TimedRotatingFileHandler(filename=log_filename,
                                   when='H',
                                   interval=1,
                                   backupCount=5)

    rfh.setLevel(logging.DEBUG)

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


def series_to_supervised(data, n_in=1, n_out=1, dropnan=True):
	n_vars = 1 if type(data) is list else data.shape[1]
	df = pd.DataFrame(data)
	cols, names = list(), list()
	# input sequence (t-n, ... t-1)
	for i in range(n_in, 0, -1):
		cols.append(df.shift(i))
		names += [('var%d(t-%d)' % (j+1, i)) for j in range(n_vars)]
	# forecast sequence (t, t+1, ... t+n)
	for i in range(0, n_out):
		cols.append(df.shift(-i))
		if i == 0:
			names += [('var%d(t)' % (j+1)) for j in range(n_vars)]
		else:
			names += [('var%d(t+%d)' % (j+1, i)) for j in range(n_vars)]
	# put it all together
	agg = pd.concat(cols, axis=1)
	agg.columns = names
	# drop rows with NaN values
	if dropnan:
		agg.dropna(inplace=True)
	return agg

async def wait_until(dt):
    now = int(datetime.timestamp(datetime.now()))
    sleep_time = dt - now
    print("dt:{}, now:{}, sleeptime:{}".format(dt,now,sleep_time))
    await asyncio.sleep(dt - now)


async def run_at(dt, coro):
    await wait_until(dt)
    return await coro


async def application(bwrapper, pair_list, df_list):

    logger.debug('Current time')

    # Phase 1: Perform pre-calculation tasks
    logger.info('pre-calculation phase started')
    tasks_pre_calc = bwrapper.get_current_balance(), bwrapper.get_data_dict(pair_list, test_time_df, df_list)
    balance, data_dict = await asyncio.gather(*tasks_pre_calc)

    # Phase 2: Perform calculation tasks
    logger.info('calculation phase started')
    analyzer, algorithm = analyzers.Analyzer(), algorithms.Algorithm()
    analysis_dict = await asyncio.create_task(analyzer.sample_analyzer(data_dict))
    trade_dict = await asyncio.create_task(algorithm.sample_algorithm(analysis_dict))

    if len(trade_dict):
        exec_status = await asyncio.create_task(bwrapper.execute_decision(trade_dict))
        # TODO: Handle exec_status to do sth in case of failure (like sending notification)
        # await mongocli.insert_many("live-trades",trade_dict)

    
    # Phase 3: Perform post-calculation tasks
    logger.info('post-calculation phase started')
    observation_obj = await observer.sample_observer(balance)


    #await mongocli.do_insert("observer",observation_obj.get())   

    logger.debug('Application ended')
    return True


async def main():

    bwrapper = binance_wrapper.TestBinanceWrapper(args.cash, args.com)

    # Get the pair_list
    pair_list = []

    # Get the df_csv_list to aggregate
    df_csv_list = []

    for file in args.files:
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

if __name__ == "__main__":
    #python.exe .\test-engine.py --files .\test\data\btcusdt_15m_202005121212_202005191213.csv --cash 10000 --com 0.075
    
    # Parameters:
    # - cash:
    # - comission rate:
    # - files:
    parser = argparse.ArgumentParser(description='Optional app description')
    parser.add_argument('--cash')
    parser.add_argument('--com')
    parser.add_argument('--files', nargs="*")
    args = parser.parse_args()

    # Initialize and configure objects
    setup_logger()
    observer = observers.Observer()

    logger.info("---------------------------------------------------------")
    logger.info("------------------- Engine Restarted --------------------")
    logger.info("---------------------------------------------------------")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print("Completed")