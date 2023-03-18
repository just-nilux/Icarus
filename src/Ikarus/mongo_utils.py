from exceptions import NotImplementedException
from pymongo import MongoClient, DESCENDING
import logging
import asyncio
import motor.motor_asyncio
from objects import EState, ECause, trade_from_dict
from dataclasses import asdict

logger = logging.getLogger('app')


class MongoClient():

    
    def __init__(self, host, port, database='bot', clean=False) -> None:
        self.client = motor.motor_asyncio.AsyncIOMotorClient(host=host, port=port)

        # TODO: Implement normal client as well. It is hard to test with asycn cli
        #self.normal_client = MongoClient(host=_host, port=_port)
        logger.debug('Mongo client initiated')

        # Drop the db if it is no the main one
        if clean:
            self.client.drop_database(database)
        self.db_bot = self.client[database]


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
            logger.debug(f"do_find [{col}]: total found document: {len(docs)}")
        elif type(query) == list:
            async for doc in self.db_bot[col].aggregate(query):
                docs=doc
        return docs


    async def do_aggregate(self, col, query) -> None:
        docs = []
        if type(query) == list:
            cursor = self.db_bot[col].aggregate(query)
            async for doc in cursor:
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
        
        logger.debug(f'do_insert_one [{col}]: inserted id "{result.inserted_id}"')
        return result


    async def do_insert_many(self, col, item_list) -> None:
        """
        This function writes the selected item into the collection 

        Args:
            col (string): db collection
            item_list (list): 
        """        
        result = await self.db_bot[col].insert_many(item_list)
        logger.debug(f"do_insert_many [{col}]: inserted ids {result.inserted_ids}")
        return result


    async def do_update(self, col, query, update) -> None:
        """
        Args:
            col (string): db collection
            query (dict): json query
            update (dict): update rule
        """
        result = await self.db_bot[col].update_one(query, update)
        if '_id' in query.keys(): logger.debug(f"do_update [{col}]: \"{query['_id']}\"")
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
        logger.debug(f"do_delete [{col}]: prev count {prev_count}, after count {after_count}")
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

async def update_live_trades(mongo_client, trade_list): # TODO: REFACTOR: checkout
    # TODO: Move queries outside of this script
    for trade in trade_list:

        # NOTE: Check for status change is removed since some internal changes might have been performed on status and needs to be reflected to history
        # If the status is closed then, it should be inserted to [hist-trades] and deleted from the [live-trades]
        if trade.status == EState.CLOSED:
            # This if statement combines the "update the [live-trades]" and "delete the closed [live-trades]"
            result_insert = await mongo_client.do_insert_one("hist-trades",asdict(trade))
            result_remove = await mongo_client.do_delete_many("live-trades",{"_id":trade._id}) # "do_delete_many" does not hurt, since the _id is unique

        # NOTE: Manual trade option is omitted, needs to be added
        # TODO: REFACTORING: Why did you handle all of these 3 state in the same place?
        elif trade.status in [ EState.OPEN_EXIT, EState.WAITING_EXIT, EState.EXIT_EXP]:

            if trade.exit: update_val_trade_exit = asdict(trade.exit)
            else: update_val_trade_exit = None

            result_update = await mongo_client.do_update( 
                "live-trades",
                {'_id': trade._id},
                {'$set': {'status': trade.status,
                        'exit': update_val_trade_exit,
                        'result.enter': asdict(trade.result.enter),
                        'order_stash': [asdict(order) for order in trade.order_stash]
                    }})
                
        elif trade.status == EState.OPEN_ENTER:
            # - STAT_OPEN_ENTER might be expired and postponed with some additional changes in 'enter' item (changes in enter and history)
            result_update = await mongo_client.do_update( 
                "live-trades",
                {'_id': trade._id},
                {'$set': {'status': trade.status, 'enter': asdict(trade.enter) }}) # NOTE: REFACTORING: history removed

        else:
            pass

async def do_find_trades(mongo_client, col, query={}):
    trade_list = await mongo_client.do_find(col,query)
    return [trade_from_dict(hto) for hto in trade_list]

async def do_aggregate_trades(mongo_client, col, query={}):
    trade_list = await mongo_client.do_aggregate(col,query)
    return [trade_from_dict(hto) for hto in trade_list]

async def do_find_report(mongo_client, col, query={}):
    reports = await mongo_client.do_find(col,query)
    return reports[0]['data']

async def do_aggregate_multi_query(mongo_client, col, queries=[{}]):

    query_coroutines = []
    for query in queries:
        query_coroutines.append(mongo_client.do_aggregate(col,query))

    return await asyncio.gather(*query_coroutines)