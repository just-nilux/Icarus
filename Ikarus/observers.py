'''
Observers are the configurable read-only units. They simply collect data at the end of each execution cycle
'''
import logging
import pandas as pd
from Ikarus.objects import GenericObject
from Ikarus.utils import eval_total_capital_in_lto

class Observer():

    def __init__(self):
        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.logger.info('creating an instance of {}'.format(__name__))
        self.equity = None

    async def sample_observer(self, df_balance, ikarus_time):
        observation_obj = GenericObject()
        df_balance.reset_index(level=0, inplace=True)
        # TODO: NEXT: Convert this function to use dicts directly instead of custom GenericObjects
        observer_item = list(df_balance.T.to_dict().values())
        observation_obj.load('type','balance')
        observation_obj.load('timestamp', ikarus_time)
        observation_obj.load('balances',observer_item)
        return observation_obj.get()

    async def qc_observer(self, df_balance, lto_list, quote_currency, ikarus_time):
        observation_obj = {}
        observation_obj['type'] = 'qc'
        observation_obj['timestamp'] = ikarus_time

        qc_dict = {}
        qc_dict['free'] = df_balance.loc[quote_currency,'free']
        qc_dict['in_trade'] = eval_total_capital_in_lto(lto_list)
        qc_dict['total'] = qc_dict['free'] + qc_dict['in_trade']

        observation_obj['qc'] = qc_dict
        return observation_obj    