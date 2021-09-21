import pandas as pd
from .enums import *

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

def time_scale_to_second(interval: str):
    return time_scale_to_minute(interval) * 60

def time_scale_to_milisecond(interval: str):
    return time_scale_to_minute(interval) * 60 * 1000

def eval_total_capital(df_balance, lto_list, quote_currency):
    # Toal capital: Free QC + LTO_enter
    free_qc = df_balance.loc[quote_currency,'free']

    # NOTE: In-trade balance is calculated only by considering the LTOs of the Ikarus
    #       Using only the df_balance requires live updates and evaluation of each asset in terms of QC

    # NOTE: If state of a TO is:
    #   'closed': then the amount that is used by this TO is reflected back to main capital (df_balance in backtest (by lto_update))
    #           : these LTOs needs be omitted
    #   'enter_expire': then it is marked to be handled by the their strategy but the balance is still locked in LTO

    in_trade_qc = 0
    for lto in lto_list:
        # Omit the LTOs that are closed, because their use of amount returned to df_balance (by broker or by lto_update of test-engine)
        if lto['status'] != STAT_CLOSED:
            in_trade_qc += lto[PHASE_ENTER][TYPE_LIMIT]['amount']

    total_qc = free_qc + in_trade_qc
    return total_qc

def eval_total_capital_in_lto(lto_list):
    in_trade_qc = 0
    for lto in lto_list:
        # Omit the LTOs that are closed, because their use of amount returned to df_balance (by broker or by lto_update of test-engine)
        if lto['status'] != STAT_CLOSED:
            in_trade_qc += lto[PHASE_ENTER][TYPE_LIMIT]['amount']
    return in_trade_qc

async def get_closed_hto(mongocli, query={'result.cause':STAT_CLOSED}):
    # Read Database to get hist-trades and dump to a DataFrame
    hto_list = await mongocli.do_find('hist-trades',query)
    hto_closed = []
    for hto in hto_list:
        if TYPE_OCO in hto['exit'].keys():  plannedExitType = TYPE_OCO; plannedPriceName = 'limitPrice'
        elif TYPE_LIMIT in hto['exit'].keys(): plannedExitType = TYPE_LIMIT; plannedPriceName = 'price'

        hto_dict = {
            "_id": hto['_id'],
            "strategy": hto['strategy'],
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
            "enterExpire": hto['enter'][TYPE_LIMIT]['expire'],
            "enterPrice": hto['enter'][TYPE_LIMIT]['price'],
        }
        hto_ent_exp_list.append(hto_dict)

    df = pd.DataFrame(hto_ent_exp_list)
    return df


async def get_exit_expire_hto(mongocli, query={'result.cause':STAT_EXIT_EXP}):
    # Read Database to get hist-trades and dump to a DataFrame
    
    hto_list = await mongocli.do_find('hist-trades',query)
    hto_closed_list = []
    for hto in hto_list:
        if TYPE_OCO in hto['exit'].keys():  plannedExitType = TYPE_OCO; plannedPriceName = 'limitPrice'
        elif TYPE_LIMIT in hto['exit'].keys(): plannedExitType = TYPE_LIMIT; plannedPriceName = 'price'

        hto_dict = {
            "_id": hto['_id'],
            "strategy": hto['strategy'],
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


async def get_min_scale(ordered_scales, pool):
    
    for scale in ordered_scales:
        if scale in pool:
            return scale

    return None