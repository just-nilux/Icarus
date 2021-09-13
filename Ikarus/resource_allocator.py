import math
from .enums import *
import logging

class ResourceAllocator():

    def __init__(self, _strategy_names, _mongo_cli) -> None:
        self.strategy_names = _strategy_names
        self.mongo_cli = _mongo_cli
        self.logger = logging.getLogger('app.{}'.format(__name__))
        pass

    async def allocate(self):
        # Clear all the resource_allocation if any
        await self.mongo_cli.do_delete_many(COLL_STR_MGR_PLUGIN, {'type':'resource_allocation'})

        res_alloc_obj = self.alloc_default()
        result = await self.strategy_manager_plugin(res_alloc_obj)
        self.logger.debug(f'Resource Allocate object "{result.inserted_id}" inserted')
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
        return await self.mongo_cli.do_insert_one(COLL_STR_MGR_PLUGIN, res_alloc_obj)

