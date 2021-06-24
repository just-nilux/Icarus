import re
import pymongo
import logging
import asyncio
from datetime import datetime
import motor.motor_asyncio
from time import time

class MongoClient():

    
    def __init__(self, _host, _port, _db='bot') -> None:
        self.client = motor.motor_asyncio.AsyncIOMotorClient(host=_host, port=_port)
        self.logger = logging.getLogger('app.{}'.format(__name__))

        # Drop the db if it is no the main one
        if _db != 'bot':
            self.client.drop_database(_db)
        self.db_bot = self.client[_db]

    async def count(self, col, query={}) -> None:
        return await self.db_bot[col].count_documents(query)

    async def do_find(self, col, query) -> None:
        """
        This function reads the selected item from the given collection

        Args:
            col ([type]): [description]
            item ([type]): [description]
        """
        result = self.db_bot[col].find(query)
        docs = await result.to_list(None)

        return docs


    async def do_insert(self, col, item) -> None:
        """
        This function writes the selected item into the collection 

        Args:
            col (str): Name of the collection: [live-trade | hist-trade | observer]
            item (dict): Dictionary item
        """        
        # Add timestamp as the "_id" of the document
        item['_id'] = int(time() * 1000)
        result = await self.db_bot[col].insert_one(item)
        return result


    async def do_insert_many(self, col, item_dict) -> None:
        """
        This function writes the selected item into the collection 

        Args:
            col (str): Name of the collection: [live-trade | hist-trade | observer]
            item_dict (dict): Dictionary of GenericObject
        """        

        insert_list = []
        for pair, obj in item_dict.items():
            obj.load('pair',pair)
            obj.load('_id',int(time() * 1000))
            insert_list.append(obj.get())
            
        result = await self.db_bot[col].insert_many(insert_list)
        return result


    async def do_update(self, col, item) -> None:
        """
        This function updates the selected item in the given collection

        Args:
            col (str): [description]
            item (dict): [description]
        """
        # TODO: Test needed
        # TODO: Update an item in a deeper position in the hierarchy
        result = await self.db_bot[col].update_one({'_id': item['_id']}, {'$set': {'status': item['status']}})
        self.logger.info(f"do_update: {item['_id']} in the [{col}]")
        return result


    async def do_delete(self, col, query) -> None:
        """
        This function reads the selected item from the given collection

        Args:
            col (string): collection to delete document
            query (dict): query to delete document
        """
        # TODO: Test needed
        result = self.db_bot[col].delete_one(query)
        self.logger.info(f"do_delete: {result.deleted_count} item from [{col}]")
        return result

async def test_db():
    item = dict({"key":"value"})
    item['_id'] = int(time() * 1000)
    print(item['_id'])
    result = await mongocli.do_insert('observer',item)
    print('Result:',result)
    return True

if __name__ == "__main__":
    mongocli = MongoClient("localhost", 27017)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_db())
