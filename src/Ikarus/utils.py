import pandas as pd
import os
from .objects import ECause, EState, trade_from_dict
from decimal import ROUND_DOWN, Decimal
import logging
from logging.handlers import TimedRotatingFileHandler
import time
from .safe_operators import *


def time_scale_to_minute(interval: str):
    seconds_per_unit = {
        "m": 1,
        "h": 60,
        "d": 24 * 60,
        "w": 7 * 24 * 60,
    }
    try:
        return int(interval[:-1]) * seconds_per_unit[interval[-1]]
    except (ValueError, KeyError):
        return None

def round_step_downward(quantity, step_size):
    # NOTE: if the step_size is '1.0', 1.2389196468651802 is rounded as 1.2 instead of 1.
    #       Thus if the step_size is an integer then we should approach properly
    if step_size.is_integer(): step_size = int(step_size)
    return float(Decimal(str(quantity)).quantize(Decimal(str(step_size)), rounding=ROUND_DOWN))

def truncate(num,n):
    temp = str(num)
    for x in range(len(temp)):
        if temp[x] == '.':
            try:
                return float(temp[:x+n+1])
            except:
                return float(temp)      
    return float(temp)

def time_scale_to_second(interval: str):
    return time_scale_to_minute(interval) * 60

def time_scale_to_milisecond(interval: str):
    return time_scale_to_minute(interval) * 60 * 1000

def eval_total_capital(df_balance, live_trade_list, quote_currency, max_capital_use_ratio=1):
    # Toal capital: Free QC + LTO_enter
    free_qc = df_balance.loc[quote_currency,'free']

    # NOTE: In-trade balance is calculated only by considering the LTOs of the Ikarus
    #       Using only the df_balance requires live updates and evaluation of each asset in terms of QC

    # NOTE: If state of a TO is:
    #   'closed': then the amount that is used by this TO is reflected back to main capital (df_balance in backtest (by lto_update))
    #           : these LTOs needs be omitted
    #   'enter_expire': then it is marked to be handled by the their strategy but the balance is still locked in LTO

    in_trade_qc = eval_total_capital_in_lto(live_trade_list)

    total_qc = safe_sum(free_qc, in_trade_qc)
    return safe_multiply(total_qc, max_capital_use_ratio)

def eval_total_capital_in_lto(trade_list):
    in_trade_qc = 0
    for trade in trade_list:
        # Omit the LTOs that are closed, because their use of amount returned to df_balance (by broker or by lto_update of test-engine)
        if trade.status != EState.CLOSED:
            # NOTE: It is assumed that each object may only have 1 TYPE of exit or enter
            in_trade_qc = safe_sum(in_trade_qc, trade.enter.amount)
    return in_trade_qc

async def get_closed_hto(config, mongocli, query={'result.cause':ECause.CLOSED}):
    # TODO: NEXT: All statistics needs to be changed a bit  to integrate market orders
    # Read Database to get hist-trades and dump to a DataFrame
    hto_list = await mongocli.do_find('hist-trades',query)
    hto_closed = []
    for hto in hto_list:
        trade = trade_from_dict(hto)

        hto_dict = {
            "_id": trade._id,
            "strategy": trade.strategy,
            "decision_time": trade.decision_time,
            "enterTime": trade.result.enter.time,
            "enterPrice": trade.enter.price, 
            "exitTime": trade.result.exit.time,
            "exitPrice": trade.exit.price,
            "sellPrice": trade.result.exit.price
        }
        # NOTE: No trade.result.enter.price is used because in each case Limit/Market enter the price value will be used directly
        hto_closed.append(hto_dict)

    df = pd.DataFrame(hto_closed)
    return [trade_from_dict(hto) for hto in hto_list]


async def get_enter_expire_hto(mongocli, query={'result.cause':ECause.ENTER_EXP}):
    # Read Database to get hist-trades and dump to a DataFrame
    hto_list = await mongocli.do_find('hist-trades',query)
    hto_ent_exp_list = []
    for hto in hto_list:
        # NOTE: HIGH: We dont know it the exit type is limit or not
        trade = trade_from_dict(hto)
        hto_dict = {
            "_id": trade._id,
            "strategy": trade.strategy,
            "decision_time": trade.decision_time,
            "enterExpire": trade.enter.expire, # TODO: TYPE_LIMIT | TODO: use result enter price
            "enterPrice": trade.enter.price,
        }
        hto_ent_exp_list.append(hto_dict)

    df = pd.DataFrame(hto_ent_exp_list)
    return df


async def get_exit_expire_hto(config, mongocli, query={'result.cause':ECause.EXIT_EXP}):
    # Read Database to get hist-trades and dump to a DataFrame
    # TODO:  REFACTORING: Continue from here. You did not tested the visualizion of the Limit Update
    hto_list = await mongocli.do_find('hist-trades',query)
    hto_closed_list = []
    for hto in hto_list:
        trade = trade_from_dict(hto)

        # Initial (ideal) exit module is saved to order_stash list
        initial_exit_module = hto['order_stash'][-1]
        # TODO: Rename the order_stash with some proper name

        hto_dict = {
            "_id": trade._id,
            "strategy": trade.strategy,
            "decision_time": trade.decision_time,
            "enterTime": trade.result.enter.time,
            "enterPrice": trade.enter.price,            # Ideally enter limit orders are executed with the exact prices
            "exitPrice": initial_exit_module.price,
            "sellPrice": trade.result.exit.price,
            "exitExpire": initial_exit_module.price
        }
        hto_closed_list.append(hto_dict)
    df = pd.DataFrame(hto_closed_list)

    return df


async def get_pair_min_period_mapping(config):
    
    pair_scale_set_mapping = {}
    for name, strategy in config['strategy'].items():
        for pair in strategy['pairs']:
            if pair not in pair_scale_set_mapping.keys():
                pair_scale_set_mapping[pair] = set()
            pair_scale_set_mapping[pair].add(strategy['time_scales'][0])

    pair_min_period_mapping = {}
    for pair, scale_set in pair_scale_set_mapping.items():
        for scale in config['time_scales'].keys():
            if scale in scale_set:
                pair_min_period_mapping[pair] = scale
                break

    return pair_min_period_mapping


def get_min_scale(ordered_scales, pool):
    
    for scale in ordered_scales:
        if scale in pool:
            return scale

    return None

def round_to_period(current_time, period_min, direction='floor', offset=0):
    """
    Args:
        current_time ([type]): [description]
        period_min ([type]): [description]
        direction (str, optional): [floor|ceiling]. Defaults to 'floor'.
        offset (int, optional): [description]. Defaults to 0.

    Returns:
        [int]: [rounded_time]
    """    
    current_time -= (current_time % 60)                         # exact minute
    current_time -= (current_time % period_min )                # exact scale
    if direction == 'floor':
        rounded_time = current_time + offset
    elif direction == 'ceiling':
        rounded_time = current_time + period_min + offset
    else:
        raise Exception(f'Unknown direction: {direction}')
    return int(rounded_time)


def setup_logger(logger, log_config):
    if log_config.get('clear',False):
        os.remove(log_config['file'])

    logger = logging.getLogger('app')
    logger.setLevel(logging.DEBUG)

    rfh = TimedRotatingFileHandler(filename=log_config['file'],
                                   when='H',
                                   interval=1,
                                   backupCount=5)

    rfh.setLevel(log_config['level'])

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('[{}][{}][{} - {}][{}][{}]'.format('%(asctime)s',
        '%(filename)-21s','%(lineno)-3d','%(funcName)-24s','%(levelname)8s', '%(message)s'))
    formatter.converter = time.gmtime # Use the UTC Time
    rfh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(rfh)
    logger.addHandler(ch)

    logger.info('logger has been set')