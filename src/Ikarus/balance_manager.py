from .utils import safe_substract, safe_sum
from .strategies.StrategyBase import StrategyBase


def buy(df_balance, quote_cur, base_cur, trade):

    if df_balance.loc[quote_cur,'locked'] < trade.enter.amount:
        return False

    # This should be the quantity after the fee is paid which requires trade.result.enter
    df_balance.loc[quote_cur, 'locked'] = safe_substract(df_balance.loc[quote_cur, 'locked'], trade.enter.amount)

    # Add the enter quantity to the base currency
    if base_cur in list(df_balance.index):
        # This should be the quantity after the fee is paid which requires trade.result.enter
        df_balance.loc[base_cur, 'free' ] = safe_sum(df_balance.loc[base_cur, 'free' ], trade.result.enter.quantity) 
    else:
        # Previously there was no base_currency, so we create a row for it
        # free locked total
        df_balance.loc[base_cur] = [trade.result.enter.quantity, 0, 0]

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return True


def sell(df_balance, quote_cur, base_cur, trade):

    if df_balance.loc[base_cur,'locked'] < trade.result.exit.quantity:
        return False

    # NOTE: Locked base_cur will be withdrew and deposited to free qc
    df_balance.loc[base_cur,'locked'] = safe_substract(df_balance.loc[base_cur,'locked'], trade.result.exit.quantity)
    df_balance.loc[quote_cur,'free'] = safe_sum(df_balance.loc[quote_cur,'free'], trade.result.exit.amount)

    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return True


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

    if df_balance.loc[quote_cur,'locked'] < trade_enter.amount:
        return False

    # Move free amount to locked
    df_balance.loc[quote_cur,'locked'] = safe_substract(df_balance.loc[quote_cur,'locked'], trade_enter.amount)
    df_balance.loc[quote_cur,'free'] = safe_sum(df_balance.loc[quote_cur,'free'], trade_enter.amount)

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return True


def cancel_exit_order(df_balance, base_cur, trade_exit):

    if df_balance.loc[base_cur,'locked'] < trade_exit.quantity:
        return False

    # Move free amount to locked
    df_balance.loc[base_cur,'locked'] = safe_substract(df_balance.loc[base_cur,'locked'], trade_exit.quantity)
    df_balance.loc[base_cur,'free'] = safe_sum(df_balance.loc[base_cur,'free'], trade_exit.quantity)

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return True


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
