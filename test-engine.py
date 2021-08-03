import asyncio
from binance import Client, AsyncClient
from datetime import datetime
import json
from Ikarus import binance_wrapper, backtest_strategies, notifications, analyzers, observers, mongo_utils
from Ikarus.enums import *
import logging
from logging.handlers import TimedRotatingFileHandler
import pandas as pd
import sys
from scripts import fplot as fp
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
    hto_list = await mongocli.do_find('hist-trades',{'result.cause':STAT_CLOSED})
    hto_closed = []
    for hto in hto_list:
        if TYPE_OCO in hto['exit'].keys():  plannedExitType = TYPE_OCO; plannedPriceName = 'limitPrice'
        elif TYPE_LIMIT in hto['exit'].keys(): plannedExitType = TYPE_LIMIT; plannedPriceName = 'price'

        hto_dict = {
            "_id": hto['_id'],
            "decision_time": hto['decision_time'],
            "enterTime": hto['result']['enter']['time'],
            "enterPrice": hto['enter'][TYPE_LIMIT]['price'],
            "exitTime": hto['result']['exit']['time'],
            "exitPrice": hto['exit'][plannedExitType][plannedPriceName],
            "sellPrice": hto['result']['exit']['price']
        }
        hto_closed.append(hto_dict)

    df = pd.DataFrame(hto_closed)
    return df


async def get_enter_expire_hto(df):
    # Read Database to get hist-trades and dump to a DataFrame
    hto_list = await mongocli.do_find('hist-trades',{'result.cause':STAT_ENTER_EXP})
    hto_ent_exp_list = []
    for hto in hto_list:
        # NOTE: HIGH: We dont know it the exit type is limit or not
        hto_dict = {
            "_id": hto['_id'],
            "decision_time": hto['decision_time'],
            "enterExpire": hto['enter'][TYPE_LIMIT]['expire'],
            "enterPrice": hto['enter'][TYPE_LIMIT]['price'],
        }
        hto_ent_exp_list.append(hto_dict)

    df = pd.DataFrame(hto_ent_exp_list)
    return df


async def get_exit_expire_hto(df):
    # Read Database to get hist-trades and dump to a DataFrame
    
    hto_list = await mongocli.do_find('hist-trades',{'result.cause':STAT_EXIT_EXP})
    hto_closed_list = []
    for hto in hto_list:
        if TYPE_OCO in hto['exit'].keys():  plannedExitType = TYPE_OCO; plannedPriceName = 'limitPrice'
        elif TYPE_LIMIT in hto['exit'].keys(): plannedExitType = TYPE_LIMIT; plannedPriceName = 'price'

        hto_dict = {
            "_id": hto['_id'],
            "decision_time": hto['decision_time'],
            "enterTime": hto['result']['enter']['time'],
            "enterPrice": hto['enter'][TYPE_LIMIT]['price'],
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

    logger.info('Total enter_expire trades: {}'.format(await mongocli.count("hist-trades", {'result.cause':STAT_ENTER_EXP})))
    logger.info('Total exit_expire trades: {}'.format(await mongocli.count("hist-trades", {'result.cause':STAT_EXIT_EXP})))
    logger.info('Total closed trades: {}'.format(await mongocli.count("hist-trades", {'result.cause':STAT_CLOSED})))
    
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


async def write_updated_ltos_to_db(lto_list, lto_dict_original):

    for lto in lto_list:

        # NOTE: Check for status change is removed since some internal changes might have been performed on status and needs to be reflected to history
        # If the status is closed then, it should be inserted to [hist-trades] and deleted from the [live-trades]
        if lto['status'] == STAT_CLOSED:
            # This if statement combines the "update the [live-trades]" and "delete the closed [live-trades]"
            result_insert = await mongocli.do_insert_one("hist-trades",lto)
            result_remove = await mongocli.do_delete_many("live-trades",{"_id":lto['_id']}) # "do_delete_many" does not hurt, since the _id is unique

        # NOTE: Manual trade option is omitted, needs to be added
        elif lto['status'] == STAT_OPEN_EXIT:
            # - The status might be changed from STAT_OPEN_ENTER or STAT_PART_CLOSED_ENTER to STAT_OPEN_EXIT (changes in result.enter and history)
            # - The open_exit might be expired and postponed with some other changes in 'exit' item (changes in exit and history)
            result_update = await mongocli.do_update( 
                "live-trades",
                {'_id': lto['_id']},
                {'$set': {'status': lto['status'],
                        'exit':lto['exit'],
                        'result.enter':lto['result']['enter'],
                        'history':lto['history'] 
                    }})
                
        elif lto['status'] == STAT_OPEN_ENTER:
            # - STAT_OPEN_ENTER might be expired and postponed with some additional changes in 'enter' item (changes in enter and history)
            result_update = await mongocli.do_update( 
                "live-trades",
                {'_id': lto['_id']},
                {'$set': {'status': lto['status'], 'enter':lto['enter'], 'history':lto['history'] }})

        # NOTE: These two below are not applicable
        elif lto['status'] == STAT_PART_CLOSED_ENTER:
            pass
        elif lto['status'] == STAT_PART_CLOSED_EXIT:
            pass
        else:
            pass


async def update_ltos(lto_list, data_dict, df_balance):
    """
    Args:
        lto_dict (dict): will be updated (status, result, exit sections)
        data_dict (dict): used for getting the candle to see if trade status needs to change
        current_ts (ts): used for info sections of ltos
        df_balance (pd.DataFrame): When a lto go from STAT_OPEN_EXIT to STAT_CLOSED or STAT_OPEN_ENTER to STAT_OPEN_EXIT
        it needs to be updated in terms of 'free' and 'locked'                                               

    Returns:
        dict: lto_dict
    """

    for i in range(len(lto_list)):
        pair = lto_list[i]['pair']

        # 1.2.1: Check trades and update status
        # TODO: Update the following patch for the multi scale
        assert len(data_dict[pair].keys()) == 1, "Multiple time scale is not supported"
        scale = list(data_dict[pair].keys())[0]
        last_kline = data_dict[pair][scale].tail(1)
        last_closed_candle_open_time = bson.Int64(last_kline.index.values[0])  # current_candle open_time

        if lto_list[i]['status'] == STAT_OPEN_ENTER:
            # NOTE: There is 2 method to enter: TYPE_LIMIT and TYPE_MARKET. Since market executed directly, it is not expected to have market at this stage
            if TYPE_LIMIT in lto_list[i]['enter'].keys():

                # Check if the open enter trade is filled else if the trade is expired
                if float(last_kline['low']) < lto_list[i]['enter'][TYPE_LIMIT]['price']:

                    # NOTE: Since this is testing, no dust created, perfect conversion
                    # TODO: If the enter is successfull then the exit order should be placed. This is only required in DEPLOY
                    lto_list[i]['status'] = STAT_WAITING_EXIT
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['enter']['type'] = TYPE_LIMIT
                    lto_list[i]['result']['enter']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['enter']['price'] = lto_list[i]['enter'][TYPE_LIMIT]['price']
                    lto_list[i]['result']['enter']['amount'] = lto_list[i]['enter'][TYPE_LIMIT]['amount']
                    lto_list[i]['result']['enter']['quantity'] = lto_list[i]['enter'][TYPE_LIMIT]['quantity']

                    # Remove the bought amount from the 'locked' and 'ref_balance' columns
                    df_balance.loc[config['broker']['quote_currency'], 'locked'] -= lto_list[i]['enter'][TYPE_LIMIT]['amount']
                    df_balance.loc[config['broker']['quote_currency'], 'ref_balance'] = df_balance.loc[config['broker']['quote_currency'], 'locked'] +  df_balance.loc[config['broker']['quote_currency'], 'free']
                    # TODO sync the ref_balance and total
                    # Update df_balance: add the quantity to the base_cur or create a row for base_cur
                    base_cur = pair.replace(config['broker']['quote_currency'],'')
                    if pair in list(df_balance.index):
                        df_balance.loc[base_cur, 'locked' ] += lto_list[i]['result']['enter']['quantity']
                    else:
                        # Previously there was no base_currency, so we create a row for it
                        # free  locked    total      pair   price  ref_balance
                        df_balance.loc[base_cur] = [0.0, lto_list[i]['result']['enter']['quantity'], 0, pair, 0, 0]
                        df_balance.loc[base_cur, 'total'] = df_balance.loc[base_cur,'free'] + df_balance.loc[base_cur,'locked']
                        # NOTE: TEST: 'price' and 'ref_balance' is omitted #NOTE ADD total not the ref_balance for the base_cur

                elif int(lto_list[i]['enter'][TYPE_LIMIT]['expire']) <= last_closed_candle_open_time:
                    # Report the expiration to algorithm
                    lto_list[i]['status'] = STAT_ENTER_EXP
                    lto_list[i]['history'].append(lto_list[i]['status'])

            else:
                # TODO: Internal Error
                pass

        elif lto_list[i]['status'] == STAT_PART_CLOSED_ENTER:
            # Ignore for the tests
            pass

        elif lto_list[i]['status'] == STAT_OPEN_EXIT:

            if TYPE_LIMIT in lto_list[i]['exit'].keys():

                # Check if the open sell trade is filled or stoploss is taken
                if float(last_kline['high']) > lto_list[i]['exit'][TYPE_LIMIT]['price']:

                    lto_list[i]['status'] = STAT_CLOSED
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['cause'] = STAT_CLOSED

                    lto_list[i]['result']['exit']['type'] = TYPE_LIMIT
                    lto_list[i]['result']['exit']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['exit']['price'] = lto_list[i]['exit'][TYPE_LIMIT]['price']
                    lto_list[i]['result']['exit']['amount'] = lto_list[i]['exit'][TYPE_LIMIT]['amount']
                    lto_list[i]['result']['exit']['quantity'] = lto_list[i]['exit'][TYPE_LIMIT]['quantity']

                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] - lto_list[i]['result']['enter']['amount']
                    lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']

                    # Update df_balance: # Update df_balance: write the amount of the exit
                    # TODO: Gather up all the df_balance sections and put them in a function
                    df_balance.loc[config['broker']['quote_currency'],'free'] += lto_list[i]['result']['exit']['amount']
                    df_balance.loc[config['broker']['quote_currency'],'total'] = df_balance.loc[config['broker']['quote_currency'],'free'] + df_balance.loc[config['broker']['quote_currency'],'locked']
                    df_balance.loc[config['broker']['quote_currency'],'ref_balance'] = df_balance.loc[config['broker']['quote_currency'],'total']
                    # NOTE: For the quote_currency total and the ref_balance is the same

                elif int(lto_list[i]['exit'][TYPE_LIMIT]['expire']) <= last_closed_candle_open_time:
                    lto_list[i]['status'] = STAT_EXIT_EXP
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    
                else:
                    pass

            elif TYPE_OCO in lto_list[i]['exit'].keys():
                # NOTE: Think about the worst case and check the stop loss first.

                if float(last_kline['low']) < lto_list[i]['exit'][TYPE_OCO]['stopPrice']:
                    # Stop Loss takens
                    lto_list[i]['status'] = STAT_CLOSED
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['cause'] = STAT_CLOSED
                    lto_list[i]['result']['exit']['type'] = 'oco_stoploss'
                    lto_list[i]['result']['exit']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['exit']['price'] = lto_list[i]['exit'][TYPE_OCO]['stopLimitPrice']
                    lto_list[i]['result']['exit']['amount'] = lto_list[i]['exit'][TYPE_OCO]['amount']
                    lto_list[i]['result']['exit']['quantity'] = lto_list[i]['exit'][TYPE_OCO]['quantity']

                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] - lto_list[i]['result']['enter']['amount']
                    lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']

                    # Update df_balance: # Update df_balance: write the amount of the exit
                    # TODO: Gather up all the df_balance sections and put them in a function
                    df_balance.loc[config['broker']['quote_currency'],'free'] += lto_list[i]['result']['exit']['amount']
                    df_balance.loc[config['broker']['quote_currency'],'total'] = df_balance.loc[config['broker']['quote_currency'],'free'] + df_balance.loc[config['broker']['quote_currency'],'locked']
                    df_balance.loc[config['broker']['quote_currency'],'ref_balance'] = df_balance.loc[config['broker']['quote_currency'],'total']
                    pass
                
                elif float(last_kline['high']) > lto_list[i]['exit'][TYPE_OCO]['limitPrice']:
                    # Limit taken

                    lto_list[i]['status'] = STAT_CLOSED
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['cause'] = STAT_CLOSED

                    lto_list[i]['result']['exit']['type'] = 'oco_limit'
                    lto_list[i]['result']['exit']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['exit']['price'] = lto_list[i]['exit'][TYPE_OCO]['limitPrice']
                    lto_list[i]['result']['exit']['amount'] = lto_list[i]['exit'][TYPE_OCO]['amount']
                    lto_list[i]['result']['exit']['quantity'] = lto_list[i]['exit'][TYPE_OCO]['quantity']

                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] - lto_list[i]['result']['enter']['amount']
                    lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']

                    # Update df_balance: # Update df_balance: write the amount of the exit
                    # TODO: Gather up all the df_balance sections and put them in a function
                    df_balance.loc[config['broker']['quote_currency'],'free'] += lto_list[i]['result']['exit']['amount']
                    df_balance.loc[config['broker']['quote_currency'],'total'] = df_balance.loc[config['broker']['quote_currency'],'free'] + df_balance.loc[config['broker']['quote_currency'],'locked']
                    df_balance.loc[config['broker']['quote_currency'],'ref_balance'] = df_balance.loc[config['broker']['quote_currency'],'total']
                    # NOTE: For the quote_currency total and the ref_balance is the same
                    pass

                elif int(lto_list[i]['exit'][TYPE_OCO]['expire']) <= last_closed_candle_open_time:
                    lto_list[i]['status'] = STAT_EXIT_EXP
                    lto_list[i]['history'].append(lto_list[i]['status'])

                else:
                    pass

            else:
                # TODO: Internal Error
                pass
                
        elif lto_list[i]['status'] == STAT_PART_CLOSED_EXIT:
            # Ignore for the tests
            pass

        else:
            # TODO: Internal Error
            pass

    return lto_list


async def application(bwrapper, pair_list, df_list):

    #################### Phase 1: Perform pre-calculation tasks ####################
    #current_ts = int(df_list[0].index[-1])
    
    # The close time of the last_kline + 1ms, corresponds to the open_time of the future kline which is actually the kline we are in. 
    # If the execution takes 2 second, then the order execution and the updates will be done
    # 2 second after the new kline started. But the analysis will be done based on the last closed kline
    current_ts = int(df_list[0]['close_time'].iloc[-1] + 1) 

    # 1.1 Get live trade objects (LTOs)
    lto_list = await mongocli.do_find('live-trades',{})

    lto_list_original = copy.deepcopy(lto_list)

    # 1.2 Get balance and datadict
    info = await mongocli.get_last_doc('observer',{})
    # NOTE:info given to the get_current_balance only for test-engine.py
    tasks_pre_calc = bwrapper.get_current_balance(info), bwrapper.get_data_dict(pair_list, input_data_config, df_list)
    df_balance, data_dict = await asyncio.gather(*tasks_pre_calc)

    # 1.3: Query the status of LTOs from the Broker
    # 1.4: Update the LTOs
    lto_list = await update_ltos(lto_list, data_dict, df_balance)

    #################### Phase 2: Perform calculation tasks ####################

    # 2.1: Analyzer only provide the simplified informations, it does not make any decision
    analysis_dict = await asyncio.create_task(analyzer.sample_analyzer(data_dict))

    # 2.2: Algorithm is the only authority to make decision
    # NOTE: Execution of multiple strategy is possible, if 'strategy': 'sample_oco_strategy' like items added to the TOs
    nto_list = await asyncio.create_task(strategy_list[0].run(analysis_dict, lto_list, df_balance, current_ts)) # Send the last timestamp index

    # 2.3: Execute LTOs and NTOs if any
    if len(nto_list) or len(lto_list):
        # 2.3.1: Execute the TOs
        exec_status, df_balance, lto_list = await asyncio.create_task(bwrapper.execute_decision(nto_list, df_balance, lto_list, data_dict))
        # TODO: Handle exec_status to do sth in case of failure (like sending notification)


    #################### Phase 3: Perform post-calculation tasks ####################

    if len(nto_list):
        # 3.1: Write trade_dict to [live-trades] (assume it is executed successfully)
        result = await mongocli.do_insert_many("live-trades",nto_list)

    # 3.2: Write the LTOs and NTOs to [live-trades] and [hist-trades]
    await write_updated_ltos_to_db(lto_list, lto_list_original)

    # 3.3: Get the onserver
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
    # NOTE: Normally the pair list is obtained from the config, but for testing it is coming from the data files.
    time_scale_list = []
    df_csv_list = []

    # Iterate over the given files
    # TODO: To simulate live-trade, include the next candle as the current candle

    for file in config['files']:
        filename = file.split('\\')[-1]
        pair_list.append(filename.split('_')[0].upper())
        time_scale_list.append(filename.split('_')[1])
        df = pd.read_csv(file)
        df = df.set_index(['open_time'])
        df_csv_list.append(df)

    # TODO: Multiple pairs, or multiple timescale for a pair logic, requires some generalizations
    #       This changes can be handled after the app is confident about working 1 pair and 1 scale
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

    # Add scales_in_minute to the config to be used in strategy etc.
    config = generate_scales_in_minute(config)

    # Setup initial objects
    observer = observers.Observer()
    analyzer = analyzers.Analyzer(config)
    strategy_manager = backtest_strategies.StrategyManager(config)
    strategy_list = strategy_manager.get_strategies()

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