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

    for idx, item in enumerate(pair_scale_mapping.items()):
        df_enter_expire = await get_enter_expire_hto(mongocli,{'result.cause':STAT_ENTER_EXP, 'pair':item[0]})
        df_exit_expire = await get_exit_expire_hto(config, mongocli, {'result.cause':STAT_EXIT_EXP, 'pair':item[0]})
        df_closed = await get_closed_hto(config, mongocli, {'result.cause':STAT_CLOSED, 'pair':item[0]})

        fplot.buy_sell(df_pair_list[idx], df_closed=df_closed, df_enter_expire=df_enter_expire, df_exit_expire=df_exit_expire, title=f'{item[0]} - {item[1]}')

    pass


async def visualize_dashboard(bwrapper, mongocli, config):

    start_time = datetime.strptime(config['backtest']['start_time'], "%Y-%m-%d %H:%M:%S")
    start_timestamp = int(datetime.timestamp(start_time))*1000
    end_time = datetime.strptime(config['backtest']['end_time'], "%Y-%m-%d %H:%M:%S")
    end_timestamp = int(datetime.timestamp(end_time))*1000

    pair_scale_mapping = await get_pair_min_period_mapping(config)

    df_list, dashboard_data_pack = [], {}
    for pair,scale in pair_scale_mapping.items(): 
        df_list.append(bwrapper.get_historical_klines(start_timestamp, end_timestamp, pair, scale))
        dashboard_data_pack[pair]={}
    
    df_pair_list = list(await asyncio.gather(*df_list))

    for idx, item in enumerate(pair_scale_mapping.items()):
        # TODO: Optimize and clean the code: e.g. assign call outputs directly to the dataframes
        df_enter_expire = await get_enter_expire_hto(mongocli,{'result.cause':STAT_ENTER_EXP, 'pair':item[0]})
        df_exit_expire = await get_exit_expire_hto(config, mongocli, {'result.cause':STAT_EXIT_EXP, 'pair':item[0]})
        df_closed = await get_closed_hto(config, mongocli, {'result.cause':STAT_CLOSED, 'pair':item[0]})

        #fplot.buy_sell_dashboard(df_pair_list[idx], df_closed=df_closed, df_enter_expire=df_enter_expire, df_exit_expire=df_exit_expire, title=f'{item[0]} - {item[1]}')
        dashboard_data_pack[item[0]]['df'] = df_pair_list[idx]
        dashboard_data_pack[item[0]]['df_enter_expire'] = df_enter_expire
        dashboard_data_pack[item[0]]['df_exit_expire'] = df_exit_expire
        dashboard_data_pack[item[0]]['df_closed'] = df_closed

    # Get observer objects
    for obs_type, obs_list in config['visualization']['observers'].items():
        df_observers = pd.DataFrame(list(await mongocli.do_find('observer',{'type':obs_type})))
        df_observers.set_index(['timestamp'], inplace=True)
        df_observers = df_observers[obs_list]
        dashboard_data_pack[obs_type] = df_observers

    fplot.buy_sell_dashboard(dashboard_data_pack=dashboard_data_pack, title=f'Visualizing Time Frame: {config["backtest"]["start_time"]} - {config["backtest"]["end_time"]}')

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
        await visualize_dashboard(bwrapper, mongocli, config)
    else:
        await visualize_offline()


if __name__ == '__main__':
    

    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

