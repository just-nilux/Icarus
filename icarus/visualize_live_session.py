import asyncio
from sshtunnel import SSHTunnelForwarder
from brokers import backtest_wrapper
from objects import EState, ECause
from pymongo import ASCENDING, DESCENDING
import mongo_utils
#from scripts import finplot_wrapper as fplot
from visualization import finplot_wrapper as fplot
from utils import get_pair_min_period_mapping
from binance import AsyncClient
import pandas as pd
import json
import sys
from datetime import datetime

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
        
    if 'ssh_tunnel' in config:
        #tunnel_server = SSHTunnelForwarder(**config['ssh_tunnel'])
        tunnel_server = SSHTunnelForwarder(
            tuple(config['ssh_tunnel']['ssh_address_or_host']),
            ssh_username=config['ssh_tunnel']['ssh_username'],
            ssh_pkey=config['ssh_tunnel']['ssh_pkey'],
            remote_bind_address=tuple(config['ssh_tunnel']['remote_bind_address']),
            local_bind_address=tuple(config['ssh_tunnel']['local_bind_address'])
        )
        tunnel_server.start()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    if 'ssh_tunnel' in config:
        tunnel_server.stop()