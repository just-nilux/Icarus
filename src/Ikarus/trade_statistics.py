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
import pandas as pd


''' You can not manage something that you can not measure '''


def eval_hto_stat(hist_trade):

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



async def eval_balance_stats(stats, config, mongo_client):
    start_obs = await mongo_client.get_n_docs('observer', {'type':'balance'}, order=1, n=2) # pymongo.ASCENDING
    end_obs = await mongo_client.get_n_docs('observer', {'type':'balance'}, order=-1) # pymongo.ASCENDING

    balance_stat = {}
    balance_stat['Start Balance'] = next(float(item['free'] + item['locked']) for item in start_obs[0]['balances'] if item['asset'] == config['broker']['quote_currency'])
    
    open_trade_pipe = [
        {"$group": {"_id": '', "sum": {"$sum": '$enter.amount'}}},
    ]
    open_trade_amount = await mongo_client.do_find("live-trades", open_trade_pipe)

    balances = pd.DataFrame(end_obs[0]['balances'])
    balances.set_index('asset', inplace=True)
    balance_stat['End Balance'] = balances.loc[config['broker']['quote_currency']]['free'] + open_trade_amount['sum']
    balance_stat['Absolute Profit'] = balance_stat['End Balance'] - balance_stat['Start Balance']
    balance_stat['Percentage Profit'] = balance_stat['Absolute Profit']*100/balance_stat['Start Balance']

    #TODO:  Add dust amount to statistics

    stats['Balance'] = balance_stat


async def eval_strategy_stats(stats, config, mongo_client):

    stats['Strategies'] = {}
    for strategy in config['strategy'].keys():
        strategy_stat = {}
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


# TODO: Not Tested Yet
def tabulate_stats(stats, filename):
    f = open(filename,'w')
    for key, item in stats.items():
        if type(item) != list:
            f.write(key + "\n" )
            f.write(tabulate(item.items()))
            f.write("\n\n")

        else:
            f.write(tabulate(item, headers='firstrow', tablefmt='grid'))
            f.write("\n\n")
            
    f.close()


async def main(config, mongo_client):
    stats = {}
    stats['Generation Date'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    stats['Start Time'] = config['backtest']['start_time']
    stats['End Time'] = config['backtest']['end_time']
    await eval_balance_stats(stats, config, mongo_client)
    await eval_strategy_stats(stats, config, mongo_client)
    
    f = open(os.path.dirname(str(sys.argv[1])) + "/stats.json",'w')
    json.dump(stats, f,  indent=4)
    f.close()

    pass


if __name__ == "__main__":

    config_file_path = open(str(sys.argv[1]),'r')
    config = json.load(config_file_path)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    mongo_client = mongo_utils.MongoClient(config['mongodb']['host'], 
        config['mongodb']['port'], 
        config['tag'],
        clean=False)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(config, mongo_client))