import asyncio
from ..objects import EState
from .. import broker, mongo_utils
#from scripts import finplot_wrapper as fplot
from . import finplot_wrapper as fplot
 
from ..utils import get_pair_min_period_mapping
from binance import AsyncClient
import pandas as pd
import json
import sys
from datetime import datetime


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
        enter_expired_trades = await mongo_utils.query_trades(mongocli, 'hist-trades', {'result.cause':EState.ENTER_EXP, 'pair':item[0]})
        exit_expired_trades = await mongo_utils.query_trades(mongocli, 'hist-trades', {'result.cause':EState.EXIT_EXP, 'pair':item[0]})
        closed_trades = await mongo_utils.query_trades(mongocli, 'hist-trades', {'result.cause':EState.CLOSED, 'pair':item[0]})

        dashboard_data_pack[item[0]]['df'] = df_pair_list[idx]
        dashboard_data_pack[item[0]]['enter_expired_trades'] = enter_expired_trades
        dashboard_data_pack[item[0]]['exit_expired_trades'] = exit_expired_trades
        dashboard_data_pack[item[0]]['closed_trades'] = closed_trades

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
        bwrapper = broker.TestBinanceWrapper(client, config)
        mongocli = mongo_utils.MongoClient(config['mongodb']['host'], 
            config['mongodb']['port'], 
            config['tag'],
            clean=False)
        await visualize_dashboard(bwrapper, mongocli, config)


if __name__ == '__main__':
    

    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    if len(sys.argv) >=3:
        config['credential_file'] = str(sys.argv[2])

    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

