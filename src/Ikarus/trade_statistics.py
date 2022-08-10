from numpy import average
from .safe_operators import safe_divide, safe_sum, safe_substract
from .objects import ECause
from . import mongo_utils
import json
import sys
import os
import asyncio
from datetime import datetime, timezone
from tabulate import tabulate
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
    if not open_trade_amount: open_trade_sum = 0
    else: open_trade_sum = open_trade_amount['sum'] #TODO: This might need to be open_trade_amount[0]['sum']

    balances = pd.DataFrame(end_obs[0]['balances'])
    balances.set_index('asset', inplace=True)
    balance_stat['End Balance'] = safe_sum(balances.loc[config['broker']['quote_currency']]['free'],open_trade_sum,  quant='0.01')
    balance_stat['Absolute Profit'] = safe_substract(balance_stat['End Balance'], balance_stat['Start Balance'], quant='0.01')
    balance_stat['Percentage Profit'] = safe_divide(balance_stat['Absolute Profit']*100, balance_stat['Start Balance'], quant='0.01')

    # Max Drawdown:
    df_observers = pd.DataFrame(list(await mongo_client.do_find('observer',{'type':'quote_asset'})))
    df_observers.set_index(['timestamp'], inplace=True)
    mdd_percentage = (df_observers['total'].max() - df_observers['total'].min() ) / df_observers['total'].max() * 100
    balance_stat['Max Drawdown'] = round(mdd_percentage,2)

    # Paid Fees
    trade_fee_pipe = [
        {"$match":{"result.cause":{"$in": [ECause.CLOSED, ECause.CLOSED_STOP_LIMIT]}}},
        {"$project": {"trade_fee": {"$sum":[ "$result.exit.fee", { "$multiply": [ "$result.enter.fee", "$result.enter.price" ] }]}}},
        {"$group": {"_id": '', "trade_fee_sum": {"$sum": '$trade_fee'}}},
    ]
    if trade_fee_group := await mongo_client.do_aggregate('hist-trades',trade_fee_pipe):
        balance_stat['Paid Fee'] = trade_fee_group[0]['trade_fee_sum']
    else:
        balance_stat['Paid Fee'] = 0
    #TODO:  Add dust amount to statistics

    stats['Balance'] = balance_stat


async def eval_secondary_strategy_stats(stats, config, mongo_client):

    primary_stats = pd.DataFrame(stats['Strategies'].values(), index=stats['Strategies'].keys())
    primary_stats_sum = primary_stats[['Live', 'Closed', 'Closed OCO Stop Limit', 'Enter Expired']].sum(axis=1)
    primary_stats_closed_sum = primary_stats[['Closed', 'Closed OCO Stop Limit']].sum(axis=1)

    primary_stats['Daily Trade Create Rate'] = primary_stats_sum.divide(stats['Total Time in Day']).round(2)
    primary_stats['Trade Enter Rate'] = primary_stats_closed_sum.divide(primary_stats_sum - primary_stats['Live']).round(2)
    primary_stats['Win Rate'] = primary_stats['Win Count'].divide(primary_stats[['Win Count', 'Lose Count']].sum(axis=1)).round(2)
    primary_stats['Average Profit'] = primary_stats['Closed Profit'].divide(primary_stats_closed_sum).round(2)
    stats['Strategies'] = primary_stats.T.to_dict()


async def eval_primary_strategy_stats(stats, config, mongo_client):

    stats['Strategies'] = {}
    for strategy in config['strategy'].keys():
        strategy_stat = {}
        strategy_stat['Pairs'] = config['strategy'][strategy]['pairs']
        strategy_stat['Live'] = int(await mongo_client.count("live-trades", {'strategy':strategy}))
        strategy_stat['Closed'] = int(await mongo_client.count("hist-trades", {'strategy':strategy, 'result.cause':ECause.CLOSED}))
        strategy_stat['Closed OCO Stop Limit'] = int(await mongo_client.count("hist-trades", {'strategy':strategy, 'result.cause':ECause.CLOSED_STOP_LIMIT}))
        strategy_stat['Enter Expired'] = int(await mongo_client.count("hist-trades", {'strategy':strategy, 'result.cause':ECause.ENTER_EXP}))

        # TODO: Calculate and record the profit of ECause.CLOSED, ECause.CLOSED_STOP_LIMIT seperately 
        closed_pipe = [
            {"$match":{"strategy":{"$eq":strategy}, "result.cause":{"$in": [ECause.CLOSED, ECause.CLOSED_STOP_LIMIT]}}},
            {"$group": {"_id": '', "sum": {"$sum": '$result.profit'}}},
        ]
        closed_profit = await mongo_client.do_find("hist-trades", closed_pipe)
        if closed_profit != []: 
            strategy_stat['Closed Profit'] = closed_profit['sum']
        else: 
            strategy_stat['Closed Profit'] = 0

        # Best win
        pipe = [
            {"$sort": {"result.profit": -1} },
            {"$limit" : 1}
        ]
        best_trade = await mongo_utils.do_aggregate_trades(mongo_client, "hist-trades", pipe)
        if best_trade:
            strategy_stat['Best Profit'] = best_trade[0].result.profit

        # Worst lose
        pipe = [
            {"$sort": {"result.profit": 1} },
            {"$limit" : 1}
        ]
        worst_trade = await mongo_utils.do_aggregate_trades(mongo_client, "hist-trades", pipe)
        if worst_trade:
            strategy_stat['Worst Profit'] = worst_trade[0].result.profit

        # Number of Win and Losses
        closed_trades_pipe = [
            {"$match":{"strategy":{"$eq":strategy}, "result.cause":{"$in": [ECause.CLOSED, ECause.CLOSED_STOP_LIMIT]}}}
        ]
        closed_trades = await mongo_utils.do_aggregate_trades(mongo_client, "hist-trades", closed_trades_pipe)

        # Number of Win and Lose
        win_count, lose_count = 0, 0
        for trade in closed_trades:
            if trade.result.profit > 0: win_count+=1
            else: lose_count+=1
        strategy_stat['Win Count'] = win_count
        strategy_stat['Lose Count'] = lose_count


        live_time_list = [trade.result.live_time/(1000*60*60*24) for trade in closed_trades]
        strategy_stat['Min Lifetime'] = min(live_time_list)
        strategy_stat['Max Lifetime'] = max(live_time_list)
        strategy_stat['Average Lifetime'] = round(average(live_time_list),2)


        stats['Strategies'][strategy] = strategy_stat

    strategy_values = pd.DataFrame(stats['Strategies'].values())
    stats['Strategies']['Total'] = strategy_values.sum().to_dict()

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

    start_obs = await mongo_client.get_n_docs('observer', {'type':'balance'}, order=1, n=2) # pymongo.ASCENDING
    end_obs = await mongo_client.get_n_docs('observer', {'type':'balance'}, order=-1) # pymongo.ASCENDING
    start_dt = datetime.fromtimestamp(start_obs[1]['timestamp']/1000, timezone.utc)
    end_dt = datetime.fromtimestamp(end_obs[0]['timestamp']/1000, timezone.utc)
    stats['Total Time in Day'] = safe_divide((end_dt - start_dt).total_seconds(), 60*60*24) # In second

    await eval_balance_stats(stats, config, mongo_client)
    await eval_primary_strategy_stats(stats, config, mongo_client)
    await eval_secondary_strategy_stats(stats, config, mongo_client)


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