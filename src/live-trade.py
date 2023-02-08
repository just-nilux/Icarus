from Ikarus.objects import *
from Ikarus.strategies.StrategyBase import StrategyBase
import asyncio
from binance import AsyncClient
from datetime import datetime
import json
from Ikarus.broker import BinanceWrapper, sync_trades_of_backtest
from Ikarus import strategy_manager, analyzers, mongo_utils, trade_statistics, notifications
from Ikarus.exceptions import SysStatDownException
from Ikarus.utils import time_scale_to_second, get_min_scale, round_to_period, eval_total_capital, \
    eval_total_capital_in_lto, setup_logger
import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import bson
import time
from itertools import chain
import itertools
import more_itertools
from Ikarus import resource_allocator

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


async def write_updated_ltos_to_db(lto_list):
    '''
    Consider the fact that if one of the lto execution does not work such as 'waiting_exit' execution or 
    'update' action due to 'exit_expire' which was 'open_exit' previously,
    '''
    for lto in lto_list:

        # NOTE: Check for status change is removed since some internal changes might have been performed on status and needs to be reflected to history
        # If the status is closed then, it should be inserted to [hist-trades] and deleted from the [live-trades]
        if lto['status'] == STAT_CLOSED:
            # This if statement combines the "update the [live-trades]" and "delete the closed [live-trades]"
            result_insert = await mongocli.do_insert_one("hist-trades",lto)
            result_remove = await mongocli.do_delete_many("live-trades",{"_id":lto['_id']}) # "do_delete_many" does not hurt, since the _id is unique

            if lto['result']['cause'] == STAT_CLOSED:
                hto_stat = await stats.eval_hto_stat(lto)
                telbot.send_constructed_msg('hto', *hto_stat)

        # NOTE: Manual trade option is omitted, needs to be added
        elif lto['status'] in [ STAT_OPEN_EXIT, STAT_WAITING_EXIT, STAT_EXIT_EXP]:
            '''
            STAT_OPEN_EXIT:     Enter phase might be just filled and STAT_WAITING_EXIT may turn to STAT_OPEN_EXIT if the exec succesful,
            STAT_WAITING_EXIT:  Enter phase might be just filled and STAT_WAITING_EXIT may turn to STAT_OPEN_EXIT if the exec unsuccesful,
            STAT_EXIT_EXP:      Exit_expired occured and 'update' or 'market_exit' actions are not succesfully executed
            '''
            result_update = await mongocli.do_update( 
                "live-trades",
                {'_id': lto['_id']},
                {'$set': {'status': 
                        lto['status'],
                        'exit':lto['exit'],
                        'result.enter':lto['result']['enter'],
                        'history':lto['history'],
                        'update_history':lto['update_history'],
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


async def update_ltos(lto_list, data_dict, strategy_period_mapping, orders_dict):
    """
    Args:
        lto_list (list): will be updated (status, result, exit sections)
        orders_dict (dict): 
        data_dict (dict): 

    Returns:
        list: lto_list
    """

    # NOTE: In broker, an OCO order actually 2 different orders. The solution might be:
    #       - Keep the limit order as the trade id.
    #       - If the limit_maker is FILLED then we are fine
    #       - If the limit_maker İS EXPIRED then read the tradeid of to oco_stoploss and do what needs to be done
    #       - If the limit_maker İS CANCELED they bot oco orders canceld and this is an external touch
    #       : Keep the limit_maker as the 'tradeid' of the lto and keep the oco_stoploss in that lto. If needed reach it.

    # NOTE: Each lto with enter/exit type TYPE_LIMIT has 1 order in orders_dict. However, each OCO exit has 2 orders in orders dict.
    #       len(orders_dict) >= len(lto_dict)

    for i in range(len(lto_list)):

        if lto_list[i]['status'] == STAT_WAITING_EXIT:
            # NOTE: If the condition is true, then there is no active order for that LTO, so the statement: orders_dict[orderId]
            #       will cause exception since there is no orderId
            continue

        pair = lto_list[i]['pair']

        #scale = list(data_dict[pair].keys())[0]
        #last_closed_candle_open_time = bson.Int64(data_dict[pair][scale].index[-1])  # current_candle open_time
        # NOTE: last_closed_candle_open_time is used because for the anything that happens: it happend in the last closed kline

        strategy_min_scale = strategy_period_mapping[lto_list[i]['strategy']]
        last_kline = data_dict[pair][strategy_min_scale].tail(1)
        last_closed_candle_open_time = bson.Int64(last_kline.index.values[0])

        phase_lto = get_lto_phase(lto_list[i])
        type = config['strategy'][lto_list[i]['strategy']][phase_lto]['type']
        orderId = lto_list[i][phase_lto][type]['orderId'] # Get the orderId of the exit module

        # BUG: If the lto has market enter order or simply the exit order execution failed, then the status will remain STAT_WAITING_EXIT.
        #       In this case the phase become the PHASE_EXIT and the order ID is searched for the exit order which does not exist yet
        if orders_dict[orderId]['status'] == 'CANCELED':
            logger.warning(f'LTO: "{lto_list[i]["_id"]}": canceled at the phase {phase_lto}. Order ID: {orderId}. Closing the LTO')
            telbot.send_constructed_msg('lto', *[lto_list[i]['_id'], lto_list[i]['strategy'], lto_list[i]['pair'], phase_lto, orderId, 'manually canceled'])

            # NOTE: In case of Manual Interventions, close the LTO without any change
            lto_list[i]['status'] = STAT_CLOSED
            lto_list[i]['result']['cause'] = CAUSE_MANUAL_CHANGE
            lto_list[i]['result']['exit']['time'] = last_closed_candle_open_time

            if lto_list[i]['result']['enter']['time'] != '':
                lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']

            # Skip the rest of the evaluation since the LTO exposed to manual change
            continue

        if lto_list[i]['status'] == STAT_OPEN_ENTER:
            if TYPE_LIMIT in lto_list[i]['enter'].keys():
                
                enter_orderId = lto_list[i]['enter'][TYPE_LIMIT]['orderId'] # Get the orderId of the enter module
                # Check if the open enter trade is filled else if the trade is expired
                if orders_dict[enter_orderId]['status'] == 'FILLED':

                    lto_list[i]['status'] = STAT_WAITING_EXIT
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['enter']['type'] = TYPE_LIMIT
                    lto_list[i]['result']['enter']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['enter']['price'] = float(orders_dict[enter_orderId]['price'])
                    lto_list[i]['result']['enter']['quantity'] = float(orders_dict[enter_orderId]['executedQty'])
                    lto_list[i]['result']['enter']['amount'] = float(lto_list[i]['result']['enter']['price'] * lto_list[i]['result']['enter']['quantity'])
                    lto_list[i]['result']['enter']['fee'] = calculate_fee(lto_list[i]['result']['enter']['amount'], StrategyBase.fee)
                    telbot.send_constructed_msg('lto', *[lto_list[i]['_id'], lto_list[i]['strategy'], lto_list[i]['pair'], 'enter', enter_orderId, 'filled'])


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
                exit_orderId = lto_list[i]['exit'][TYPE_LIMIT]['orderId'] # Get the orderId of the exit module
                # Check if the open sell trade is filled or stoploss is taken
                if orders_dict[exit_orderId]['status'] == 'FILLED':

                    lto_list[i]['status'] = STAT_CLOSED
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['cause'] = STAT_CLOSED

                    lto_list[i]['result']['exit']['type'] = TYPE_LIMIT
                    lto_list[i]['result']['exit']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['exit']['price'] = float(orders_dict[exit_orderId]['price'])
                    lto_list[i]['result']['exit']['quantity'] = float(orders_dict[exit_orderId]['executedQty'])
                    lto_list[i]['result']['exit']['amount'] = float(lto_list[i]['result']['exit']['price'] * lto_list[i]['result']['exit']['quantity'])
                    lto_list[i]['result']['exit']['fee'] = calculate_fee(lto_list[i]['result']['exit']['amount'], StrategyBase.fee)

                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] \
                        - lto_list[i]['result']['enter']['amount'] \
                        - lto_list[i]['result']['enter']['fee'] \
                        - lto_list[i]['result']['exit']['fee']
                    lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']

                    telbot.send_constructed_msg('lto', *[lto_list[i]['_id'], lto_list[i]['strategy'], lto_list[i]['pair'], 'exit', exit_orderId, 'filled'])

                elif int(lto_list[i]['exit'][TYPE_LIMIT]['expire']) <= last_closed_candle_open_time:
                    lto_list[i]['status'] = STAT_EXIT_EXP
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    
                else:
                    pass

            elif TYPE_OCO in lto_list[i]['exit'].keys():
                oco_limit_orderId = lto_list[i]['exit'][TYPE_OCO]['orderId'] # Get the orderId of the enter module
                oco_stopLimit_orderId = lto_list[i]['exit'][TYPE_OCO]['stopLimit_orderId'] # Get the orderId of the enter module

                if orders_dict[oco_limit_orderId]['status'] == 'EXPIRED' and orders_dict[oco_stopLimit_orderId]['status'] == 'FILLED':

                    # Stop Loss takens
                    lto_list[i]['status'] = STAT_CLOSED
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['cause'] = STAT_CLOSED
                    lto_list[i]['result']['exit']['type'] = 'oco_stoploss'
                    lto_list[i]['result']['exit']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['exit']['price'] = float(orders_dict[oco_stopLimit_orderId]['price'])
                    lto_list[i]['result']['exit']['quantity'] = float(orders_dict[oco_stopLimit_orderId]['executedQty'])
                    lto_list[i]['result']['exit']['amount'] = float(lto_list[i]['result']['exit']['price'] * lto_list[i]['result']['exit']['quantity'])
                    lto_list[i]['result']['exit']['fee'] = calculate_fee(lto_list[i]['result']['exit']['amount'], StrategyBase.fee)

                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] \
                        - lto_list[i]['result']['enter']['amount'] \
                        - lto_list[i]['result']['enter']['fee'] \
                        - lto_list[i]['result']['exit']['fee']
                    lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']
                    
                    telbot.send_constructed_msg('lto', *[lto_list[i]['_id'], lto_list[i]['strategy'], lto_list[i]['pair'], 'exit', oco_stopLimit_orderId, 'filled'])

                elif orders_dict[oco_limit_orderId]['status'] == 'FILLED' and orders_dict[oco_stopLimit_orderId]['status'] == 'EXPIRED':

                    # Limit taken
                    lto_list[i]['status'] = STAT_CLOSED
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['cause'] = STAT_CLOSED

                    lto_list[i]['result']['exit']['type'] = 'oco_limit'
                    lto_list[i]['result']['exit']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['exit']['price'] = float(orders_dict[oco_limit_orderId]['price'])
                    lto_list[i]['result']['exit']['quantity'] = float(orders_dict[oco_limit_orderId]['executedQty'])
                    lto_list[i]['result']['exit']['amount'] = float(lto_list[i]['result']['exit']['price'] * lto_list[i]['result']['exit']['quantity'])
                    lto_list[i]['result']['exit']['fee'] = calculate_fee(lto_list[i]['result']['exit']['amount'], StrategyBase.fee)

                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] \
                        - lto_list[i]['result']['enter']['amount'] \
                        - lto_list[i]['result']['enter']['fee'] \
                        - lto_list[i]['result']['exit']['fee']
                    lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']
                    
                    telbot.send_constructed_msg('lto', *[lto_list[i]['_id'], lto_list[i]['strategy'], lto_list[i]['pair'], 'exit', oco_limit_orderId, 'filled'])


                elif int(lto_list[i]['exit'][TYPE_OCO]['expire']) <= last_closed_candle_open_time:
                    lto_list[i]['status'] = STAT_EXIT_EXP
                    lto_list[i]['history'].append(lto_list[i]['status'])

                else:
                    # TODO: LOG WARNING
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


async def application(strategy_list, strategy_res_allocator, broker, ikarus_time):
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
    meta_data_pool = set(chain(*meta_data_pool))

    # NOTE: Query to get all of the LTOs that has a strategy property that is contained in 'active_strategies'
    live_trade_dicts = await mongocli.do_aggregate('live-trades',[{ '$match': { 'strategy': {'$in': list(strategy_period_mapping.keys()) }} }])
    live_trades = [trade_from_dict(trade_dict) for trade_dict in live_trade_dicts]

    df_balance, data_dict, orders = await asyncio.gather(*[
        broker.get_current_balance(),
        broker.get_data_dict(meta_data_pool, ikarus_time),
        broker.get_lto_orders(live_trades)]
    )

    live_trades, analysis_dict = await asyncio.gather(*[
        broker.get_current_balance(),
        update_ltos(live_trades, data_dict, strategy_period_mapping, orders),
        analyzer.sample_analyzer(data_dict)]
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
    new_trades = list(chain(*strategy_decisions)) # TODO: NEXT: Strategy output is only nto but it edits the ltos as well, so return ltos too

    new_trades.clear()

    if len(new_trades) or len(live_trades):
        #nto_list, lto_list = await asyncio.create_task(bwrapper.execute_decision(nto_list, lto_list))
        broker.execute_decision(new_trades, df_balance, live_trades)

    new_trade_list = [i for i in new_trade_list if i is not None]

    if len(new_trades):
        # 3.1: Write trade_dict to [live-trades] (assume it is executed successfully)
        result = await mongocli.do_insert_many("live-trades", [trade_to_dict(trade) for trade in new_trades])

    await mongo_utils.update_live_trades(mongocli, live_trades)


    df_balance = await broker.get_current_balance()

    obs_strategy_capitals = Observer('strategy_capitals', ts=ikarus_time, data=strategy_res_allocator.strategy_capitals).to_dict()

    observer_item = list(df_balance.reset_index(level=0).T.to_dict().values())
    obs_balance = Observer(EObserverType.BALANCE, ts=ikarus_time, data=observer_item).to_dict()

    observation_obj = {}
    observation_obj['free'] = df_balance.loc[config['broker']['quote_currency'],'free']
    observation_obj['in_trade'] = eval_total_capital_in_lto(live_trades+new_trade_list)
    observation_obj['total'] = observation_obj['free'] + observation_obj['in_trade']
    obs_quote_asset = Observer(EObserverType.QUOTE_ASSET, ts=ikarus_time, data=observation_obj).to_dict()

    observation_obj = {}
    free = df_balance.loc[config['broker']['quote_currency'],'free']
    in_trade = eval_total_capital_in_lto(live_trades+new_trade_list)
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


async def main():
    global FLAG_SYSTEM_STATUS

    client = await AsyncClient.create(**cred_info['Binance']['Test'])
    bwrapper = BinanceWrapper(client, config, telbot)

    all_pairs = [strategy['pairs'] for strategy in config['strategy'].values()]
    all_pairs = list(set(itertools.chain(*all_pairs)))
    symbol_info = await bwrapper.get_all_symbol_info(all_pairs)

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

    #telbot.send_constructed_msg('app', 'started!')
    while True:
        try:
            sys_stat = await asyncio.wait_for(client.get_system_status(), timeout=10)
            logger.debug(f'System status: {sys_stat}')

            if sys_stat['status'] != 0:
                raise SysStatDownException()

            #telbot.send_constructed_msg('app', f'FLAG_SYSTEM_STATUS set to {FLAG_SYSTEM_STATUS}')

            server_time = await client.get_server_time() # UTC
            current_time = int(server_time['serverTime']/1000)
            logger.debug(f'Server time: {server_time["serverTime"]}, ({datetime.fromtimestamp(current_time)})')


            start_time_offset = 10
            next_start_time = round_to_period(current_time, ikarus_cycle_period_in_sec, direction='ceiling', offset=start_time_offset)

            logger.debug(f'Cycle start time: {next_start_time}, ({datetime.fromtimestamp(next_start_time)})')
            result = await asyncio.create_task(run_at(next_start_time, application(strategy_list, strategy_res_allocator, bwrapper, next_start_time-start_time_offset)))
            
            '''
            # NOTE: The logic below is for gathering data every 'period' seconds (Good for testing and not waiting)
            await asyncio.gather(
                asyncio.sleep(10),
                application(bwrapper, telbot),
            )
            '''
        except SysStatDownException as e:
            logger.error(str(e))
            telbot.send_constructed_msg('error', str(e))
            await asyncio.sleep(60)

        except Exception as e:
            logger.error(str(e))
            telbot.send_constructed_msg('error', str(e))
            
            
    await client.close_connection()

if __name__ == "__main__":
    
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    logger = logging.getLogger('app')
    telbot = notifications.TelegramBot(**cred_info['Telegram'], telegram_config=config['notification']['telegram'])
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