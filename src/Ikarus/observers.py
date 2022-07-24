'''
Observers are the configurable read-only units. They simply collect data at the end of each execution cycle
'''
import logging
import pandas as pd
from .utils import eval_total_capital_in_lto, safe_multiply, safe_substract, safe_sum

logger = logging.getLogger('app')


class Observer():

    def __init__(self, _config):
        self.config = _config
        logger.info('creating an instance of {}'.format(__name__))
        self.equity = None


    async def balance(self, ikarus_time, df_balance):
        observation_obj = {}
        df_balance.reset_index(level=0, inplace=True)
        observer_item = list(df_balance.T.to_dict().values())
        observation_obj['type'] = 'balance'
        observation_obj['timestamp'] = ikarus_time
        observation_obj['balances'] = observer_item

        # BUG: This function updates df_balance
        return observation_obj


    async def quote_asset(self, ikarus_time, df_balance, trade_list):
        # NOTE: As a principle all the observer item that will be  visualized should not have an extra level of indent
        observation_obj = {}
        observation_obj['type'] = 'quote_asset'
        observation_obj['timestamp'] = ikarus_time
        observation_obj['free'] = df_balance.loc[self.config['broker']['quote_currency'],'free']
        observation_obj['in_trade'] = eval_total_capital_in_lto(trade_list)
        observation_obj['total'] = observation_obj['free'] + observation_obj['in_trade']

        return observation_obj


    async def quote_asset_leak(self, ikarus_time, df_balance, trade_list):
        observation_obj = {}
        observation_obj['type'] = 'quote_asset_leak'
        observation_obj['timestamp'] = ikarus_time

        free = df_balance.loc[self.config['broker']['quote_currency'],'free']
        in_trade = eval_total_capital_in_lto(trade_list)
        observation_obj['total'] = safe_sum(free, in_trade)
        observation_obj['ideal_free'] = safe_multiply(observation_obj['total'], safe_substract(1, self.config['risk_management']['max_capital_use_ratio']))
        observation_obj['real_free'] = free
        observation_obj['binary'] = int(observation_obj['ideal_free'] < observation_obj['real_free'])

        return observation_obj