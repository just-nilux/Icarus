import asyncio
from binance import Client, AsyncClient
from datetime import datetime
import json
from Ikarus import binance_wrapper, performance, strategy_manager, notifications, analyzers, observers, mongo_utils
from Ikarus.enums import *
from Ikarus.exceptions import NotImplementedException
from Ikarus.utils import time_scale_to_second, get_closed_hto, get_enter_expire_hto, get_exit_expire_hto, get_min_scale
import logging
from logging.handlers import TimedRotatingFileHandler
import pandas as pd
import sys
import copy
import bson
from itertools import chain, groupby
import operator
import itertools
from scripts import finplot_wrapper as fplot
from scripts.visualize_test_session import visualize_online

# Global Variables
SYSTEM_STATUS = 0
STATUS_TIMEOUT = 0

def generate_scales_in_minute(config_dict):
    # TODO: add the key: 'M'
    scales_to_minute = {'m':1, 'h':60, 'd':24*60, 'w':10080}  # Hardcoded scales in minute
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


async def write_updated_ltos_to_db(lto_list):

    for lto in lto_list:

        # NOTE: Check for status change is removed since some internal changes might have been performed on status and needs to be reflected to history
        # If the status is closed then, it should be inserted to [hist-trades] and deleted from the [live-trades]
        if lto['status'] == STAT_CLOSED:
            # This if statement combines the "update the [live-trades]" and "delete the closed [live-trades]"
            result_insert = await mongocli.do_insert_one("hist-trades",lto)
            result_remove = await mongocli.do_delete_many("live-trades",{"_id":lto['_id']}) # "do_delete_many" does not hurt, since the _id is unique

            if lto['result']['cause'] == STAT_CLOSED:
                hto_stat = await stats.eval_hto_stat(lto)
                pass

        # NOTE: Manual trade option is omitted, needs to be added
        elif lto['status'] in [ STAT_OPEN_EXIT, STAT_WAITING_EXIT, STAT_EXIT_EXP]:
            # - The status might be changed from STAT_OPEN_ENTER or STAT_PART_CLOSED_ENTER to STAT_OPEN_EXIT (changes in result.enter and history)
            # - The open_exit might be expired and postponed with some other changes in 'exit' item (changes in exit and history)
            result_update = await mongocli.do_update( 
                "live-trades",
                {'_id': lto['_id']},
                {'$set': {'status': lto['status'],
                        'exit':lto['exit'],
                        'result.enter':lto['result']['enter'],
                        'history':lto['history'],
                        'update_history':lto['update_history']
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


async def update_ltos(lto_list, data_dict, strategy_period_mapping, df_balance):
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

    # NOTE: Only get the related LTOs and ONLY update the related LTOs. Doing the same thing here is pointless.

    for i in range(len(lto_list)):
        pair = lto_list[i]['pair']

        # 1.2.1: Check trades and update status
        strategy_min_scale = strategy_period_mapping[lto_list[i]['strategy']]
        last_kline = data_dict[pair][strategy_min_scale].tail(1)
        last_closed_candle_open_time = bson.Int64(last_kline.index.values[0])

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
                    lto_list[i]['result']['exit']['quantity'] = lto_list[i]['exit'][TYPE_LIMIT]['quantity'] 
                    lto_list[i]['result']['exit']['amount'] = lto_list[i]['result']['exit']['price'] * lto_list[i]['result']['exit']['quantity']
                    # NOTE: Exit quantity and the enter quantity is assumed to be the same

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
                    lto_list[i]['result']['exit']['quantity'] = lto_list[i]['exit'][TYPE_OCO]['quantity']
                    lto_list[i]['result']['exit']['amount'] = lto_list[i]['result']['exit']['price'] * lto_list[i]['result']['exit']['quantity']

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
                    lto_list[i]['result']['exit']['quantity'] = lto_list[i]['exit'][TYPE_OCO]['quantity']
                    lto_list[i]['result']['exit']['amount'] = lto_list[i]['result']['exit']['price'] * lto_list[i]['result']['exit']['quantity']

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


async def application(strategy_list, bwrapper, ikarus_time):
    # NOTE: 'ikarus-time' denotes the current_time in old implementation
    #################### Phase 1: Perform pre-calculation tasks ####################
    #current_ts = int(df_list[0].index[-1])
    
    # The close time of the last_kline + 1ms, corresponds to the open_time of the future kline which is actually the kline we are in. 
    # If the execution takes 2 second, then the order execution and the updates will be done
    # 2 second after the new kline started. But the analysis will be done based on the last closed kline
    #current_ts = int(df_list[0]['close_time'].iloc[-1] + 1)  
    # NOTE: df_list[0]['close_time'].iloc[-1] is the close time of last closed candle such as 1589360399999
    #       In this case +1 will be the start time of the next candle which is the current candle for the application
    logger.info(f'Ikarus Time: [{ikarus_time}]')

    # 1.1 Get balance and datadict,
    # TODO: NEXT: give index paramter to retrieve a single object instead of a list
    info = await mongocli.get_n_docs('observer') # Default is the last doc
    # NOTE:info given to the get_current_balance only for test-engine.p
    
    # Each strategy has a min_period. Thus I can iterate over it to see the matches between the current time and their period
    meta_data_pool = []
    #active_strategies = []
    strategy_period_mapping = {}
    # NOTE: Active Strategies is used to determine the strategies and gather the belonging LTOs
    for strategy_obj in strategy_list:
        if ikarus_time % time_scale_to_second(strategy_obj.min_period) == 0:
            meta_data_pool.append(strategy_obj.meta_do)
            strategy_period_mapping[strategy_obj.name] = strategy_obj.min_period

    ikarus_time = ikarus_time * 1000 # Convert to ms
    meta_data_pool = set(chain(*meta_data_pool))

    # All you need to give to data_dcit is actually the (time_scale, pair) tuples and the ikarus_time
    tasks_pre_calc = bwrapper.get_current_balance(info[0]), bwrapper.get_data_dict(meta_data_pool, ikarus_time)
    df_balance, data_dict = await asyncio.gather(*tasks_pre_calc)

    # 1.2 Get live trade objects (LTOs)
    # NOTE: Query to get all of the LTOs that has a strategy property that is contained in 'active_strategies'
    lto_list = await mongocli.do_aggregate('live-trades',[{ '$match': { 'strategy': {'$in': list(strategy_period_mapping.keys()) }} }])

    # 1.3: Query the status of LTOs from the Broker
    # 1.4: Update the LTOs
    lto_list = await update_ltos(lto_list, data_dict, strategy_period_mapping, df_balance)
    #################### Phase 2: Perform calculation tasks ####################

    # 2.1: Analyzer only provide the simplified informations, it does not make any decision
    analysis_dict = await asyncio.create_task(analyzer.sample_analyzer(data_dict))

    # 2.2: Algorithm is the only authority to make decision
    #nto_list = await asyncio.create_task(strategy_list[0].run(analysis_dict, lto_list, df_balance, current_ts)) # Send the last timestamp index
    # NOTE: Group the LTOs: It is only required here since only each strategy may know what todo with its own LTOs
    grouped_ltos = {}
    for strategy,lto in groupby(lto_list,key= operator.itemgetter("strategy")):
        grouped_ltos[strategy] = list(lto)

    strategy_tasks = []
    for strategy in strategy_list:
        strategy_tasks.append(asyncio.create_task(strategy.run(analysis_dict, grouped_ltos.get(strategy.name, []), df_balance, ikarus_time)))
    
    # TODO: NEXT: Currently all the pairs of a strategy can create LTO at the same time. But is this what is desired?
    strategy_decisions = list(await asyncio.gather(*strategy_tasks))
    nto_list = list(chain(*strategy_decisions))

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
    await write_updated_ltos_to_db(lto_list)

    # 3.3: Get the onserver
    observation_obj = await observer.sample_observer(df_balance)
    observation_obj.load('timestamp',ikarus_time)
    await mongocli.do_insert_one("observer",observation_obj.get())

    pass


async def main():

    # NOTE: Temporary hack for yesting without internet connection
    client = await AsyncClient.create(api_key=cred_info['Binance']['Production']['PUBLIC-KEY'],
                                      api_secret=cred_info['Binance']['Production']['SECRET-KEY'])
    bwrapper = binance_wrapper.TestBinanceWrapper(client, config)

    all_pairs = [strategy['pairs'] for name, strategy in config['strategy'].items()]
    all_pairs = list(set(itertools.chain(*all_pairs)))
    symbol_info = await bwrapper.get_all_symbol_info(all_pairs)

    # TODO: Actually no need to make symbol_info a member of the instances, it is better to have it as 
    strategy_mgr = strategy_manager.StrategyManager(config, symbol_info)
    strategy_list = strategy_mgr.get_strategies()

    strategy_periods = set()
    for strategy in strategy_list:
        if strategy.name in config['strategy'].keys():
            strategy_periods.add(strategy.min_period)

    ikarus_cycle_period = await get_min_scale(config['time_scales'].keys(), strategy_periods)
    if ikarus_cycle_period == '': raise ValueError('No ikarus_cycle_period specified')

    # Init the df_tickers to not to call binance API in each iteration
    binance_wrapper.TestBinanceWrapper.df_tickers = await bwrapper.get_all_tickers()

    # Initiate the cash in the [observer]
    initial_observation_item = {
        'balances': config['balances']
    }
    await mongocli.do_insert_one("observer", initial_observation_item)   

    # Evaluate start and end times
    session_start_time = datetime.strptime(config['backtest']['start_time'], "%Y-%m-%d %H:%M:%S")
    session_start_timestamp = int(datetime.timestamp(session_start_time))
    session_end_time = datetime.strptime(config['backtest']['end_time'], "%Y-%m-%d %H:%M:%S")
    session_end_timestamp = int(datetime.timestamp(session_end_time))

    # Iterate through the time stamps
    total_len = int((session_end_timestamp - session_start_timestamp) / time_scale_to_second(ikarus_cycle_period)) # length = Second / Min*60
    printProgressBar(0, total_len, prefix = 'Progress:', suffix = 'Complete', length = 50)

    for idx, start_time in enumerate(range(session_start_timestamp, session_end_timestamp, time_scale_to_second(ikarus_cycle_period))):
        logger.debug(f'Iteration {idx}:')
        printProgressBar(idx + 1, total_len, prefix = 'Progress:', suffix = 'Complete', length = 50)

        await application(strategy_list, bwrapper, start_time)

    # Evaluate the statistics
    await stats.main()

    # Get [hist-trades] docs to visualize the session
    await visualize_online(bwrapper, mongocli, config)
    pass
    # Visualize the test session
    # TODO: Get the df
    #fplot.buy_sell(df=df, df_closed=df_closed_hto, df_enter_expire=df_enter_expire, df_exit_expire=df_exit_expire)


if __name__ == '__main__':
    
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    logger = logging.getLogger('app')
    mongocli = mongo_utils.MongoClient(config['mongodb']['host'], 
        config['mongodb']['port'], 
        config['tag'],
        clean=config['mongodb']['clean'])
    
    # Initialize and configure objects
    setup_logger(config['log-level'])

    # Setup initial objects
    stats = performance.Statistics(config, mongocli) 
    observer = observers.Observer()
    analyzer = analyzers.Analyzer(config)

    logger.info("---------------------------------------------------------")
    logger.info("------------------- Engine Restarted --------------------")
    logger.info("---------------------------------------------------------")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    print(f"Test Session <{config['tag']}> completed")