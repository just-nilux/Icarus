'''
Observers are the configurable read-only units. They simply collect data at the end of each execution cycle
'''
import logging
import pandas as pd
from Ikarus.objects import GenericObject
from Ikarus.utils import eval_total_capital_in_lto, safe_multiply, safe_substract, safe_sum

class Observer():

    def __init__(self, _config):
        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.config = _config
        self.logger.info('creating an instance of {}'.format(__name__))
        self.equity = None


    async def balance(self, ikarus_time, df_balance):
        observation_obj = GenericObject()
        df_balance.reset_index(level=0, inplace=True)
        # TODO: NEXT: Convert this function to use dicts directly instead of custom GenericObjects
        observer_item = list(df_balance.T.to_dict().values())
        observation_obj.load('type','balance')
        observation_obj.load('timestamp', ikarus_time)
        observation_obj.load('balances',observer_item)

        # BUG: This function updates df_balance
        return observation_obj.get()


    async def qc(self, ikarus_time, df_balance, lto_list):
        # NOTE: As a principle all the observer item that will be  visualized should not have an extra level of indent
        observation_obj = {}
        observation_obj['type'] = 'qc'
        observation_obj['timestamp'] = ikarus_time
        observation_obj['free'] = df_balance.loc[self.config['broker']['quote_currency'],'free']
        observation_obj['in_trade'] = eval_total_capital_in_lto(lto_list)
        observation_obj['total'] = observation_obj['free'] + observation_obj['in_trade']

        return observation_obj


    async def qc_leak(self, ikarus_time, df_balance, lto_list):
        observation_obj = {}
        observation_obj['type'] = 'qc_leak'
        observation_obj['timestamp'] = ikarus_time

        free = df_balance.loc[self.config['broker']['quote_currency'],'free']
        in_trade = eval_total_capital_in_lto(lto_list)
        observation_obj['total'] = safe_sum(free, in_trade)
        observation_obj['ideal_free'] = safe_multiply(observation_obj['total'], safe_substract(1, self.config['risk_management']['max_capital_use_ratio']))
        observation_obj['real_free'] = free
        observation_obj['binary'] = int(observation_obj['ideal_free'] < observation_obj['real_free'])

        return observation_obj