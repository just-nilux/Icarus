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
from datetime import datetime

async def visualize_offline():
    # Read Database to get hist-trades and dump to a DataFrame

    df = pd.read_csv(config['files'][0])
    df = df.set_index(['open_time'])

    #df_enter_expire = await get_enter_expire_hto(mongocli)
    #df_exit_expire = await get_exit_expire_hto(mongocli)
    #df_closed = await get_closed_hto(mongocli)

    fplot.buy_sell(df)

    pass


async def visualize_online(bwrapper, mongocli, config):

    start_time = datetime.strptime(config['backtest']['start_time'], "%Y-%m-%d %H:%M:%S")
    start_timestamp = int(datetime.timestamp(start_time))*1000
    end_time = datetime.strptime(config['backtest']['end_time'], "%Y-%m-%d %H:%M:%S")
    end_timestamp = int(datetime.timestamp(end_time))*1000

    pair_scale_mapping = await get_pair_min_period_mapping(config)

    df_list = []
    for pair,scale in pair_scale_mapping.items(): 
        df_list.append(bwrapper.get_historical_klines(start_timestamp, end_timestamp, pair, scale))

    df_pair_list = list(await asyncio.gather(*df_list))

    for idx, pair in enumerate(pair_scale_mapping.keys()):
        df_enter_expire = await get_enter_expire_hto(mongocli,{'result.cause':STAT_ENTER_EXP, 'pair':pair})
        df_exit_expire = await get_exit_expire_hto(mongocli, {'result.cause':STAT_EXIT_EXP, 'pair':pair})
        df_closed = await get_closed_hto(mongocli, {'result.cause':STAT_CLOSED, 'pair':pair})

        fplot.buy_sell(df_pair_list[idx], df_closed=df_closed)

    pass


async def main():

    if config['backtest']['online']:
        client = await AsyncClient.create(api_key=cred_info['Binance']['Test']['PUBLIC-KEY'],
                                        api_secret=cred_info['Binance']['Test']['SECRET-KEY'])
        bwrapper = binance_wrapper.TestBinanceWrapper(client, config)
        mongocli = mongo_utils.MongoClient(config['mongodb']['host'], 
            config['mongodb']['port'], 
            config['tag'],
            clean=False)
        await visualize_online(bwrapper, mongocli, config)
    else:
        await visualize_offline()


if __name__ == '__main__':
    

    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

