'''
Observers are the configurable read-only units. They simply collect data at the end of each execution cycle
'''
import logging
import pandas as pd

logger = logging.getLogger('app.{}'.format(__name__))

class Observer():

    def __init__(self):
        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.logger.info('creating an instance of {}'.format(__name__))
        self.equity = None


    async def default_observer(self,balance=pd.DataFrame(),trade_obj={}):
        """This function returns the default observer object which observes the equity (observe.json)

        Returns:
            dict: observation.json
        """
        self.logger.debug('default_observer started')

        print(balance['ref_balance'].sum())
        observation = dict()
        observation["equity"] = self.equity

        self.logger.debug('default_observer ended')
        return observation