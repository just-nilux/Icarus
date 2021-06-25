import re
import pymongo
import logging
import asyncio
from datetime import datetime
import motor.motor_asyncio
from time import time, sleep
from objects import GenericObject
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
            #timestamp = int(time() * 1000)
            #print("int value:",timestamp)
            obj.load('_id',int(time() * 1000))
            insert_list.append(obj.get())
            sleep(0.01)
            
        result = await self.db_bot[col].insert_many(insert_list)
        return result


    async def do_update(self, col, query, update) -> None:
        """
        This function updates the selected item in the given collection

        Args:
            col (str): [description]
            item (dict): [description]
        """
        # TODO: Test needed
        # TODO: Update an item in a deeper position in the hierarchy
        #result = await self.db_bot[col].update_one({'_id': item['_id']}, {'$set': {'status': item['status']}})
        result = await self.db_bot[col].update_one(query, update)

        self.logger.info(f"do_update: in the [{col}]")
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

async def test1():
    #import sys
    # insert at 1, 0 is the script path (or '' in REPL)
    #sys.path.insert(1, 'c:\\Users\\bilko\\PycharmProjects\\trade-bot\\Ikarus')

    #import o
    to1, to2, to3 = GenericObject('trade'), GenericObject('trade'), GenericObject('trade')
    to1.load('status','open_enter')
    to2.load('status','open_enter')
    to3.load('status','open_exit')

    trade_dict = dict({'BTCUSDT':to1, 'XRPUSDT':to2, 'AVAXUSDT':to3})


    # Insert
    print('Before insert many:')
    result = await mongocli.do_insert_many("live-trades",trade_dict)
    print('Result:',result)
    '''
    # Find
    lto_list = await mongocli.do_find('live-trades',{'status':'open_enter'})
    print('lto_list:',lto_list)
    
    # Update the values
    for lto in lto_list:
        result_update = await mongocli.do_update(
            "live-trades",
            {'_id': lto['_id']},
            {'$set': {'status': lto['status']}})
        print('result_update:',result_update)

    # Update
    for lto in lto_list:
        result_update = await mongocli.do_update(
            "live-trades",
            {'_id': lto['_id']},
            {'$set': {'status': lto['status']}})
        print('result_update:',result_update)
    
    
    # Delete
    result_delete = await mongocli.do_delete('live-trades',{'status':'open_exit'})
    print('result_delete:',result_delete)
    '''
    return True

if __name__ == "__main__":
    mongocli = MongoClient("localhost", 27017, 'mongo-test')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test1())
