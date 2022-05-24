from .enums import *
from .utils import calculate_fee, safe_substract, safe_sum
from .strategies.StrategyBase import StrategyBase


def buy(df_balance, quote_cur, base_cur, result_enter):

    calculated_fee = calculate_fee(result_enter.amount, StrategyBase.fee)
    if df_balance.loc[quote_cur,'locked'] < result_enter.amount or df_balance.loc[quote_cur, 'free'] < calculated_fee:
        return False

    # Cut the fee first
    df_balance.loc[quote_cur, 'free'] = safe_substract(df_balance.loc[quote_cur, 'free'], calculated_fee)
    # Remove the enter amount from quote currency

    # NOTE: Cut the amount from the 'locked' since the enter amount is located to there until execution
    df_balance.loc[quote_cur, 'locked'] = safe_substract(df_balance.loc[quote_cur, 'locked'], result_enter.amount)

    # Add the enter quantity to the base currency
    if base_cur in list(df_balance.index):
        df_balance.loc[base_cur, 'free' ] = safe_sum(df_balance.loc[base_cur, 'free' ], result_enter.quantity)
    else:
        # Previously there was no base_currency, so we create a row for it
        # free locked total
        df_balance.loc[base_cur] = [result_enter.quantity, 0, 0]

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return True

def sell(df_balance, quote_cur, base_cur, result_exit):

    # NOTE: Locked base_cur will be withdrew and deposited to free qc
    df_balance.loc[base_cur,'locked'] = safe_substract(df_balance.loc[base_cur,'locked'], result_exit.quantity)
    df_balance.loc[quote_cur,'free'] = safe_sum(df_balance.loc[quote_cur,'free'], result_exit.amount)
    df_balance.loc[quote_cur,'free'] = safe_substract(df_balance.loc[quote_cur,'free'], result_exit.fee)

    df_balance['total'] = df_balance['free'] + df_balance['locked']


def place_enter_order(df_balance, quote_cur, trade_enter):

    # Move fre amount to locked
    #df_balance.loc[quote_cur,'free'] -= enter_module['amount']
    if df_balance.loc[quote_cur,'free'] < trade_enter.amount:
        return False

    df_balance.loc[quote_cur,'free'] = safe_substract(df_balance.loc[quote_cur,'free'], trade_enter.amount)
    df_balance.loc[quote_cur,'locked'] = safe_sum(df_balance.loc[quote_cur,'locked'], trade_enter.amount)

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return True


def cancel_enter_order(df_balance, quote_cur, trade_enter):

    # Move free amount to locked
    df_balance.loc[quote_cur,'locked'] = safe_substract(df_balance.loc[quote_cur,'locked'], trade_enter.amount)
    df_balance.loc[quote_cur,'free'] = safe_sum(df_balance.loc[quote_cur,'free'], trade_enter.amount)

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']


def cancel_exit_order(df_balance, base_cur, trade_exit):

    # Move free amount to locked
    df_balance.loc[base_cur,'locked'] = safe_substract(df_balance.loc[base_cur,'locked'], trade_exit.quantity)
    df_balance.loc[base_cur,'free'] = safe_sum(df_balance.loc[base_cur,'free'], trade_exit.quantity)

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']


def place_exit_order(df_balance, base_cur, trade_exit):

    if df_balance.loc[base_cur,'free'] < trade_exit.quantity:
        return False

    # Move free amount to locked
    df_balance.loc[base_cur, 'free'] = safe_substract(df_balance.loc[base_cur, 'free'], trade_exit.quantity)
    df_balance.loc[base_cur, 'locked'] = safe_sum(df_balance.loc[base_cur, 'locked'], trade_exit.quantity)

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return True
