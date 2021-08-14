import logging
from Ikarus.enums import *
from Ikarus import mongo_utils
import json
import sys
import os
import asyncio
from datetime import datetime
from tabulate import tabulate
from itertools import chain, groupby
import operator
import pathlib

class Statistics():
    # You can not manage something that you can not measure

    def __init__(self, _config, _mongocli):
        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.logger.info('creating an instance of {}'.format(__name__))
        self.mongocli = _mongocli
        self.config = _config

        # TODO: This ehader section can be coınfigured based on desired stats
        strategy_table_header = ['Strategy', 'Live Trades', 'Closed', 'Enter Expired', 'Exit Expired', 'Closed Profit', 'Exit Expired Profit']
        # Main objects that will store the stat information
        self.stat = {}
        self.stat['general'] = []
        self.stat['strategies'] = []
        self.stat['strategies'].append(strategy_table_header)

    async def evaluate_stats(self):

        # Evaluate Statistics
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

        start_obs = await self.mongocli.get_n_docs('observer', order=1, n=2) # pymongo.ASCENDING
        end_obs = await self.mongocli.get_n_docs('observer', order=-1) # pymongo.ASCENDING

        start_dt = datetime.fromtimestamp(start_obs[1]['timestamp']/1000)
        end_dt = datetime.fromtimestamp(end_obs[0]['timestamp']/1000)

        start_obs[0]['balances']
        start_balance = next(float(item['free'] + item['locked']) for item in start_obs[0]['balances'] if item['asset'] == self.config['broker']['quote_currency'])
        end_balance = next(float(item['free'] + item['locked']) for item in end_obs[0]['balances'] if item['asset'] == self.config['broker']['quote_currency'])

        general_stats = {
            "Start Time": str(start_dt),
            "End Time": str(end_dt),
            "Total Time": (end_dt - start_dt).total_seconds() / 60, # In second
            "Start Balance": "{:.2f} {}".format(start_balance, self.config['broker']['quote_currency']),
            "End Balance": "{:.2f} {}".format(end_balance, self.config['broker']['quote_currency']),
            "Absolute Profit": "{:.2f} {}".format(end_balance - start_balance, self.config['broker']['quote_currency']),
            "Total Profit": "% {:.2f}".format((end_balance - start_balance)*100/start_balance),
        }

        self.stat['general'] = general_stats
        pass


    async def _eval_strategy_stats(self, strategy):
        """
        The format should be list of list:
        [AlwaysEnter, 1, 2, 3]
        [FallingKnifeCatcher, 1, 2, 3]
        etc
        Args:
            strategy ([type]): [description]
        """
        strategy_stats = []
        strategy_stats.append(strategy)
        strategy_stats.append(int(await self.mongocli.count("live-trades", {'strategy':strategy})))
        strategy_stats.append(int(await self.mongocli.count("hist-trades", {'strategy':strategy, 'result.cause':STAT_CLOSED})))
        strategy_stats.append(int(await self.mongocli.count("hist-trades", {'strategy':strategy, 'result.cause':STAT_ENTER_EXP})))
        strategy_stats.append(int(await self.mongocli.count("hist-trades", {'strategy':strategy, 'result.cause':STAT_EXIT_EXP})))

        closed_pipe = [
            {"$match":{"strategy":{"$eq":strategy}, "result.cause":{"$eq":"closed"}}},
            {"$group": {"_id": '', "sum": {"$sum": '$result.profit'}}},
        ]
        closed_profit = await self.mongocli.do_find("hist-trades", closed_pipe)
        if closed_profit != []: 
            strategy_stats.append(closed_profit['sum']) 
        else: 
            strategy_stats.append(0)

        exit_expire_pipe = [
            {"$match":{"strategy":{"$eq":strategy}, "result.cause":{"$eq":"exit_expire"}}},
            {"$group": {"_id": '', "sum": {"$sum": '$result.profit'}}},
        ]
        exit_expire_profit = await self.mongocli.do_find("hist-trades", exit_expire_pipe)
        if exit_expire_profit != []: 
            strategy_stats.append(exit_expire_profit['sum']) 
        else: 
             strategy_stats.append(0)

        self.stat['strategies'].append(strategy_stats)
        pass

    async def write_stats(self):
        """
        Iterate over the stat dict and print in a proper format
        I need everythoing in list of list

        []
        """
        write_location = pathlib.Path(config_file_path.name).parent.joinpath('stat.txt')
        print(write_location.name)

        with write_location.open(mode='w') as fid:
            fid.write("sdaasda")
            fid.close()
        print(write_location)
        f = open(write_location,'w')
        for key, item in self.stat.items():
            if type(item) != list:
                f.write(key + "\n" )
                f.write(tabulate(item.items()))
                f.write("\n\n")

            else:
                f.write(tabulate(item, headers='firstrow', tablefmt='grid'))
                f.write("\n\n")
                
        f.close()
        #print(tabulate(self.stat.items()))

        pass


    async def eval_stats(self):

        # NOTE: Required stat evaluations can be configured

        await self._eval_general_stats()
        for strategy in self.config['strategy'].keys():
            print(strategy)
            await self._eval_strategy_stats(strategy)
        pass

    async def main(self):

        await self.eval_stats()
        await self.write_stats()
        pass


if __name__ == "__main__":

    config_file_path = open(str(sys.argv[1]),'r')
    config = json.load(config_file_path)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    mongocli = mongo_utils.MongoClient(config['mongodb']['host'], 
        config['mongodb']['port'], 
        config['tag'],
        clean=False)

    stats = Statistics(config, mongocli)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(stats.main())

