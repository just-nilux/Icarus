from copy import Error
import pandas as pd
import more_itertools
from .enums import *
from decimal import ROUND_DOWN, Decimal
import logging
from logging.handlers import TimedRotatingFileHandler
import time


def calculate_fee(amount, fee, digit=8):
    return round(safe_multiply(amount,fee), digit)

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

def safe_divide(num1, num2, quant='0.00000001', rounding=None):
    return float( (Decimal(str(num1)) / Decimal(str(num2))).quantize(Decimal(quant), rounding=rounding) )

def safe_multiply(num1, num2, quant='0.00000001', rounding=None):
    return float( (Decimal(str(num1)) * Decimal(str(num2))).quantize(Decimal(quant), rounding=rounding) )

def safe_sum(num1, num2, quant='0.00000001', rounding=None):
    return float( (Decimal(str(num1)) + Decimal(str(num2))).quantize(Decimal(quant), rounding=rounding) )

def safe_substract(num1, num2, quant='0.00000001', rounding=None):
    return float( (Decimal(str(num1)) - Decimal(str(num2))).quantize(Decimal(quant), rounding=rounding) )

def time_scale_to_second(interval: str):
    return time_scale_to_minute(interval) * 60

def time_scale_to_milisecond(interval: str):
    return time_scale_to_minute(interval) * 60 * 1000

def eval_total_capital(df_balance, lto_list, quote_currency, max_capital_use_ratio=1):
    # Toal capital: Free QC + LTO_enter
    free_qc = df_balance.loc[quote_currency,'free']

    # NOTE: In-trade balance is calculated only by considering the LTOs of the Ikarus
    #       Using only the df_balance requires live updates and evaluation of each asset in terms of QC

    # NOTE: If state of a TO is:
    #   'closed': then the amount that is used by this TO is reflected back to main capital (df_balance in backtest (by lto_update))
    #           : these LTOs needs be omitted
    #   'enter_expire': then it is marked to be handled by the their strategy but the balance is still locked in LTO

    in_trade_qc = eval_total_capital_in_lto(lto_list)

    total_qc = safe_sum(free_qc, in_trade_qc)
    return safe_multiply(total_qc, max_capital_use_ratio)

def eval_total_capital_in_lto(lto_list):
    in_trade_qc = 0
    for lto in lto_list:
        # Omit the LTOs that are closed, because their use of amount returned to df_balance (by broker or by lto_update of test-engine)
        if lto['status'] != STAT_CLOSED:
            # NOTE: It is assumed that each object may only have 1 TYPE of exit or enter
            in_trade_qc = safe_sum(in_trade_qc, more_itertools.one(lto[PHASE_ENTER].values())['amount'])
    return in_trade_qc

async def get_closed_hto(config, mongocli, query={'result.cause':STAT_CLOSED}):
    # TODO: NEXT: All statistics needs to be changed a bit  to integrate market orders
    # Read Database to get hist-trades and dump to a DataFrame
    hto_list = await mongocli.do_find('hist-trades',query)
    hto_closed = []
    for hto in hto_list:

        # Ideal enter and exit types
        enter_type = config['strategy'][hto['strategy']]['enter']['type']
        exit_type = config['strategy'][hto['strategy']]['exit']['type']
        # NOTE: These ideal types only change in market_exit action which is handled in get_exit_expire_hto

        if exit_type == TYPE_OCO: plannedPriceName = 'limitPrice'
        elif exit_type == TYPE_LIMIT or exit_type == TYPE_MARKET: plannedPriceName = 'price'

        hto_dict = {
            "_id": hto['_id'],
            "strategy": hto['strategy'],
            "decision_time": hto['decision_time'],
            "enterTime": hto['result']['enter']['time'],
            "enterPrice": hto['enter'][enter_type]['price'],
            "exitTime": hto['result']['exit']['time'],
            "exitPrice": hto['exit'][exit_type][plannedPriceName],
            "sellPrice": hto['result']['exit']['price']
        }
        hto_closed.append(hto_dict)

    df = pd.DataFrame(hto_closed)
    return df


async def get_enter_expire_hto(mongocli, query={'result.cause':STAT_ENTER_EXP}):
    # Read Database to get hist-trades and dump to a DataFrame
    hto_list = await mongocli.do_find('hist-trades',query)
    hto_ent_exp_list = []
    for hto in hto_list:
        # NOTE: HIGH: We dont know it the exit type is limit or not
        hto_dict = {
            "_id": hto['_id'],
            "strategy": hto['strategy'],
            "decision_time": hto['decision_time'],
            "enterExpire": hto['enter'][TYPE_LIMIT]['expire'],# TODO: TYPE_LIMIT | TODO: use result enter price
            "enterPrice": hto['enter'][TYPE_LIMIT]['price'],
        }
        hto_ent_exp_list.append(hto_dict)

    df = pd.DataFrame(hto_ent_exp_list)
    return df


async def get_exit_expire_hto(config, mongocli, query={'result.cause':STAT_EXIT_EXP}):
    # Read Database to get hist-trades and dump to a DataFrame
    
    hto_list = await mongocli.do_find('hist-trades',query)
    hto_closed_list = []
    for hto in hto_list:

        enter_type = config['strategy'][hto['strategy']]['enter']['type']
        exit_type = config['strategy'][hto['strategy']]['exit']['type']

        if exit_type == TYPE_OCO: plannedPriceName = 'limitPrice'
        elif exit_type == TYPE_LIMIT: plannedPriceName = 'price'

        # Initial (ideal) exit module is saved to update_history list
        initial_exit_module = hto['update_history'][0]
        # TODO: Rename the update_history with some proper name

        hto_dict = {
            "_id": hto['_id'],
            "strategy": hto['strategy'],
            "decision_time": hto['decision_time'],
            "enterTime": hto['result']['enter']['time'],
            "enterPrice": hto['enter'][enter_type]['price'],            # Ideally enter limit orders are executed with the exact prices
            "exitPrice": initial_exit_module[plannedPriceName],
            "sellPrice": hto['result']['exit']['price'],
            "exitExpire": initial_exit_module['expire']
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

def get_lto_phase(lto):

    if lto['status'] in [STAT_OPEN_ENTER, STAT_ENTER_EXP]:
        return PHASE_ENTER

    elif lto['status'] in [STAT_EXIT_EXP, STAT_OPEN_EXIT, STAT_WAITING_EXIT]:
        return PHASE_EXIT

    else:
        raise Exception(f'LTO {lto["_id"]} status {lto["status"]}')


def setup_logger(logger, log_level, log_file):
    logger = logging.getLogger('app')
    logger.setLevel(logging.DEBUG)

    rfh = TimedRotatingFileHandler(filename=log_file,
                                   when='H',
                                   interval=1,
                                   backupCount=5)

    rfh.setLevel(log_level)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('[{}][{}][{} - {}][{}][{}]'.format('%(asctime)s',
        '%(filename)-21s','%(lineno)-3d','%(funcName)-24s','%(levelname)8s', '%(message)s'))
    formatter.converter = time.gmtime # Use the UTC Time
    rfh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(rfh)
    logger.addHandler(ch)

    logger.info('logger has been set')