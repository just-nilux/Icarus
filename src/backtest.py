from Ikarus.objects import *
import asyncio
from binance import AsyncClient
from datetime import datetime
import json
from Ikarus.brokers.backtest_wrapper import BacktestWrapper, sync_trades_of_backtest
from Ikarus import strategy_manager, analyzers, mongo_utils, trade_statistics
from Ikarus.utils import time_scale_to_second, get_min_scale, round_to_period, eval_total_capital, \
    eval_total_capital_in_lto, setup_logger
import logging
import sys
import bson
from itertools import chain
import itertools
from Ikarus import resource_allocator

def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    logger.debug(f'Progress: {percent}%')
    # Print New Line on Complete
    if iteration == total: 
        print()


async def application(strategy_list, strategy_res_allocator, bwrapper, ikarus_time):

    if str(ikarus_time*1000) in config['backtest'].get('breakpoints',{}).keys():
        logger.debug(f"Stopped at breakpoint \"{config['backtest']['breakpoints'][str(ikarus_time*1000)]}\": {ikarus_time}")

    
    # The close time of the last_kline + 1ms, corresponds to the open_time of the future kline which is actually the kline we are in. 
    # If the execution takes 2 second, then the order execution and the updates will be done
    # 2 second after the new kline started. But the analysis will be done based on the last closed kline
    logger.info(f'Ikarus Time: [{ikarus_time}]') # UTC

    # TODO: give index paramter to retrieve a single object instead of a list
    info = await mongocli.get_n_docs('observer', {'type':EObserverType.BALANCE}) # Default is the last doc

    
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

    tasks_pre_calc = bwrapper.get_current_balance(info[0]), bwrapper.get_data_dict_download(meta_data_pool, ikarus_time)
    df_balance, data_dict = await asyncio.gather(*tasks_pre_calc)

    # NOTE: Query to get all of the LTOs that has a strategy property that is contained in 'active_strategies'
    live_trade_dicts = await mongocli.do_aggregate('live-trades',[{ '$match': { 'strategy': {'$in': list(strategy_period_mapping.keys()) }} }])

    live_trade_list = [trade_from_dict(trade_dict) for trade_dict in live_trade_dicts]
    await sync_trades_of_backtest(live_trade_list, data_dict, strategy_period_mapping, df_balance, config['broker']['quote_currency'])

    analysis_dict = await analyzer.analyze(data_dict)

    # NOTE: Group the LTOs: It is only required here since only each strategy may know what todo with its own LTOs
    # Total usable qc
    total_qc = eval_total_capital(df_balance, live_trade_list, config['broker']['quote_currency'], config['strategy_allocation']['kwargs']['max_capital_use'])
    
    total_qc_in_lto = eval_total_capital_in_lto(live_trade_list) # Total used qc in lto
    logger.info(f'Total QC: {total_qc}, Total amount of LTO: {total_qc_in_lto}')

    strategy_resources = strategy_res_allocator.allocate(df_balance, live_trade_list)

    grouped_ltos = {}
    for live_trade in live_trade_list:
        grouped_ltos.setdefault(live_trade.strategy, []).append(live_trade)

    strategy_tasks = []
    for active_strategy in active_strategies:
        strategy_tasks.append(asyncio.create_task(active_strategy.run(
            analysis_dict, 
            grouped_ltos.get(active_strategy.name, []), 
            ikarus_time, 
            strategy_resources[active_strategy.name])))

    strategy_decisions = list(await asyncio.gather(*strategy_tasks))
    new_trade_list = list(chain(*strategy_decisions)) # TODO: NEXT: Strategy output is only nto but it edits the ltos as well, so return ltos too

    if len(new_trade_list) or len(live_trade_list):
        # NOTE: If there is any error during execution, then it the trade can be removed/fixed and the error can be handled inside the execute_decisison
        bwrapper.execute_decision(new_trade_list, df_balance, live_trade_list)

    new_trade_list = [i for i in new_trade_list if i is not None]

    if len(new_trade_list):
        # Write trade_dict to [live-trades] (assume it is executed successfully)
        result = await mongocli.do_insert_many("live-trades", [trade_to_dict(new_trade) for new_trade in new_trade_list])

    await mongo_utils.update_live_trades(mongocli, live_trade_list)

    obs_strategy_capitals = Observer('strategy_capitals', ts=ikarus_time, data=strategy_res_allocator.strategy_capitals).to_dict()

    observer_item = list(df_balance.reset_index(level=0).T.to_dict().values())
    obs_balance = Observer(EObserverType.BALANCE, ts=ikarus_time, data=observer_item).to_dict()

    observation_obj = {}
    observation_obj['free'] = df_balance.loc[config['broker']['quote_currency'],'free']
    observation_obj['in_trade'] = eval_total_capital_in_lto(live_trade_list+new_trade_list)
    observation_obj['total'] = observation_obj['free'] + observation_obj['in_trade']
    obs_quote_asset = Observer(EObserverType.QUOTE_ASSET, ts=ikarus_time, data=observation_obj).to_dict()

    observation_obj = {}
    free = df_balance.loc[config['broker']['quote_currency'],'free']
    in_trade = eval_total_capital_in_lto(live_trade_list+new_trade_list)
    observation_obj['total'] = safe_sum(free, in_trade)
    observation_obj['ideal_free'] = safe_multiply(observation_obj['total'], safe_substract(1, config['strategy_allocation']['kwargs']['max_capital_use']))
    observation_obj['real_free'] = free
    observation_obj['binary'] = int(observation_obj['ideal_free'] < observation_obj['real_free'])

    obs_quote_asset_leak = Observer('quote_asset_leak', ts=ikarus_time, data=observation_obj).to_dict()

    # TODO: NEXT: Observer configuration needs to be implemented just like analyzers
    observer_list = [
        obs_quote_asset,
        obs_quote_asset_leak,
        obs_balance,
        obs_strategy_capitals
    ]
    #observer_objs = list(await asyncio.gather(*observer_list))
    await mongocli.do_insert_many("observer", observer_list)

    pass


async def main():

    # Create a Async Binance client and receive initial information
    client = await AsyncClient.create(**cred_info['Binance']['Production'])
    bwrapper = BacktestWrapper(client, config)
    all_pairs = [strategy['pairs'] for strategy in config['strategy'].values()]
    all_pairs = list(set(itertools.chain(*all_pairs)))
    symbol_info = await bwrapper.get_all_symbol_info(all_pairs)

    # Create Strategy Manager and configure strategies
    strategy_mgr = strategy_manager.StrategyManager(config, symbol_info, mongocli)
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
    BacktestWrapper.df_tickers = await bwrapper.get_all_tickers()

    # Initiate the cash in the [observer]
    initial_observer = Observer(EObserverType.BALANCE, None, config['balances']).to_dict()
    await mongocli.do_insert_one("observer", initial_observer)

    # Initate a ResourceAllocator for strategies
    strategywise_resource_allocator = getattr(resource_allocator, config['strategy_allocation']['type'])\
        (**config['strategy_allocation']['kwargs'])

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

    await bwrapper.obtain_candlesticks(meta_data_pool, session_start_timestamp*1000, session_end_timestamp*1000)

    for idx, start_time in enumerate(range(session_start_timestamp, session_end_timestamp, time_scale_to_second(ikarus_cycle_period))):
        logger.debug(f'Iteration {idx}:')
        printProgressBar(idx + 1, total_len, prefix = 'Progress:', suffix = 'Complete', length = 50)
        
        await application(strategy_list, strategywise_resource_allocator, bwrapper, start_time)

    # Evaluate the statistics
    # await trade_statistics.main(config, mongocli)


if __name__ == '__main__':
    
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)

    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    logger = logging.getLogger('app')
    mongocli = mongo_utils.MongoClient(**config['mongodb'])
    
    # Initialize and configure objects
    setup_logger(logger, config['log'])

    # Setup initial objects
    analyzer = analyzers.Analyzer(config)

    logger.info("---------------------------------------------------------")
    logger.info("------------------- Engine Restarted --------------------")
    logger.info("---------------------------------------------------------")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    print(f"Test Session <{config['tag']}> completed")