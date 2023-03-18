import asyncio

from ..brokers import backtest_wrapper
from ..objects import EState, ECause
from pymongo import ASCENDING, DESCENDING
from .. import mongo_utils
#from scripts import finplot_wrapper as fplot
from . import finplot_wrapper as fplot
from ..utils import get_pair_min_period_mapping
from binance import AsyncClient
import pandas as pd
import json
import sys
from datetime import datetime, timezone
from itertools import chain

async def visualize_online(bwrapper, mongocli, config):

    start_time = datetime.strptime(str(sys.argv[2]), "%Y-%m-%d %H:%M:%S")
    #start_timestamp = int(datetime.timestamp(start_time))*1000
    start_timestamp = int(start_time.replace(tzinfo=timezone.utc).timestamp())*1000
    end_time = datetime.strptime(str(sys.argv[3]), "%Y-%m-%d %H:%M:%S")
    #end_timestamp = int(datetime.timestamp(end_time))*1000
    end_timestamp = int(end_time.replace(tzinfo=timezone.utc).timestamp())*1000

    pair_scale_mapping = await get_pair_min_period_mapping(config)

    df_list = []
    for pair,scale in pair_scale_mapping.items(): 
        df_list.append(bwrapper.get_historical_klines(start_timestamp, end_timestamp, pair, scale))

    df_pair_list = list(await asyncio.gather(*df_list))

    for idx, pair in enumerate(pair_scale_mapping.keys()):
        df_enter_expire = await get_enter_expire_hto(mongocli, {
            'result.cause':EState.ENTER_EXP, 
            'pair':pair, 
            'decision_time': { '$gte': start_timestamp}, 
            'enter.limit.expire': { '$lte': end_timestamp}
            })
        df_exit_expire = await get_exit_expire_hto(config, mongocli, {
            'result.cause':EState.EXIT_EXP, 
            'pair':pair, 
            'decision_time': { '$gte': start_timestamp}, 
            'result.exit.time': { '$lte': end_timestamp}
            })
        df_closed = await get_closed_hto(config, mongocli, {
            'result.cause':EState.CLOSED, 
            'pair':pair, 
            'decision_time': { '$gte': start_timestamp}, 
            'result.exit.time': { '$lte': end_timestamp}
            })

        fplot.buy_sell(df_pair_list[idx], df_closed=df_closed, df_enter_expire=df_enter_expire, df_exit_expire=df_exit_expire)

    pass


async def visualize_dashboard(bwrapper: backtest_wrapper.BacktestWrapper, mongocli, config):

    start_obs = await mongocli.get_n_docs('observer', {'type':'quote_asset'}, order=ASCENDING) # pymongo.ASCENDING
    end_obs = await mongocli.get_n_docs('observer', {'type':'quote_asset'}, order=DESCENDING) # pymongo.ASCENDING

    pair_scale_mapping = await get_pair_min_period_mapping(config)

    dashboard_data_pack = {}
    for pair,scale in pair_scale_mapping.items(): 
        dashboard_data_pack[pair]={}
    
    meta_data_pool = [(v,k) for k,v in pair_scale_mapping.items()]
    await bwrapper.obtain_candlesticks(meta_data_pool, int(start_obs[0]['ts']), int(end_obs[0]['ts']))

    df_pair_list = [bwrapper.downloaded_data[pair][value] for pair, value in pair_scale_mapping.items()]

    # Get trade objects
    for idx, item in enumerate(pair_scale_mapping.items()):
        canceled = await mongo_utils.do_find_trades(mongocli, 'hist-trades', {'result.cause':ECause.ENTER_EXP, 'pair':item[0]})
        closed = await mongo_utils.do_find_trades(mongocli, 'hist-trades', {'result.cause':{'$in':[ECause.MARKET, ECause.STOP_LIMIT, ECause.LIMIT]}, 'pair':item[0]})

        dashboard_data_pack[item[0]]['df'] = df_pair_list[idx]
        dashboard_data_pack[item[0]]['canceled'] = canceled
        dashboard_data_pack[item[0]]['closed'] = closed

    # Get observer objects
    for obs_type, obs_list in config['visualization']['observers'].items():
        df_observers = pd.DataFrame(list(await mongocli.do_find('observer',{'type':obs_type})))
        df_obs_data = pd.DataFrame(df_observers['data'].to_list())
        df_obs_data.set_index(df_observers['ts'])
        df_obs_data = df_obs_data[obs_list]
        dashboard_data_pack[obs_type] = df_obs_data

    fplot.buy_sell_dashboard(dashboard_data_pack=dashboard_data_pack, 
                             title=f"Visualizing Time Frame: {str(datetime.fromtimestamp(int(start_obs[0]['ts']/1000)))} - {str(datetime.fromtimestamp(int(end_obs[0]['ts']/1000)))}")


async def main():
    client = await AsyncClient.create(**cred_info['Binance']['Production'])
    bwrapper = backtest_wrapper.BacktestWrapper(client, config)

    config['mongodb']['clean'] = False
    mongo_client = mongo_utils.MongoClient(**config['mongodb'])
    await visualize_dashboard(bwrapper, mongo_client, config)
    #await bwrapper.client.close_connection()


if __name__ == '__main__':

    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())