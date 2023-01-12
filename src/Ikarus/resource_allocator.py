import math
import logging
from abc import ABC, abstractmethod
from .objects import EState
from .utils import safe_multiply, safe_sum, safe_divide

logger = logging.getLogger('app')

class SharedTradeAllocator():

    def __init__(self, pairs, ) -> None:
        self.pairs = pairs


    def distribute(self, free_trade_slot, free_capital, free_pairs):
        capital_per_trade = safe_divide(free_capital, free_trade_slot)
        return {pair: capital_per_trade for pair in free_pairs}


    def allocate(self, max_live_trade, strategy_capital, trade_list):

        in_trade_capital = 0
        in_trade_pairs = set()
        for trade in trade_list:
            if trade.status == EState.CLOSED:
                continue
            in_trade_pairs.append(trade.pair)
            in_trade_capital = safe_sum(in_trade_capital, trade.enter.amount)
        
        free_capital = strategy_capital - in_trade_capital
        free_pairs = set(self.pairs) - in_trade_pairs
        free_trade_slot = max_live_trade-len(in_trade_pairs)
        
        return self.distribute(free_trade_slot, free_capital, free_pairs)


class DiscreteStrategyAllocator():

    def __init__(self, initial_capital, distribution_config, max_capital_use=1, stop_capital=None) -> None:
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
