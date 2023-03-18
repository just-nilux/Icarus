import logging
from binance.helpers import round_step_size
import strategies
# TODO: Make the StrategyManager static and use it so

logger = logging.getLogger('app')


class StrategyManager():

    def __init__(self, _config, _symbol_info, _mongo_cli) -> None:

        self.strategy_list = []
        self.strategy_names = []
        for strategy_tag, strategy_config in _config['strategy'].items():
            
            if not hasattr(strategies,strategy_config['strategy']):
                raise Exception(f'Unknown strategy: {strategy_config["strategy"]}!')
        
            strategy_class = getattr(getattr(strategies, strategy_config["strategy"]),strategy_config["strategy"])
            self.strategy_list.append(strategy_class(strategy_tag, _config, _symbol_info))
            self.strategy_names.append(strategy_tag)

        self.mongo_cli = _mongo_cli
        pass

    def get_strategies(self): return self.strategy_list # NOTE: It returns a shallow copy

    def remove_strategy(self): return True

    def add_strategy(self): return True


    def feed_resource_allocation(self):
        return 

    def feed_market_scan(self):
        return