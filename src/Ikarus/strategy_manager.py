import logging
from binance.helpers import round_step_size
from . import strategies
from . import resource_allocator
# TODO: Make the StrategyManager static and use it so

logger = logging.getLogger('app')


class StrategyManager():

    def __init__(self, _config, _symbol_info, _mongo_cli) -> None:

        self.strategy_list = []
        self.strategy_names = []
        for strategy_name in _config['strategy'].keys():
            
            if not hasattr(strategies,strategy_name):
                raise Exception(f'Unknown strategy: {strategy_name}!')
        
            strategy_class = getattr(getattr(strategies, strategy_name),strategy_name)
            self.strategy_list.append(strategy_class(_config, _symbol_info))
            self.strategy_names.append(strategy_name)

        self.mongo_cli = _mongo_cli
        pass

    def get_strategies(self): return self.strategy_list # NOTE: It returns a shallow copy

    def remove_strategy(self): return True

    def add_strategy(self): return True


    def feed_resource_allocation(self):
        return 

    def feed_market_scan(self):
        return