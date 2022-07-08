from Ikarus.objects import ECause
from .enums import *
from . import mongo_utils
import json
import sys
import os
import asyncio
from datetime import datetime, timezone
from tabulate import tabulate
from .utils import safe_substract


# You can not manage something that you can not measure

'''


def tabulate_stats(self):    
    f = open(self.statfile+"/stat.txt",'w')
    for key, item in self.stat.items():
        if type(item) != list:
            f.write(key + "\n" )
            f.write(tabulate(item.items()))
            f.write("\n\n")

        else:
            f.write(tabulate(item, headers='firstrow', tablefmt='grid'))
            f.write("\n\n")
            
    f.close()


async def eval_hto_stat(self, hist_trade):

    hto_stat = [ 
        hist_trade._id,
        hist_trade.strategy,
        hist_trade.pair,
        datetime.fromtimestamp(hist_trade.result.enter.time/1000, timezone.utc),
        datetime.fromtimestamp(hist_trade.result.exit.time/1000, timezone.utc),
        safe_substract(hist_trade.result.exit.amount, hist_trade.result.enter.amount),
        100*(hist_trade.result.exit.price - hist_trade.result.enter.price)/hist_trade.result.enter.price
    ]
    return hto_stat

'''

async def eval_balance_stats(stats, mongo_client):
    start_obs = await mongo_client.get_n_docs('observer', {'type':'balance'}, order=1, n=2) # pymongo.ASCENDING
    end_obs = await mongo_client.get_n_docs('observer', {'type':'balance'}, order=-1) # pymongo.ASCENDING

    start_dt = datetime.fromtimestamp(start_obs[1]['timestamp']/1000, timezone.utc)
    end_dt = datetime.fromtimestamp(end_obs[0]['timestamp']/1000, timezone.utc)

    #stats['Start Time'] = str(start_dt)
    #stats['End Time'] = str(end_dt)
    #stats['Total Time'] = "{:.2f} days".format((end_dt - start_dt).total_seconds() / (60*60*24)), # In second
    balance_stat = {}
    balance_stat['Start Balance'] = next(float(item['free'] + item['locked']) for item in start_obs[0]['balances'] if item['asset'] == config['broker']['quote_currency'])
    balance_stat['End Balance'] = next(float(item['free'] + item['locked']) for item in end_obs[0]['balances'] if item['asset'] == config['broker']['quote_currency'])
    balance_stat['Total Profit'] = (balance_stat['End Balance'] - balance_stat['Start Balance'])*100/balance_stat['Start Balance']
    stats['Balance'] = balance_stat
    


async def eval_strategy_stats(stats, mongo_client):

    stats['Strategies'] = {}
    for strategy in config['strategy'].keys():
        strategy_stat = {}
        strategy_stat['Name'] = strategy
        strategy_stat['Live Trades'] = int(await mongo_client.count("live-trades", {'strategy':strategy}))
        strategy_stat['Closed'] = int(await mongo_client.count("hist-trades", {'strategy':strategy, 'result.cause':ECause.CLOSED}))
        strategy_stat['Enter Expired'] = int(await mongo_client.count("hist-trades", {'strategy':strategy, 'result.cause':ECause.ENTER_EXP}))
        strategy_stat['Exit Expired'] = int(await mongo_client.count("hist-trades", {'strategy':strategy, 'result.cause':ECause.EXIT_EXP}))

        closed_pipe = [
            {"$match":{"strategy":{"$eq":strategy}, "result.cause":{"$eq":"closed"}}},
            {"$group": {"_id": '', "sum": {"$sum": '$result.profit'}}},
        ]
        closed_profit = await mongo_client.do_find("hist-trades", closed_pipe)
        if closed_profit != []: 
            strategy_stat['Closed Expired'] = closed_profit['sum']
        else: 
            strategy_stat['Closed Expired'] = 0

        exit_expire_pipe = [
            {"$match":{"strategy":{"$eq":strategy}, "result.cause":{"$eq":"exit_expire"}}},
            {"$group": {"_id": '', "sum": {"$sum": '$result.profit'}}},
        ]
        exit_expire_profit = await mongo_client.do_find("hist-trades", exit_expire_pipe)
        if exit_expire_profit != []: 
            strategy_stat['Exit Expired Expired'] = exit_expire_profit['sum']
        else: 
            strategy_stat['Exit Expired Expired'] = 0
        stats['Strategies'][strategy] = strategy_stat


async def main():
    mongo_client = mongo_utils.MongoClient(config['mongodb']['host'], 
        config['mongodb']['port'], 
        config['tag'],
        clean=False)
    stats = {}
    now = datetime.now()
    now.strftime("%d/%m/%Y %H:%M:%S")
    stats['date'] = now.strftime("%d/%m/%Y %H:%M:%S")
    await eval_balance_stats(stats, mongo_client)
    await eval_strategy_stats(stats, mongo_client)
    
    f = open(os.path.dirname(str(sys.argv[1])) + "/stat.txt",'w')
    json.dump(stats, f,  indent=4)
    f.close()


    pass


if __name__ == "__main__":

    config_file_path = open(str(sys.argv[1]),'r')
    config = json.load(config_file_path)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)


    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

