import pandas as pd
from .enums import *
from .utils import calculate_fee, safe_substract, safe_sum
from Ikarus.strategies.StrategyBase import StrategyBase
from .exceptions import NotImplementedException
import logging

logger = logging.getLogger('app')

def buy(df_balance, quote_cur, base_cur, enter_module, enter_type):
    # Cut the fee first
    df_balance.loc[quote_cur, 'free'] = safe_substract(df_balance.loc[quote_cur, 'free'], calculate_fee(enter_module['amount'], StrategyBase.fee))
    # Remove the enter amount from quote currency

    # NOTE: Cut the amount from the 'locked' since the enter amount is located to there until execution
    df_balance.loc[quote_cur, 'locked'] = safe_substract(df_balance.loc[quote_cur, 'locked'], enter_module['amount'])

    # Add the enter quantity to the base currency
    if base_cur in list(df_balance.index):
        df_balance.loc[base_cur, 'free' ] = safe_sum(df_balance.loc[base_cur, 'free' ], enter_module['quantity'])
    else:
        # Previously there was no base_currency, so we create a row for it
        # free locked total
        df_balance.loc[base_cur] = [enter_module['quantity'], 0, 0]

    # Sync with total
    # BUG: Random Negative Balance exc.
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return df_balance

def sell(df_balance, quote_cur, base_cur, exit_module):

    # NOTE: Locked base_cur will be withdrew and deposited to free qc
    df_balance.loc[base_cur,'locked'] = safe_substract(df_balance.loc[base_cur,'locked'], exit_module['quantity'])
    df_balance.loc[quote_cur,'free'] = safe_sum(df_balance.loc[quote_cur,'free'],exit_module['amount'])
    df_balance.loc[quote_cur,'free'] = safe_substract(df_balance.loc[quote_cur,'free'], exit_module['fee'])

    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return df_balance


def place_enter_order(df_balance, quote_cur, enter_module):

    # Move fre amount to locked
    #df_balance.loc[quote_cur,'free'] -= enter_module['amount']
    df_balance.loc[quote_cur,'free'] = safe_substract(df_balance.loc[quote_cur,'free'], enter_module['amount'])
    df_balance.loc[quote_cur,'locked'] = safe_sum(df_balance.loc[quote_cur,'locked'], enter_module['amount'])

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return df_balance


def cancel_enter_order(df_balance, quote_cur, enter_module):

    # Move free amount to locked
    df_balance.loc[quote_cur,'locked'] = safe_substract(df_balance.loc[quote_cur,'locked'], enter_module['amount'])
    df_balance.loc[quote_cur,'free'] = safe_sum(df_balance.loc[quote_cur,'free'], enter_module['amount'])

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return df_balance


def cancel_exit_order(df_balance, base_cur, quantity):

    # Move free amount to locked
    df_balance.loc[base_cur,'locked'] = safe_substract(df_balance.loc[base_cur,'locked'], quantity)
    df_balance.loc[base_cur,'free'] = safe_sum(df_balance.loc[base_cur,'free'], quantity)

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return df_balance


def place_exit_order(df_balance, base_cur, quantity):

    # Move free amount to locked
    df_balance.loc[base_cur, 'free'] = safe_substract(df_balance.loc[base_cur, 'free'], quantity)
    df_balance.loc[base_cur, 'locked'] = safe_sum(df_balance.loc[base_cur, 'locked'], quantity)

    # Sync with total
    if not df_balance[['free', 'locked', 'total']].ge(0).all().all(): raise Exception('Negative balance')
    df_balance['total'] = df_balance['free'] + df_balance['locked']
    return df_balance
