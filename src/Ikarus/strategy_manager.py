import logging
from binance.helpers import round_step_size
from . import strategies
# TODO: Make the StrategyManager static and use it so

logger = logging.getLogger('app')


class StrategyManager():

    def __init__(self, _config, _symbol_info, _mongo_cli) -> None:

        self.strategy_list = []
        self.strategy_names = []
        for strategy_name in _config['strategy'].keys():
            
            if hasattr(strategies,strategy_name):
                strategy_class = getattr(getattr(strategies, strategy_name),strategy_name)
                self.strategy_list.append(strategy_class(_config, _symbol_info))
                self.strategy_names.append(strategy_name)
            else:
                raise Exception(f'Unknown strategy: {strategy_name}!')

        self.mongo_cli = _mongo_cli
        pass

    def get_strategies(self): return self.strategy_list # NOTE: It returns a shallow copy

    def remove_strategy(self): return True

    def add_strategy(self): return True

    async def source_plugin(self): 
        # Read docs from pluging collection if exist
        col_names = await self.mongo_cli.get_collection_names()

        if not 'strmgr_plugin' in col_names:
            # NOTE: It is an Error to not to have strmgr_plugin collection.
            #       It is not an Error to not to have any document in strmgr_plugin collection
            raise Exception(f'{"strmgr_plugin"} collection does not exist')

        # Seperate the docs based on their type: resource_allocation, market_scan
        res_alloc = await self.mongo_cli.do_find('strmgr_plugin',{'type':'resource_allocation'})
        
        if len(res_alloc) == 0:
            logger.debug(f'No new resource_allocation object in {"strmgr_plugin"}')
            return

        # Feed the config changes to related strategies
        for strategy in self.strategy_list:
            strategy.strategywise_alloc_rate = res_alloc[0]['strategy'][strategy.name]

        logger.info(f'Resource allocated: {res_alloc[0]["strategy"]}')

        # Delete the consumed plugin objects from DB
        # NOTE: A resource_allocation object has no use after it is consumed. If no document in strmgr_plugin then its okay.
        #       It means that no need to do re-alloation for the current strategies. At least for now.
        await self.mongo_cli.do_delete_many('strmgr_plugin', {'type':'resource_allocation'})

        return 

    def feed_resource_allocation(self):
        return 

    def feed_market_scan(self):
        return