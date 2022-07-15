from Ikarus.objects import *
from Ikarus.strategies.StrategyBase import StrategyBase
import asyncio
from binance import AsyncClient
from datetime import datetime
import json
from Ikarus import binance_wrapper, strategy_manager, analyzers, observers, mongo_utils, trade_statistics
from Ikarus.utils import time_scale_to_second, get_min_scale, round_to_period, eval_total_capital, \
    eval_total_capital_in_lto, setup_logger
import logging
import pandas as pd
import sys
import os
import bson
from itertools import chain
import itertools
from Ikarus.resource_allocator import ResourceAllocator 
from Ikarus import balance_manager

# Global Variables
SYSTEM_STATUS = 0
STATUS_TIMEOUT = 0

def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()


async def write_updated_ltos_to_db(trade_list): # TODO: REFACTOR: checkout
    # TODO: Move queries outside of this script
    for trade in trade_list:

        # NOTE: Check for status change is removed since some internal changes might have been performed on status and needs to be reflected to history
        # If the status is closed then, it should be inserted to [hist-trades] and deleted from the [live-trades]
        if trade.status == EState.CLOSED:
            # This if statement combines the "update the [live-trades]" and "delete the closed [live-trades]"
            result_insert = await mongocli.do_insert_one("hist-trades",asdict(trade))
            result_remove = await mongocli.do_delete_many("live-trades",{"_id":trade._id}) # "do_delete_many" does not hurt, since the _id is unique

            if trade.result.cause == ECause.CLOSED:
                hto_stat = trade_statistics.eval_hto_stat(trade) # TODO : REFACTORING
                pass

        # NOTE: Manual trade option is omitted, needs to be added
        # TODO: REFACTORING: Why did you handle all of these 3 state in the same place?
        elif trade.status in [ EState.OPEN_EXIT, EState.WAITING_EXIT, EState.EXIT_EXP]:
            result_update = await mongocli.do_update( 
                "live-trades",
                {'_id': trade._id},
                {'$set': {'status': trade.status,
                        'exit': asdict(trade.exit),
                        'result.enter': asdict(trade.result.enter),
                        'order_stash': [asdict(order) for order in trade.order_stash]
                    }})
                
        elif trade.status == EState.OPEN_ENTER:
            # - STAT_OPEN_ENTER might be expired and postponed with some additional changes in 'enter' item (changes in enter and history)
            result_update = await mongocli.do_update( 
                "live-trades",
                {'_id': trade._id},
                {'$set': {'status': trade.status, 'enter': asdict(trade.enter) }}) # NOTE: REFACTORING: history removed

        else:
            pass


async def update_ltos(trade_list, data_dict, strategy_period_mapping, df_balance):
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

    for i in range(len(trade_list)):
        pair = trade_list[i].pair

        # 1.2.1: Check trades and update status
        strategy_min_scale = strategy_period_mapping[trade_list[i].strategy]
        last_kline = data_dict[pair][strategy_min_scale].tail(1)
        last_closed_candle_open_time = bson.Int64(last_kline.index.values[0])
        base_cur = pair.replace(config['broker']['quote_currency'],'')

        if trade_list[i].status == EState.OPEN_ENTER:
            # NOTE: There is 2 method to enter: TYPE_LIMIT and TYPE_MARKET. Since market executed directly, it is not expected to have market at this stage
            if type(trade_list[i].enter) == Limit:

                # Check if the open enter trade is filled else if the trade is expired
                if float(last_kline['low']) < trade_list[i].enter.price:

                    # TODO: If the enter is successful then the exit order should be placed. This is only required in DEPLOY
                    
                    trade_list[i].set_result_enter(last_closed_candle_open_time, fee_rate=StrategyBase.fee)
                    if not balance_manager.buy(df_balance, config['broker']['quote_currency'], base_cur, trade_list[i].result.enter):
                        logger.error(f"Function failed: balance_manager.buy().")
                        # TODO: Fix the logic. The balance manager should be called prior

                elif int(trade_list[i].enter.expire) <= last_closed_candle_open_time:
                    # Report the expiration to algorithm
                    trade_list[i].status = EState.ENTER_EXP
                    # NOTE: No update on command because it is, only placed by the strategies

            else:
                # TODO: Internal Error
                pass

        elif trade_list[i].status == EState.OPEN_EXIT:

            if type(trade_list[i].exit) == Limit:

                # Check if the open sell trade is filled or stoploss is taken
                if float(last_kline['high']) > trade_list[i].exit.price:

                    trade_list[i].set_result_exit(last_closed_candle_open_time, fee_rate=StrategyBase.fee)
                    base_cur = pair.replace(config['broker']['quote_currency'],'')
                    if not balance_manager.sell(df_balance, config['broker']['quote_currency'], base_cur, trade_list[i].result.exit):
                        logger.error(f"Function failed: balance_manager.sell().")
                        # TODO: Fix the logic. The balance manager should be called prior

                elif int(trade_list[i].exit.expire) <= last_closed_candle_open_time:
                    trade_list[i].status = EState.EXIT_EXP


            elif type(trade_list[i].exit) == OCO:
                # NOTE: Think about the worst case and check the stop loss first.

                if float(last_kline['low']) < trade_list[i].exit.stop_price:
                    # Stop Loss takens
                    trade_list[i].set_result_exit(last_closed_candle_open_time,
                        cause=ECause.CLOSED_STOP_LIMIT, #TODO: REFACTORING: Checkout if it is good to have stoploss or not
                        price=trade_list[i].exit.stop_limit_price,
                        fee_rate=StrategyBase.fee)

                    base_cur = pair.replace(config['broker']['quote_currency'],'')
                    balance_manager.sell(df_balance, config['broker']['quote_currency'], base_cur, trade_list[i].result.exit)
                
                elif float(last_kline['high']) > trade_list[i].exit.price:
                    # Limit taken
                    trade_list[i].set_result_exit(last_closed_candle_open_time,
                        fee_rate=StrategyBase.fee)

                    base_cur = pair.replace(config['broker']['quote_currency'],'')
                    if not balance_manager.sell(df_balance, config['broker']['quote_currency'], base_cur, trade_list[i].result.exit):
                        logger.error(f"Function failed: balance_manager.sell().")
                        # TODO: Fix the logic. The balance manager should be called prior

                elif int(trade_list[i].exit.expire) <= last_closed_candle_open_time:
                    trade_list[i].status = EState.EXIT_EXP

                else:
                    pass

            else:
                # TODO: Internal Error
                pass

        else:
            # TODO: Internal Error
            pass



async def application(strategy_list, bwrapper, ikarus_time):

    if str(ikarus_time*1000) in config['backtest'].get('breakpoints',{}).keys():
        logger.debug(f"Stopped at breakpoint \"{config['backtest']['breakpoints'][str(ikarus_time*1000)]}\": {ikarus_time}")

    # NOTE: 'ikarus-time' denotes the current_time in old implementation
    #################### Phase 1: Perform pre-calculation tasks ####################
    
    # The close time of the last_kline + 1ms, corresponds to the open_time of the future kline which is actually the kline we are in. 
    # If the execution takes 2 second, then the order execution and the updates will be done
    # 2 second after the new kline started. But the analysis will be done based on the last closed kline
    logger.info(f'Ikarus Time: [{ikarus_time}]') # UTC

    # 1.1 Get balance and datadict,
    # TODO: give index paramter to retrieve a single object instead of a list
    info = await mongocli.get_n_docs('observer', {'type':'balance'}) # Default is the last doc
    # NOTE:info given to the get_current_balance only for test-engine.p
    
    # Each strategy has a min_period. Thus I can iterate over it to see the matches between the current time and their period
    meta_data_pool = []
    active_strategies = []
    strategy_period_mapping = {}
    # NOTE: Active Strategies is used to determine the strategies and gather the belonging LTOs
    for strategy_obj in strategy_list:
        if ikarus_time % time_scale_to_second(strategy_obj.min_period) == 0:
            meta_data_pool.append(strategy_obj.meta_do)
            strategy_period_mapping[strategy_obj.name] = strategy_obj.min_period
            active_strategies.append(strategy_obj) # Create a copy of each strategy object

    ikarus_time = ikarus_time * 1000 # Convert to ms
    meta_data_pool = set(chain(*meta_data_pool))

    # All you need to give to data_dcit is actually the (time_scale, pair) tuples and the ikarus_time
    tasks_pre_calc = bwrapper.get_current_balance(info[0]), bwrapper.get_data_dict_download(meta_data_pool, ikarus_time)
    df_balance, data_dict = await asyncio.gather(*tasks_pre_calc)

    # 1.2 Get live trade objects (LTOs)
    # NOTE: Query to get all of the LTOs that has a strategy property that is contained in 'active_strategies'
    live_trade_dicts = await mongocli.do_aggregate('live-trades',[{ '$match': { 'strategy': {'$in': list(strategy_period_mapping.keys()) }} }])

    # 1.3: Query the status of LTOs from the Broker
    # 1.4: Update the LTOs
    live_trade_list = [trade_from_dict(trade_dict) for trade_dict in live_trade_dicts]
    await update_ltos(live_trade_list, data_dict, strategy_period_mapping, df_balance)

    # 2.1: Analyzer only provide the simplified informations, it does not make any decision
    analysis_dict = await analyzer.sample_analyzer(data_dict)

    #################### Phase 2: Perform calculation tasks ####################

    # 2.2: Algorithm is the only authority to make decision
    # NOTE: Group the LTOs: It is only required here since only each strategy may know what todo with its own LTOs
    logger.debug('Phase 2')
    # Total usable qc
    total_qc = eval_total_capital(df_balance, live_trade_list, config['broker']['quote_currency'], config['risk_management']['max_capital_use_ratio'])
    
    # Total qc in use. Thus total_qc >= total_qc_in_lto
    total_qc_in_lto = eval_total_capital_in_lto(live_trade_list) # Total used qc in lto
    logger.info(f'Total QC: {total_qc}, Total amount of LTO: {total_qc_in_lto}')

    grouped_ltos = {}
    for live_trade in live_trade_list:
        grouped_ltos.setdefault(live_trade.strategy, []).append(live_trade)

    strategy_tasks = []
    for active_strategy in active_strategies:
        strategy_tasks.append(asyncio.create_task(active_strategy.run(
            analysis_dict, 
            grouped_ltos.get(active_strategy.name, []), 
            ikarus_time, 
            total_qc, 
            df_balance.loc[config['broker']['quote_currency'],'free'])))

    strategy_decisions = list(await asyncio.gather(*strategy_tasks))
    new_trade_list = list(chain(*strategy_decisions)) # TODO: NEXT: Strategy output is only nto but it edits the ltos as well, so return ltos too

    # 2.3: Execute LTOs and NTOs if any
    if len(new_trade_list) or len(live_trade_list):
        # 2.3.1: Execute the TOs
        # NOTE: If there is any error during execution, then it the trade can be removed/fixed and the error can be handled inside the execute_decisison
        bwrapper.execute_decision(new_trade_list, df_balance, live_trade_list, data_dict)
        # TODO: Investigate if the lto_list and the nto_list is updated directly (which means no need for re-assignment)

    #################### Phase 3: Perform post-calculation tasks ####################

    if len(new_trade_list):
        # 3.1: Write trade_dict to [live-trades] (assume it is executed successfully)
        result = await mongocli.do_insert_many("live-trades", [trade_to_dict(new_trade) for new_trade in new_trade_list])         # TODO: TEST_REFACTORING


    # 3.2: Write the LTOs and NTOs to [live-trades] and [hist-trades]
    await write_updated_ltos_to_db(live_trade_list)

    # 3.3: Get the onserver
    # TODO: NEXT: Observer configuration needs to be implemented just like analyzers
    observer_list = [
        observer.quote_asset(ikarus_time, df_balance, live_trade_list+new_trade_list),
        observer.quote_asset_leak(ikarus_time, df_balance, live_trade_list+new_trade_list),
        observer.balance(ikarus_time, df_balance)
    ]
    observer_objs = list(await asyncio.gather(*observer_list))
    await mongocli.do_insert_many("observer", observer_objs)

    pass


async def main():

    # Create a Async Binance client and receive initial information
    client = await AsyncClient.create(api_key=cred_info['Binance']['Production']['PUBLIC-KEY'],
                                      api_secret=cred_info['Binance']['Production']['SECRET-KEY'])
    bwrapper = binance_wrapper.TestBinanceWrapper(client, config)
    all_pairs = [strategy['pairs'] for name, strategy in config['strategy'].items()]
    all_pairs = list(set(itertools.chain(*all_pairs)))
    symbol_info = await bwrapper.get_all_symbol_info(all_pairs)

    # Create Resource Allocator and initialize allocation for strategies
    res_allocater = ResourceAllocator(list(config['strategy'].keys()), mongocli)
    await res_allocater.allocate()
    # NOTE: This implementation uses Resource Allocator only in the boot time.
    #       For dynamic allocation (or at least updating each day/week automatically), allocator needs to
    #       create a new allocation and strategy manager needs to consume it in an cycle

    # Create Strategy Manager and configure strategies
    strategy_mgr = strategy_manager.StrategyManager(config, symbol_info, mongocli)
    await strategy_mgr.source_plugin()
    # TODO: Receive data from plugin once. This needs to be a periodic operations for each cycle if a new
    #       resource_allocation object exist
    strategy_list = strategy_mgr.get_strategies()

    meta_data_pool = []
    strategy_periods = set()
    for strategy_obj in strategy_list:
        strategy_periods.add(strategy_obj.min_period)
        meta_data_pool.append(strategy_obj.meta_do)
    meta_data_pool = set(chain(*meta_data_pool))

    ikarus_cycle_period = get_min_scale(config['time_scales'].keys(), strategy_periods)
    if ikarus_cycle_period == '': raise ValueError('No ikarus_cycle_period specified')

    # Init the df_tickers to not to call binance API in each iteration
    binance_wrapper.TestBinanceWrapper.df_tickers = await bwrapper.get_all_tickers()

    # Initiate the cash in the [observer]
    initial_observation_item = {
        'type': 'balance',
        'balances': config['balances']
    }
    await mongocli.do_insert_one("observer", initial_observation_item)

    # Evaluate start and end times
    session_start_time = datetime.strptime(config['backtest']['start_time'], "%Y-%m-%d %H:%M:%S")
    session_start_timestamp = int(datetime.timestamp(session_start_time)) # UTC
    session_end_time = datetime.strptime(config['backtest']['end_time'], "%Y-%m-%d %H:%M:%S")
    session_end_timestamp = int(datetime.timestamp(session_end_time))

    # Iterate through the time stamps
    ikarus_cycle_period_in_sec = time_scale_to_second(ikarus_cycle_period)
    session_start_timestamp = round_to_period(session_start_timestamp, ikarus_cycle_period_in_sec, direction='ceiling')
    session_end_timestamp = round_to_period(session_end_timestamp, ikarus_cycle_period_in_sec, direction='floor')

    total_len = int((session_end_timestamp - session_start_timestamp) / time_scale_to_second(ikarus_cycle_period)) # length = Second / Min*60
    printProgressBar(0, total_len, prefix = 'Progress:', suffix = 'Complete', length = 50)

    await bwrapper.download_all_data(meta_data_pool, session_start_timestamp*1000, session_end_timestamp*1000)

    for idx, start_time in enumerate(range(session_start_timestamp, session_end_timestamp, time_scale_to_second(ikarus_cycle_period))):
        logger.debug(f'Iteration {idx}:')
        printProgressBar(idx + 1, total_len, prefix = 'Progress:', suffix = 'Complete', length = 50)

        await application(strategy_list, bwrapper, start_time)

    # Evaluate the statistics
    await trade_statistics.main(config, mongocli)


if __name__ == '__main__':
    
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)

    if len(sys.argv) >=3:
        config['credential_file'] = str(sys.argv[2])

    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    logger = logging.getLogger('app')
    mongocli = mongo_utils.MongoClient(host=config['mongodb']['host'], 
        port=config['mongodb']['port'], 
        db=config['tag'],
        clean=config['mongodb']['clean'])
    
    # Initialize and configure objects
    setup_logger(logger, config['log'])

    # Setup initial objects
    observer = observers.Observer(config)
    analyzer = analyzers.Analyzer(config)

    logger.info("---------------------------------------------------------")
    logger.info("------------------- Engine Restarted --------------------")
    logger.info("---------------------------------------------------------")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    print(f"Test Session <{config['tag']}> completed")