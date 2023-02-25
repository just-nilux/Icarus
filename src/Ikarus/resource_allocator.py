import math
import logging
from abc import ABC, abstractmethod
from .objects import EState
from .utils import safe_multiply, safe_sum, safe_divide


class DiscreteStrategyAllocator():
    '''
    Sample Configuration:

    "strategy_allocation":{
        "type": "DiscreteStrategyAllocator",
        "kwargs": {
            "initial_capital": 20000,
            "distribution_config": ["FixedLimitTarget_03", "FixedLimitTarget_02", "FixedLimitTarget_01"],
            "capital_coeff":0.9, 
            "stop_capital":null,
            "capital_limit": 50
        }
    },
    '''

    def __init__(self, distribution_config, initial_capital=None, capital_coeff=1, stop_capital=None, capital_limit=0) -> None:

        # In case of discrete allocation, max_capital_use ratio is used for inital allocation afterwards it is not used
        self.capital_coeff = capital_coeff
        self.stop_capital = stop_capital
        self.distribution_status = None
        self.capital_limit = capital_limit
        
        if type(distribution_config) == list:
            cap_per_strategy = safe_divide(1,len(distribution_config))
            self.distribution_config = {key: cap_per_strategy for key in distribution_config}

        elif type(distribution_config) == dict:
            self.distribution_config = distribution_config

        if initial_capital != None:
            self.set_capital(initial_capital)


    def set_capital(self, initial_capital) -> dict:
        self.strategy_capitals = {key: safe_multiply(value,initial_capital) for key, value in self.distribution_config.items()}
        self.distribution_status = self.distribute()


    def set_distribution_config(self, config):
        self.distribution_config = config


    def distribute(self) -> dict:
        distribution = {}
        for key, value in self.strategy_capitals.items():
            strategy_cap = safe_multiply(value,self.capital_coeff)

            if self.capital_limit > strategy_cap:
                strategy_cap = self.capital_limit
        
            distribution[key] = strategy_cap

        return distribution


    def allocate(self, df_balance, live_trades) -> dict:

        if not hasattr(self,'strategy_capitals'):
            # NOTE: Temporary solution
            self.set_capital(df_balance.loc['USDT','free'])

        # Check if a trade is closed
        #   If so, apply the profit amount to the self.distribution_status['strategy1']
        for lt in live_trades:
            if lt.status == EState.CLOSED:
                # trade.result.profit reflects the impact of a trade on balance
                self.strategy_capitals[lt.strategy] = safe_sum(self.strategy_capitals[lt.strategy], lt.result.profit)
        
        total_capital = 0
        for value in self.strategy_capitals.values():
            total_capital = safe_sum(total_capital, value)
        
        # Check if stop capital is reached
        #   If so, make all allocatıons 0 to stop strategies from creating new trades
        if self.stop_capital:
            if total_capital <= self.stop_capital:
                return {key: 0 for key in self.distribution_config.keys()}
        # Apply max_capital_use_coeff by restricting the in_use amount if specified

        self.distribution_status = self.distribute()
        return self.distribution_status
