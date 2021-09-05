import asyncio
from Ikarus import mongo_utils, binance_wrapper
#from scripts import finplot_wrapper as fplot
import finplot_wrapper as fplot
from Ikarus.enums import *
from Ikarus.utils import get_closed_hto, get_enter_expire_hto, get_exit_expire_hto, get_pair_min_period_mapping
from binance import AsyncClient
import pandas as pd
import argparse
import json
import sys
from datetime import datetime, timezone

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
            'result.cause':STAT_ENTER_EXP, 
            'pair':pair, 
            'decision_time': { '$gte': start_timestamp}, 
            'enter.limit.expire': { '$lte': end_timestamp}
            })
        df_exit_expire = await get_exit_expire_hto(mongocli, {
            'result.cause':STAT_EXIT_EXP, 
            'pair':pair, 
            'decision_time': { '$gte': start_timestamp}, 
            'result.exit.time': { '$lte': end_timestamp}
            })
        df_closed = await get_closed_hto(mongocli, {
            'result.cause':STAT_CLOSED, 
            'pair':pair, 
            'decision_time': { '$gte': start_timestamp}, 
            'result.exit.time': { '$lte': end_timestamp}
            })

        fplot.buy_sell(df_pair_list[idx], df_closed=df_closed, df_enter_expire=df_enter_expire, df_exit_expire=df_exit_expire)

    pass


async def main():


    client = await AsyncClient.create(api_key=cred_info['Binance']['Test']['PUBLIC-KEY'],
                                    api_secret=cred_info['Binance']['Test']['SECRET-KEY'])
    bwrapper = binance_wrapper.TestBinanceWrapper(client, config)
    mongocli = mongo_utils.MongoClient(config['mongodb']['host'], 
        config['mongodb']['port'], 
        config['tag'],
        clean=False)

    start_time = datetime.strptime(str(sys.argv[2]), "%Y-%m-%d %H:%M:%S")
    start_timestamp = int(datetime.timestamp(start_time))*1000
    end_time = datetime.strptime(str(sys.argv[3]), "%Y-%m-%d %H:%M:%S")
    end_timestamp = int(datetime.timestamp(end_time))*1000

    await visualize_online(bwrapper, mongocli, config)
    await bwrapper.client.close_connection()


if __name__ == '__main__':
    

    if len(sys.argv) < 4:
        print("Error")
        exit()

    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())