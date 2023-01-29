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
            "max_capital_use":0.9, 
            "stop_capital":null
        }
    },
    '''

    def __init__(self, initial_capital, distribution_config, max_capital_use=1, stop_capital=None) -> None:

        # In case of discrete allocation, max_capital_use ratio is used for inital allocation afterwards it is not used
        self.max_capital_use = max_capital_use
        self.stop_capital = stop_capital
        self.distribution_status = None
        
        if type(distribution_config) == list:
            cap_per_strategy = safe_divide(1,len(distribution_config))
            self.distribution_config = {key: cap_per_strategy for key in distribution_config}

        elif type(distribution_config) == dict:
            self.distribution_config = distribution_config

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
                self.strategy_capitals[lt.strategy] = safe_sum(self.strategy_capitals[lt.strategy], lt.result.profit)
        
        total_capital = 0
        for value in self.strategy_capitals.values():
            total_capital = safe_sum(total_capital, value)
        
        # Check if stop capital is reached
        #   If so, make all allocatıons 0 to stop strategies from creating new trades
        if self.stop_capital:
            if total_capital <= self.stop_capital:
                return {key: 0 for key in self.distribution_config.keys()}
        # Apply max_capital_use by restricting the in_use amount if specified

        self.distribution_status = self.distribute()
        return self.distribution_status
