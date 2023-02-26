import pandas as pd
import os
from .objects import ECause, EState, trade_from_dict
from decimal import ROUND_DOWN, Decimal
import logging
from logging.handlers import TimedRotatingFileHandler
import time
from .safe_operators import *
import itertools


def minute_to_time_scale(minute: int):
    units = ["M", "w", "d", "h", "m"]
    min_per_units = [
        302400, 
        10080, 
        1440,
        60, 
        1
    ]

    for idx in range(len(units)):
        if min_per_units[idx] <= minute:
            scaler = minute / min_per_units[idx]
            if scaler % 1 != 0:
                break
            time_scale = f'{int(scaler)}{units[idx]}'
            return time_scale
    
    return None

def time_scale_to_minute(interval: str):
    minute_per_unit = {
        "m": 1,
        "h": 60,
        "d": 24 * 60,
        "w": 7 * 24 * 60,
        "M": 30 * 24 * 60
    }
    try:
        return int(interval[:-1]) * minute_per_unit[interval[-1]]
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
    if log_config.get('clear',False) and os.path.isfile(log_config['file']) :
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


def generate_pair_x_timescale_pool(strategy_config):
    time_scale_pool = []
    pair_pool = []
    for strategy in strategy_config.values():
        time_scale_pool.append(strategy['time_scales'])
        pair_pool.append(strategy['pairs'])

    time_scale_pool = list(set(itertools.chain(*time_scale_pool)))
    pair_pool = list(itertools.chain(*pair_pool))

    meta_data_pool = list(itertools.product(time_scale_pool, pair_pool))
    return meta_data_pool