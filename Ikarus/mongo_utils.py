import re
import pymongo
import logging
import asyncio
from datetime import datetime
import motor.motor_asyncio

class MongoClient():
    def __init__(self, _host, _port) -> None:
        #self.client = pymongo.MongoClient(host=_host, port=_port)
        self.client = motor.motor_asyncio.AsyncIOMotorClient(host=_host, port=_port)
        self.logger = logging.getLogger('app.{}'.format(__name__))

        # get the "bot" database
        self.db_bot = self.client['bot']

        # get the collections
        self.col_observer = self.db_bot['observer']
        self.col_live_trade = self.db_bot['live-trade']
        self.col_hist_trade = self.db_bot['hist-trade']

    async def find(self, col, item) -> None:
        """
        This function reads the selected item from the given collection

        Args:
            col ([type]): [description]
            item ([type]): [description]
        """        
        pass


    async def do_insert(self, col, item) -> None:
        """
        This function writes the selected item into the collection 

        Args:
            col (str): Name of the collection: [live-trade | hist-trade | observer]
            item (dict): Dictionary item
        """        
        self.logger.info(f"Item written to [{col}]")

        # Add timestamp as the "_id" of the document
        item['_id'] = int(datetime.now().timestamp())
        result = await self.db_bot[col].insert_one(item)
        return result

    async def do_update(self, col, item) -> None:
        """
        This function updates the selected item in the given collection

        Args:
            col (str): [description]
            item (dict): [description]
        """        
        pass

    async def do_insert_many(self, col, item_dict) -> None:
        """
        This function writes the selected item into the collection 

        Args:
            col (str): Name of the collection: [live-trade | hist-trade | observer]
            item (dict): Dictionary item
        """        
        for pair, obj in item_dict.items():
            obj.load('pair',pair)
            await self.insert(col, obj)

        return True

async def test_db():      
    result = await mongocli.do_insert('observer',{"key":"value"})
    print('Result:',result)
    return True

if __name__ == "__main__":
    mongocli = MongoClient("localhost", 27017)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_db())
