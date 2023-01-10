import math
import logging
from abc import ABC, abstractmethod
from .objects import EState
from .utils import safe_multiply

logger = logging.getLogger('app')


class ResourceAllocator_legacy():

    def __init__(self, _strategy_names, _mongo_cli) -> None:
        self.strategy_names = _strategy_names
        self.mongo_cli = _mongo_cli
        pass

    async def allocate(self):
        # Clear all the resource_allocation if any
        await self.mongo_cli.do_delete_many('strmgr_plugin', {'type':'resource_allocation'})

        res_alloc_obj = self.alloc_default()
        result = await self.strategy_manager_plugin(res_alloc_obj)
        logger.debug(f'Resource Allocate object "{result.inserted_id}" inserted')
        return result


    def alloc_default(self):
        # Do simple equal allocation for each strategy
        capital_share = round(math.floor(1/len(self.strategy_names)*10000)*0.0001, 4)
        allocation_dict = { name : capital_share for name in self.strategy_names  }
        return {'type':'resource_allocation','strategy':allocation_dict}

    def alloc_custom():
        # Do experimental allocation
        pass

    def alloc_from_backtest():
        # Do allocation based on the historical results in backtest
        pass

    async def strategy_manager_plugin(self, res_alloc_obj):
        # Insert data to DB
        return await self.mongo_cli.do_insert_one('strmgr_plugin', res_alloc_obj)


class DiscreteStrategyAllocator():

    def __init__(self, initial_capital, distribution_config, max_capital_use=None, stop_capital=None) -> None:
        self.distribution_config = distribution_config

        # In case of discrete allocation, max_capital_use ratio is used for inital allocation afterwards it is not used
        self.max_capital_use = max_capital_use
        self.stop_capital = stop_capital
        self.distribution_status = None
        
        self.strategy_capitals = {key: safe_multiply(value,initial_capital) for key, value in self.distribution_config.items()}
        self.distribution_status = self.distribute()


    def set_distribution_config(self, config):
        self.distribution_config = config


    def distribute(self):
        return {key: safe_multiply(value,self.max_capital_use) for key, value in self.strategy_capitals.items()}


    def allocate(self, df_balance, live_trades):

        # Check if a trade is closed
        #   If so, apply the profit amount to the self.distribution_status['strategy1']
        for lt in live_trades:
            if lt.status == EState.CLOSED:
                # trade.result.profit reflects the impact of a trade on balance
                self.strategy_capitals[lt.strategy] += lt.result.profit
                
        # Check if stop capital is reached
        #   If so, make all allocatıons 0 to stop strategies from creating new trades
        if self.stop_capital:
            total_capital = sum(self.strategy_capitals.values())
            if total_capital <= self.stop_capital:
                return {key: 0 for key in self.distribution_config.keys()}
        # Apply max_capital_use by restricting the in_use amount if specified

        self.distribution_status = self.distribute()
        return self.distribution_status

