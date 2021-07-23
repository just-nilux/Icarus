import asyncio
from binance import Client, AsyncClient
from datetime import datetime
import json
from Ikarus import binance_wrapper, backtest_strategies, notifications, analyzers, observers, mongo_utils
import logging
from logging.handlers import TimedRotatingFileHandler
import pandas as pd
import sys
from scripts import fplot as fp
import copy
import bson

# Global Variables
SYSTEM_STATUS = 0
STATUS_TIMEOUT = 0

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


async def update_ltos(lto_dict, data_dict, df_balance):
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


async def application(bwrapper, pair_list, df_list):

    #################### Phase 1: Perform pre-calculation tasks ####################
    #current_ts = int(df_list[0].index[-1])
    
    # The close time of the last_kline + 1ms, corresponds to the open_time of the future kline which is actually the kline we are in. 
    # If the execution takes 2 second, then the order execution and the updates will be done
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
    tasks_pre_calc = bwrapper.get_current_balance(info), bwrapper.get_data_dict(pair_list, input_data_config, df_list)
    df_balance, data_dict = await asyncio.gather(*tasks_pre_calc)

    # 1.3: Query the status of LTOs from the Broker
    # 1.4: Update the LTOs
    lto_dict = await update_ltos(lto_dict, data_dict, df_balance)

    #################### Phase 2: Perform calculation tasks ####################

    # 2.1: Analyzer only provide the simplified informations, it does not make any decision
    analysis_dict = await asyncio.create_task(analyzer.sample_analyzer(data_dict))

    # 2.2: Algorithm is the only authority to make decision
    # NOTE: Execution of multiple algorithm is possible, if 'algorithm': 'sample_oco_algorithm' like items added to the to's
    nto_dict = await asyncio.create_task(strategy.run(analysis_dict, lto_dict, df_balance, current_ts)) # Send the last timestamp index

    # 2.3: Execute LTOs and NTOs if any
    if len(nto_dict) or len(lto_dict):
        # 2.3.1: Execute the TOs
        exec_status, df_balance, lto_dict = await asyncio.create_task(bwrapper.execute_decision(nto_dict, df_balance, lto_dict, data_dict))
        # TODO: Handle exec_status to do sth in case of failure (like sending notification)
        if len(nto_dict):
            # 2.3.2: Write trade_dict to [live-trades] (assume it is executed successfully)
            result = await mongocli.do_insert_many("live-trades",nto_dict)     

    #################### Phase 3: Perform post-calculation tasks ####################

    # 3.1: Write the LTOs and NTOs to [live-trades] and [hist-trades]
    await write_updated_ltos_to_db(lto_dict, lto_dict_original)

    # 3.2: Get the onserver
    observation_obj = await observer.sample_observer(df_balance)
    await mongocli.do_insert_one("observer",observation_obj.get())   

    pass


async def main():

    # NOTE: Temporary hack for yesting without internet connection
    #client = await AsyncClient.create(api_key=cred_info['Binance']['Production']['PUBLIC-KEY'],
    #                                  api_secret=cred_info['Binance']['Production']['SECRET-KEY'])

    client = 'mock_client'

    bwrapper = binance_wrapper.TestBinanceWrapper(client, config)

    # Init the df_tickers to not to call binance API in each iteration
    binance_wrapper.TestBinanceWrapper.df_tickers = await bwrapper.get_all_tickers()

    # Initiate the cash in the [observer]
    observation_item = {
        'balances': config['balances']
    }
    await mongocli.do_insert_one("observer",observation_item)   

    # Obtain the pairs and the time scales of the input data
    pair_list = []
    time_scale_list = []
    df_csv_list = []

    # Iterate over the given files
    for file in config['files']:
        filename = file.split('\\')[-1]
        pair_list.append(filename.split('_')[0].upper())
        time_scale_list.append(filename.split('_')[1])
        df = pd.read_csv(file)
        df = df.set_index(['open_time'])
        df_csv_list.append(df)

    # TODO: Multiple pairs, or multiple timescale for a pair logic, requires some generalizations
    hist_data_length = int(input_data_config[ input_data_config['scale']==time_scale_list[0] ]['length_int'].values)
    total_len = len(df_csv_list[0]) - hist_data_length
    printProgressBar(0, total_len, prefix = 'Progress:', suffix = 'Complete', length = 50)
    for i in range(total_len):
        logger.debug(f'Iteration {i}:')
        printProgressBar(i + 1, total_len, prefix = 'Progress:', suffix = 'Complete', length = 50)
        # TODO: Consider the fact that last candle can be newly opened candle and the analysis shouold be performed based on the last closed candle
        # Create the df_list
        df_list = []
        for df in df_csv_list:
            df_list.append(df.iloc[i:i+hist_data_length])
        await application(bwrapper, pair_list, df_list)

    # Get [hist-trades] docs to visualize the session
    df_closed_hto, df_enter_expire, df_exit_expire = await asyncio.gather( 
        get_closed_hto(df_csv_list[0]), 
        get_enter_expire_hto(df_csv_list[0]), 
        get_exit_expire_hto(df_csv_list[0]))

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

    # TODO: In case of multiple strategies, there should be a list of strategy to be given to app or it the strategy list can be global
    # Available strategies, can be kept in a 'strategies_list' variable instead of single object
    #
    # NOTE: Multiple analyzers not needed because an analyzer can be configured to work with multiple 'scales' and 'pairs'.
    #       It may provide different analysis results as an item in the analysis objects.
    # NOTE: Suppose there are multiple 'time scales' for a 'pair'. In this case, the output of all of the 'scales' are used to generate a common analysis for a 'pair'
    #       In other words, there will one-to-one mapping between 'pairs' and the analysis items.

    logger.info("---------------------------------------------------------")
    logger.info("------------------- Engine Restarted --------------------")
    logger.info("---------------------------------------------------------")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    print(f"Test Session <{config['tag']}> completed")