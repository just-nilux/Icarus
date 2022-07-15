from .exceptions import NotImplementedException
from pymongo import MongoClient, DESCENDING
import logging
import asyncio
import motor.motor_asyncio

class MongoClient():

    
    def __init__(self, host, port, db='bot', clean=False) -> None:
        self.client = motor.motor_asyncio.AsyncIOMotorClient(host=host, port=port)

        # TODO: Implement normal client as well. It is hard to test with asycn cli
        #self.normal_client = MongoClient(host=_host, port=_port)
        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.logger.debug('Mongo client initiated')

        # Drop the db if it is no the main one
        if clean:
            self.client.drop_database(db)
        self.db_bot = self.client[db]


    async def get_collection_names(self):
        return await self.db_bot.list_collection_names()


    async def count(self, col, query={}) -> None:
        return await self.db_bot[col].count_documents(query)


    async def do_find(self, col, query) -> None:
        """
        This function reads the selected item from the given collection

        Args:
            col ([type]): [description]
            item ([type]): [description]
        """
        docs = []
        if type(query) == dict:
            result = self.db_bot[col].find(query)
            docs = await result.to_list(None)
            self.logger.debug(f"do_find [{col}]: total found document: {len(docs)}")
        elif type(query) == list:
            async for doc in self.db_bot[col].aggregate(query):
                docs=doc
        return docs


    async def do_aggregate(self, col, query) -> None:
        docs = []
        if type(query) == list:
            async for doc in self.db_bot[col].aggregate(query):
                docs.append(doc)
        else:
            raise NotImplementedException('do_aggregate requires type list as input')
        return docs


    async def do_insert_one(self, col, item) -> None:
        """
        Args:
            col (str): Name of the collection: [live-trade | hist-trade | observer]
            item (dict): Dictionary item
        """


        result = await self.db_bot[col].insert_one(item)
        
        self.logger.debug(f'do_insert_one [{col}]: inserted id "{result.inserted_id}"')
        return result


    async def do_insert_many(self, col, item_list) -> None:
        """
        This function writes the selected item into the collection 

        Args:
            col (string): db collection
            item_list (list): 
        """        
        result = await self.db_bot[col].insert_many(item_list)
        self.logger.debug(f"do_insert_many [{col}]: inserted ids {result.inserted_ids}")
        return result


    async def do_update(self, col, query, update) -> None:
        """
        Args:
            col (string): db collection
            query (dict): json query
            update (dict): update rule
        """
        result = await self.db_bot[col].update_one(query, update)
        if '_id' in query.keys(): self.logger.debug(f"do_update [{col}]: \"{query['_id']}\"")
        return result


    async def do_delete_many(self, col, query) -> None:
        """
        Args:
            col (string): db collection
            query (dict): json query
        """
        # TODO: Remove the count statments or optimize them, they look ugly
        prev_count = await self.count(col)
        result = self.db_bot[col].delete_many(query)
        after_count = await self.count(col)
        self.logger.debug(f"do_delete [{col}]: prev count {prev_count}, after count {after_count}")
        return result

# Specific Methods:
    async def get_n_docs(self, col, query={}, order=DESCENDING, n=1) -> None:
        """
        This function reads the selected item from the given collection

        Args:
            col ([type]): [description]
            item ([type]): [description]
        """
        result = self.db_bot[col].find(query).sort('_id', order).limit(n)
        doc_list = []
        async for document in result:
            doc_list.append(dict(document))

        assert 'doc_list' in locals(), "No last document!"
        assert len(doc_list) > 0, "No document"
        return doc_list

