import pandas as pd
from .enums import *
from .utils import calculate_fee
from Ikarus.strategies.StrategyBase import StrategyBase
from .exceptions import NotImplementedException

def buy(df_balance, quote_cur, base_cur, enter_module, enter_type):
    # Cut the fee first
    df_balance.loc[quote_cur, 'free'] -= calculate_fee(enter_module['amount'], StrategyBase.fee)

    # Remove the enter amount from quote currency
    if enter_type == TYPE_MARKET:
        pass
    elif enter_type == TYPE_LIMIT:
        # NOTE: Cut the amount from the 'locked' since the enter amount is located to there until execution
        df_balance.loc[quote_cur, 'locked'] -= enter_module['amount']
    else:
        raise NotImplementedException('Unexpected Enter Type: ')

    # Add the enter quantity to the base currency
    if base_cur in list(df_balance.index):
        df_balance.loc[base_cur, 'locked' ] += enter_module['quantity']
    else:
        # Previously there was no base_currency, so we create a row for it
        # free locked total
        df_balance.loc[base_cur] = [enter_module['quantity'], 0, 0]

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return df_balance


def place_enter_order(df_balance, quote_cur, enter_module):

    # Move fre amount to locked
    df_balance.loc[quote_cur,'free'] -= enter_module['amount']
    df_balance.loc[quote_cur,'locked'] += enter_module['amount']

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return df_balance


def cancel_enter_order(df_balance, quote_cur, enter_module):

    # Move fre amount to locked
    df_balance.loc[quote_cur,'locked'] -= enter_module['amount'] # It is assumed TYPE_LIMIT and ignored TYPE_OCO
    df_balance.loc[quote_cur,'free'] += enter_module['amount']

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return df_balance


def place_exit_order(df_balance, base_cur, quantity):

    # Move free amount to locked
    df_balance.loc[base_cur, 'free'] -= quantity
    df_balance.loc[base_cur, 'locked'] += quantity

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return df_balance



def sell(df_balance, pair, exit_module):
    return 
