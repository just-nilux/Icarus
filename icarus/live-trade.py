from objects import *
import asyncio
from binance import AsyncClient
from datetime import datetime
import json
from brokers.binance_wrapper import BinanceWrapper, sync_trades_with_orders
import strategy_manager, analyzers, mongo_utils
from exceptions import SysStatDownException
from utils import time_scale_to_second, get_min_scale, round_to_period, eval_total_capital, \
    eval_total_capital_in_lto, setup_logger
import logging
import sys
import itertools
import resource_allocator
from resource_allocator import DiscreteStrategyAllocator

from connectivity.telegram_wrapper import TelegramBot
from connectivity.trading import init_telegram_bot, start_telegram_bot, enable_broker_interface


# Global Variables
FLAG_SYSTEM_STATUS = True


async def wait_until(dt):
    now = int(datetime.timestamp(datetime.now())) # UTC
    sleep_time = dt - now
    print("Next local start time: {} | [{}] UTC\nNow local: {} | [{}] UTC\nSleeptime: {}\n".format(datetime.fromtimestamp(dt), dt, datetime.fromtimestamp(now), now, sleep_time))
    await asyncio.sleep(dt - now)


async def run_at(dt, coro):
    await wait_until(dt)
    return await coro


async def application(strategy_list, strategy_res_allocator: DiscreteStrategyAllocator, broker_client, ikarus_time):
    logger.info(f'Ikarus Time: [{ikarus_time}]') # UTC
    
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
    meta_data_pool = set(itertools.chain(*meta_data_pool))

    # Query to get all of the trades that has a strategy property that is contained in 'active_strategies'
    live_trade_dicts = await mongocli.do_aggregate('live-trades',[{ '$match': { 'strategy': {'$in': list(strategy_period_mapping.keys()) }} }])
    live_trades = [trade_from_dict(trade_dict) for trade_dict in live_trade_dicts]

    df_balance, data_dict = await asyncio.gather(*[
        broker_client.get_current_balance(),
        broker_client.get_data_dict(meta_data_pool, ikarus_time)
        ]
    )
    logger.info(f'Current Balance: \n{df_balance.to_string()}')

    orders = await broker_client.get_trade_orders(live_trades)

    _, analysis_dict = await asyncio.gather(*[
        sync_trades_with_orders(live_trades, data_dict, strategy_period_mapping, orders),
        analyzer.analyze(data_dict)]
    )

    # NOTE: Group the LTOs: It is only required here since only each strategy may know what todo with its own LTOs
    strategy_resources = strategy_res_allocator.allocate(df_balance, live_trades)

    grouped_ltos = {}
    for trade in live_trades:
        grouped_ltos.setdefault(trade.strategy, []).append(trade)

    strategy_tasks = []
    for active_strategy in active_strategies:
        strategy_tasks.append(asyncio.create_task(active_strategy.run(
            analysis_dict, 
            grouped_ltos.get(active_strategy.name, []), 
            ikarus_time, 
            strategy_resources[active_strategy.name])))

    strategy_decisions = list(await asyncio.gather(*strategy_tasks))
    new_trades = list(itertools.chain(*strategy_decisions)) # TODO: NEXT: Strategy output is only nto but it edits the ltos as well, so return ltos too

    if len(new_trades) or len(live_trades):
        #nto_list, lto_list = await asyncio.create_task(bwrapper.execute_decision(nto_list, lto_list))
        await broker_client.execute_decision(new_trades+live_trades)

    new_trades = [i for i in new_trades if i is not None]

    if len(new_trades):
        result = await mongocli.do_insert_many("live-trades", [trade_to_dict(trade) for trade in new_trades])

    await mongo_utils.update_live_trades(mongocli, live_trades)


    df_balance = await broker_client.get_current_balance()
    logger.debug(f'Current Balance after execution: \n{df_balance.to_string()}')

    obs_strategy_capitals = Observer('strategy_capitals', ts=ikarus_time, data=strategy_res_allocator.strategy_capitals).to_dict()

    observer_item = list(df_balance.reset_index(level=0).T.to_dict().values())
    obs_balance = Observer(EObserverType.BALANCE, ts=ikarus_time, data=observer_item).to_dict()

    observation_obj = {}
    observation_obj['free'] = df_balance.loc[config['broker']['quote_currency'],'free']
    observation_obj['in_trade'] = eval_total_capital_in_lto(live_trades+new_trades)
    observation_obj['total'] = observation_obj['free'] + observation_obj['in_trade']
    obs_quote_asset = Observer(EObserverType.QUOTE_ASSET, ts=ikarus_time, data=observation_obj).to_dict()

    '''
    # NOTE: capital_limit is not integrated to this leak evaluation 
    observation_obj = {}
    free = df_balance.loc[config['broker']['quote_currency'],'free']
    in_trade = eval_total_capital_in_lto(live_trade_list+new_trade_list)
    observation_obj['total'] = safe_sum(free, in_trade)
    observation_obj['ideal_free'] = safe_multiply(observation_obj['total'], safe_substract(1, config['strategy_allocation']['kwargs']['capital_coeff']))
    observation_obj['real_free'] = free
    observation_obj['binary'] = int(observation_obj['ideal_free'] < observation_obj['real_free'])

    obs_quote_asset_leak = Observer('quote_asset_leak', ts=ikarus_time, data=observation_obj).to_dict()
    '''

    # TODO: NEXT: Observer configuration needs to be implemented just like analyzers
    observer_list = [
        obs_quote_asset,
        #obs_quote_asset_leak,
        obs_balance,
        obs_strategy_capitals
    ]
    #observer_objs = list(await asyncio.gather(*observer_list))
    await mongocli.do_insert_many("observer", observer_list)

async def main():
    client = await AsyncClient.create(**cred_info['Binance']['Test'])
    broker_client = BinanceWrapper(client, config)
    enable_broker_interface(BinanceWrapper, client, config)
    start_telegram_bot()
    print(await broker_client.get_current_balance())
    all_pairs = [strategy['pairs'] for strategy in config['strategy'].values()]
    all_pairs = list(set(itertools.chain(*all_pairs)))
    symbol_info = await broker_client.get_all_symbol_info(all_pairs)

    # Create Strategy Manager and configure strategies
    strategy_mgr = strategy_manager.StrategyManager(config, symbol_info, mongocli)
    strategy_list = strategy_mgr.get_strategies()

    strategy_periods = set()
    for strategy in strategy_list:
        if strategy.name in config['strategy'].keys():
            strategy_periods.add(strategy.min_period)

    # Initate a ResourceAllocator for strategies
    strategy_res_allocator = getattr(resource_allocator, config['strategy_allocation']['type'])\
        (**config['strategy_allocation']['kwargs'])

    ikarus_cycle_period = get_min_scale(config['time_scales'].keys(), strategy_periods)
    if ikarus_cycle_period == '': raise ValueError('No ikarus_cycle_period specified')
    ikarus_cycle_period_in_sec = time_scale_to_second(ikarus_cycle_period)

    while True:
        try:
            broker_status = await asyncio.wait_for(broker_client.get_status(), timeout=10)
            logger.debug(f'System status: {broker_status}')

            if broker_status != 0:
                raise SysStatDownException()

            current_time = await broker_client.get_time() # UTC
            logger.debug(f'Server time: {current_time}, ({datetime.fromtimestamp(current_time)})')


            start_time_offset = 10
            next_start_time = round_to_period(current_time, ikarus_cycle_period_in_sec, direction='ceiling', offset=start_time_offset)

            logger.debug(f'Cycle start time: {next_start_time}, ({datetime.fromtimestamp(next_start_time)})')
            result = await asyncio.create_task(run_at(next_start_time, application(strategy_list, strategy_res_allocator, broker_client, next_start_time-start_time_offset)))
            
            '''
            # NOTE: The logic below is for gathering data every 'period' seconds (Good for testing and not waiting)
            await asyncio.gather(
                asyncio.sleep(10),
                application(bwrapper, telbot),
            )
            '''
        except SysStatDownException as e:
            logger.error(str(e))
            TelegramBot.send_formatted_message('error', [str(e)])
            await asyncio.sleep(60)

        except asyncio.TimeoutError as e:
            logger.error(str(e))
            TelegramBot.send_formatted_message('error', [str(e)])
            await asyncio.sleep(60)

        except Exception as e:
            logger.error(str(e))
            #telbot.send_constructed_msg('error', str(e))
            
            
    await broker_client.close_connection()

def aexec(func):
    global loop
    def wrapper(update, context):
        
        asyncio.set_event_loop(loop)
        #loop.run_until_complete(func(update, context))
        #loop.close()
        asyncio.run(func(update, context))
    return wrapper

@aexec
async def dummy_func(update, context):
    global broker_client
    print("dummy_func")
    await broker_client.get_current_balance()

if __name__ == "__main__":
    
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    logger = logging.getLogger('app')
    mongocli = mongo_utils.MongoClient(**config['mongodb'])

    # Initialize and configure objects
    setup_logger(logger, config['log'])

    # Initialize telegram bot
    init_telegram_bot(cred_info['Telegram']['token'], cred_info['Telegram']['chat_id'])

    # Setup initial objects
    analyzer = analyzers.Analyzer(config)

    logger.info("---------------------------------------------------------")
    logger.info("------------------- Engine Restarted --------------------")
    logger.info("---------------------------------------------------------")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())