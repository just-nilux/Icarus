import logging
from binance.helpers import round_step_size
from .enums import *
from . import strategies

# TODO: Make the StrategyManager static and use it so
class StrategyManager():

    def __init__(self, _config , _symbol_info) -> None:

        self.strategies = {
            "AlwaysEnter": strategies.AlwaysEnter.AlwaysEnter,
            "AlwaysEnter90": strategies.AlwaysEnter90.AlwaysEnter90,
            "FallingKnifeCatcher": strategies.FallingKnifeCatcher.FallingKnifeCatcher,
            "NewStrategy": strategies.NewStrategy.NewStrategy,
        }

        self.strategy_list = []
        for strategy_name in _config['strategy'].keys():
            strategy_class = self.strategies[strategy_name]
            self.strategy_list.append(strategy_class(_config, _symbol_info))
        pass

    def get_strategies(self): return self.strategy_list # NOTE: It returns a shallow copy

    def remove_strategy(self): return True

    def add_strategy(self): return True

    def receive_from_plugin(self): 
        # Read docs from pluging collection if exist

        # Seperate the docs based on their type: resource_allocation, market_scan

        # Feed the config changes to related strategies

        # Delete the consumed plugin objects from DB

        return 

    def feed_resource_allocation(self):
        return 

    def feed_market_scan(self):
        return