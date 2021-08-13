import logging
from Ikarus.enums import *
from Ikarus import mongo_utils
import json
import sys
import asyncio
from datetime import datetime

class Statistics():
    # You can not manage something that you can not measure
    def __init__(self, _config, _mongocli):
        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.logger.info('creating an instance of {}'.format(__name__))
        self.mongocli = _mongocli
        self.config = _config

        # Main objects that will store the stat information
        self.stat = {}


    async def evaluate_stats(self):

        # Evaluate Statistics
        # TODO: NEXT: Logging does not work
        self.logger.info("---------------------------------------------------------")
        self.logger.info("---------------------- Statistics -----------------------")
        self.logger.info("---------------------------------------------------------")

        self.logger.info('Total enter_expire trades: {}'.format(await self.mongocli.count("hist-trades", {'result.cause':STAT_ENTER_EXP})))
        self.logger.info('Total exit_expire trades: {}'.format(await self.mongocli.count("hist-trades", {'result.cause':STAT_EXIT_EXP})))
        self.logger.info('Total closed trades: {}'.format(await self.mongocli.count("hist-trades", {'result.cause':STAT_CLOSED})))
        self.logger.info('Total open trades: {}'.format(await self.mongocli.count("live-trades", {})))
        
        exit_expire_pipe = [
            {"$match":{"result.cause":{"$eq":"exit_expire"}}},
            {"$group": {"_id": '', "sum": {"$sum": '$result.profit'}}},
        ]
        exit_expire_profit = await self.mongocli.do_find("hist-trades", exit_expire_pipe)
        if len(exit_expire_profit): self.logger.info('hist-trades.result.profit: exit_expire : {}'.format(exit_expire_profit['sum']))
        
        closed_pipe = [
            {"$match":{"result.cause":{"$eq":"closed"}}},
            {"$group": {"_id": '', "sum": {"$sum": '$result.profit'}}},
        ]
        closed_profit = await self.mongocli.do_find("hist-trades", closed_pipe)
        if len(closed_profit):  self.logger.info('hist-trades.result.profit: closed : {}'.format(closed_profit['sum']))

        # TODO: NEXT: give index as well as a param to retrieve single value
        last_balance = await self.mongocli.get_n_docs("observer")
        for balance in last_balance[0]['balances']:
            if balance['asset'] == 'USDT':
                usdt_balance = balance['total']
                break
        self.logger.info('Final equity : {}'.format(usdt_balance))

        pass


    async def _eval_general_stats(self):
        """
        - start_time: First item in observer
        - end_time: Last item in observer
        - total_time: Last - First
        """

        start_time = await self.mongocli.get_n_docs('observer', order=1, n=2) # pymongo.ASCENDING
        end_time = await self.mongocli.get_n_docs('observer', order=-1) # pymongo.ASCENDING

        general_stats = {
            "Start Time": str(datetime.fromtimestamp(start_time[1]['timestamp']/1000)),
            "End Time": str(datetime.fromtimestamp(end_time[0]['timestamp']/1000)),
            "Total Time": ""
        }

        pass


    async def _eval_strategy_stats(self, strategy):

        # Evaluate Statistics
        # TODO: NEXT: Logging does not work
        self.logger.info("---------------------------------------------------------")
        self.logger.info("---------------------- Statistics -----------------------")
        self.logger.info("---------------------------------------------------------")

        self.logger.info('Total enter_expire trades: {}'.format(await self.mongocli.count("hist-trades", {'result.cause':STAT_ENTER_EXP})))
        self.logger.info('Total exit_expire trades: {}'.format(await self.mongocli.count("hist-trades", {'result.cause':STAT_EXIT_EXP})))
        self.logger.info('Total closed trades: {}'.format(await self.mongocli.count("hist-trades", {'result.cause':STAT_CLOSED})))
        self.logger.info('Total open trades: {}'.format(await self.mongocli.count("live-trades", {})))
        
        exit_expire_pipe = [
            {"$match":{"result.cause":{"$eq":"exit_expire"}}},
            {"$group": {"_id": '', "sum": {"$sum": '$result.profit'}}},
        ]
        exit_expire_profit = await self.mongocli.do_find("hist-trades", exit_expire_pipe)
        if len(exit_expire_profit): self.logger.info('hist-trades.result.profit: exit_expire : {}'.format(exit_expire_profit['sum']))
        
        closed_pipe = [
            {"$match":{"result.cause":{"$eq":"closed"}}},
            {"$group": {"_id": '', "sum": {"$sum": '$result.profit'}}},
        ]
        closed_profit = await self.mongocli.do_find("hist-trades", closed_pipe)
        if len(closed_profit):  self.logger.info('hist-trades.result.profit: closed : {}'.format(closed_profit['sum']))

        last_balance = await self.mongocli.get_n_docs("observer")
        for balance in last_balance['balances']:
            if balance['asset'] == 'USDT':
                usdt_balance = balance['total']
                break
        self.logger.info('Final equity : {}'.format(usdt_balance))

        pass

    async def _stat_writer(self):
        """
        Iterate over the stat dict and print in a proper format
        """

        pass


    async def get_stats(self):

        # NOTE: Required stat evaluations can be configured

        await self._eval_general_stats()
        #for strategy, item in self.config['strategies'].items():
        #    await self._eval_strategy_stats(strategy)

        
        pass

if __name__ == "__main__":

    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    mongocli = mongo_utils.MongoClient(config['mongodb']['host'], 
        config['mongodb']['port'], 
        config['tag'],
        clean=False)

    stats = Statistics(config, mongocli)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(stats.get_stats())

