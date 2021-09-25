import asyncio
from binance import AsyncClient
from datetime import datetime
import json
from Ikarus import performance, strategy_manager, binance_wrapper, notifications, analyzers, observers, mongo_utils, lto_manipulator
from Ikarus.enums import *
from Ikarus.exceptions import SysStatDownException, NotImplementedException
from Ikarus.utils import time_scale_to_second, get_closed_hto, get_enter_expire_hto, get_exit_expire_hto, \
    get_min_scale, get_pair_min_period_mapping, eval_total_capital, eval_total_capital_in_lto
import logging
from logging.handlers import TimedRotatingFileHandler
import pandas as pd
import sys
import copy
import bson
import time
from itertools import chain, groupby
import operator
import itertools
from Ikarus.resource_allocator import ResourceAllocator


# Global Variables
FLAG_SYSTEM_STATUS = True


def setup_logger(_log_lvl):
    # TODO: Logger can be directed to tel
    global logger
    log_filename = 'log/ikarus-app.log'
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

    # create formatter and add it to the handle
    # rs
    #formatter = logging.Formatter('[{}] [{}] [{}] [{}]'.format('%(asctime)s','%(name)26s','%(levelname)8s', '%(message)s'))
    formatter = logging.Formatter('[{}][{}][{} - {}][{}][{}]'.format('%(asctime)s',
        '%(filename)-21s','%(lineno)-3d','%(funcName)-24s','%(levelname)8s', '%(message)s'))
    formatter.converter = time.gmtime # Use the UTC Time
    rfh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(rfh)
    logger.addHandler(ch)

    logger.info('logger has been set')


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

                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] - lto_list[i]['result']['enter']['amount']
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

                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] - lto_list[i]['result']['enter']['amount']
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

                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] - lto_list[i]['result']['enter']['amount']
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


async def application(strategy_list, bwrapper, ikarus_time):
    # TODO: NEXT: Update live-engine based on the changes in test-engine
    logger.info(f'Ikarus Time: [{ikarus_time}]') # UTC
    
    #################### Phase 1: Perform pre-calculation tasks ####################
    logger.debug('Phase 1')

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

    # 1.1 Get live trade objects (LTOs)
    # NOTE: Query to get all of the LTOs that has a strategy property that is contained in 'active_strategies'
    lto_list = await mongocli.do_aggregate('live-trades',[{ '$match': { 'strategy': {'$in': list(strategy_period_mapping.keys()) }} }])

    # 1.2 Get datadict and orders
    logger.debug('Phase 1.2')
    pre_calc_1_coroutines = [ bwrapper.get_data_dict(meta_data_pool, ikarus_time),
                              bwrapper.get_lto_orders(lto_list)]

    data_dict, orders = await asyncio.gather(*pre_calc_1_coroutines)
    # TODO: NEXT: [APIError(code=-1105): Parameter 'orderId' was empty.] Resolve the issue and continue integ
    if len(lto_list): 
        #orders = await lto_manipulator.fill_open_enter(lto_list, orders)
        #orders = await lto_manipulator.fill_open_exit_limit(lto_list, orders)
        #orders = await lto_manipulator.limit_maker_taken_oco(lto_list, orders)
        #orders = await lto_manipulator.stoploss_taken_oco([lto_list[1]], orders)
        pass

    # 1.3: Get df_balance, lto_dict, analysis_dict
    logger.debug('Phase 1.3')
    pre_calc_2_coroutines = [ bwrapper.get_current_balance(),
                              update_ltos(lto_list, data_dict, strategy_period_mapping, orders),
                              analyzer.sample_analyzer(data_dict)]

    df_balance, lto_list, analysis_dict = await asyncio.gather(*pre_calc_2_coroutines)

    #################### Phase 2: Perform calculation tasks ####################
    logger.debug('Phase 2')

    total_qc = eval_total_capital(df_balance, lto_list, config['broker']['quote_currency'], config['risk_management']['max_capital_use_ratio'])
    total_qc_in_lto = eval_total_capital_in_lto(lto_list)
    logger.info(f'Total QC: {total_qc}, Total amount of LTO: {total_qc_in_lto}')

    # NOTE: Group the LTOs: It is only required here since only each strategy may know what todo with its own LTOs
    grouped_ltos = {}
    if len(lto_list):
        for lto_obj in lto_list:
            grouped_ltos.setdefault(lto_obj['strategy'], []).append(lto_obj)

    strategy_tasks = []
    for strategy in strategy_list:
        strategy_tasks.append(asyncio.create_task(strategy.run(analysis_dict, grouped_ltos.get(strategy.name, []), ikarus_time, total_qc)))

    strategy_decisions = list(await asyncio.gather(*strategy_tasks))
    nto_list = list(chain(*strategy_decisions))

    # 2.3: Execute LTOs and NTOs if any
    if len(nto_list) or len(lto_list):
        # 2.3.1: Execute the TOs
        nto_list, lto_list = await asyncio.create_task(bwrapper.execute_decision(nto_list, lto_list))

    #################### Phase 3: Perform post-calculation tasks ####################
    logger.debug('Phase 3 started')

    if len(nto_list):
        # 3.1: Write trade_dict to [live-trades]
        results = await mongocli.do_insert_many("live-trades", nto_list)

        if len(nto_list) != len(results.inserted_ids):
            # TODO: Add proper error handling and proper error messages
            logger.error('Some of the NTOs could not be placed to Database')
            telbot.send_constructed_msg('error', 'Some of the NTOs could not be placed to Database')
            for nto in nto_list:
                telbot.send_constructed_msg('lto', *['', nto['strategy'], nto['pair'], PHASE_ENTER, nto['enter'][TYPE_LIMIT]['orderId'], EVENT_PLACED])
        else:
            for _id, nto in zip(results.inserted_ids,nto_list):
                logger.info(f'LTO: "{nto["_id"]}" | {nto["strategy"]} | {nto["pair"]} created with the {PHASE_ENTER} order: {nto["enter"][TYPE_LIMIT]["orderId"]}')
                telbot.send_constructed_msg('lto', *[_id, nto['strategy'], nto['pair'], PHASE_ENTER, nto['enter'][TYPE_LIMIT]['orderId'], EVENT_PLACED])


    # 3.2: Write the LTOs and NTOs to [live-trades] and [hist-trades]
    await write_updated_ltos_to_db(lto_list)

    # 3.3: Get the observer

    # 3.3.1 Get df_balance
    df_balance = await bwrapper.get_current_balance()

    # 3.3.2 Insert df_balance to [observer]
    observer_list = [
        observer.qc_observer(df_balance, lto_list+nto_list, config['broker']['quote_currency'], ikarus_time),
        observer.sample_observer(df_balance, ikarus_time)
    ]
    observer_objs = list(await asyncio.gather(*observer_list))
    await mongocli.do_insert_many("observer", observer_objs)


    return True


async def main():
    global FLAG_SYSTEM_STATUS

    client = await AsyncClient.create(api_key=cred_info['Binance']['Production']['PUBLIC-KEY'],
                                      api_secret=cred_info['Binance']['Production']['SECRET-KEY'])
    bwrapper = binance_wrapper.BinanceWrapper(client, config, telbot)

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

    strategy_periods = set()
    for strategy in strategy_list:
        if strategy.name in config['strategy'].keys():
            strategy_periods.add(strategy.min_period)

    ikarus_cycle_period = await get_min_scale(config['time_scales'].keys(), strategy_periods)
    if ikarus_cycle_period == '': raise ValueError('No ikarus_cycle_period specified')
    ikarus_cycle_period_in_sec = time_scale_to_second(ikarus_cycle_period)

    telbot.send_constructed_msg('app', 'started!')
    while True:
        try:
            sys_stat = await asyncio.wait_for(client.get_system_status(), timeout=10)

            if sys_stat['status'] != 0:
                if FLAG_SYSTEM_STATUS != False:
                    FLAG_SYSTEM_STATUS = False
                    raise SysStatDownException()
            else:
                if FLAG_SYSTEM_STATUS != True:
                    FLAG_SYSTEM_STATUS = True
                    logger.info(f'Broker is up!')
                    telbot.send_constructed_msg('app', f'FLAG_SYSTEM_STATUS set to {FLAG_SYSTEM_STATUS}')
            

            server_time = await client.get_server_time() # UTC
            logger.debug(f'System time: {server_time["serverTime"]}')
            current_time = int(server_time['serverTime']/1000)                                                  # exact second
            current_time -= (current_time % 60)                                                                 # exact minute
            current_time -= (current_time % ikarus_cycle_period_in_sec )                                          # exact scale

            # NOTE: start_time_offset is used to make sure the broker created the last closed candle properly
            start_time_offset = 10
            next_start_time = current_time + ikarus_cycle_period_in_sec + start_time_offset

            logger.debug(f'Cycle start time: {next_start_time}')
            result = await asyncio.create_task(run_at(next_start_time, application(strategy_list, bwrapper, next_start_time-start_time_offset)))
            
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

    # TODO: A paper-testing script might be need to develop, live-trade viualization and reveal unseen bugs
    #       lto_update, bwrapper.execute sections can be directly taken from backtest-engine
    
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    logger = logging.getLogger('app')
    telbot = notifications.TelegramBot(cred_info['Telegram']['Token'], cred_info['Telegram']['ChatId'], config['notification']['telegram'])
    mongocli = mongo_utils.MongoClient(config['mongodb']['host'], 
        config['mongodb']['port'], 
        config['tag'],
        clean=config['mongodb']['clean']) # NOTE: Normally it is False

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

    loop.run_until_complete( main())
    print("Completed")