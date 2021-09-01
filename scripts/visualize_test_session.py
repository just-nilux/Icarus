import asyncio
from Ikarus import mongo_utils, binance_wrapper
from Ikarus.enums import *
from Ikarus.utils import get_closed_hto, get_enter_expire_hto, get_exit_expire_hto
from binance import AsyncClient
import pandas as pd
import argparse
import fplot as fp
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

    fp.buy_sell(df)

    pass


async def visualize_online():

    client = await AsyncClient.create(api_key=cred_info['Binance']['Test']['PUBLIC-KEY'],
                                      api_secret=cred_info['Binance']['Test']['SECRET-KEY'])
    bwrapper = binance_wrapper.TestBinanceWrapper(client, config)

    start_time = datetime.strptime(config['backtest']['start_time'], "%Y-%m-%d %H:%M:%S")
    start_timestamp = int(datetime.timestamp(start_time))*1000
    end_time = datetime.strptime(config['backtest']['end_time'], "%Y-%m-%d %H:%M:%S")
    end_timestamp = int(datetime.timestamp(end_time))*1000

    # NOTE: Here is the problem, when you hardcode the time_scales in the strategies, it is no more available from the outside
    #       - As a separate tool, there is no way for an outsider to reach that info without doing cumbersome work with strategy manager
    #       - In fact, think about the 'live session visualization', it is not possible to get the time_scale info. Thus it might be a better
    #       idea to expose the time_scales to config file. By doing so, 3rd party components such as visualizer have a change to evaluate
    #       the smallest scale for each pair by checking each strategy pairs and

    # TODO: NEXT: Make the scales configurable just like pairs(considering the discussion above). However it is not planned to be change quite often

    bwrapper.get_historical_klines(start_timestamp, end_timestamp, )
    #df_enter_expire = await get_enter_expire_hto(mongocli)
    #df_exit_expire = await get_exit_expire_hto(mongocli)
    #df_closed = await get_closed_hto(mongocli)

    fp.buy_sell(df, df_enter_expire=df_enter_expire)

    pass


async def main():

    if config['backtest']['online']:
        await visualize_online()
    else:
        await visualize_offline()


if __name__ == '__main__':
    
    # python.exe .\scripts\visualize_test_session.py --filename .\test\data\btcusdt_15m_202005121212_202005191213.csv

    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    mongocli = mongo_utils.MongoClient(config['mongodb']['host'], 
        config['mongodb']['port'], 
        config['tag'],
        clean=False)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

