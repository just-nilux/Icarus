import asyncio
from Ikarus import broker, mongo_utils
#from scripts import finplot_wrapper as fplot
import finplot_wrapper as fplot
from Ikarus.enums import *
from Ikarus.utils import get_closed_hto, get_enter_expire_hto, get_exit_expire_hto, get_pair_min_period_mapping
from Ikarus import analyzers
from binance import AsyncClient
import pandas as pd
import argparse
import json
import sys
from datetime import datetime
import itertools

async def main():


    client = await AsyncClient.create(api_key=cred_info['Binance']['Test']['PUBLIC-KEY'],
                                    api_secret=cred_info['Binance']['Test']['SECRET-KEY'])
    bwrapper = broker.TestBinanceWrapper(client, config)

    meta_data_pool = []
    for name, strategy_config in config['strategy'].items():
        meta_do = list(itertools.product(strategy_config['time_scales'], strategy_config['pairs']))
        meta_data_pool.append(meta_do)
    meta_data_pool = set(itertools.chain(*meta_data_pool))
    # Evaluate start and end times
    session_start_time = datetime.strptime(config['backtest']['start_time'], "%Y-%m-%d %H:%M:%S")
    session_start_timestamp = int(datetime.timestamp(session_start_time)) # UTC
    session_end_time = datetime.strptime(config['backtest']['end_time'], "%Y-%m-%d %H:%M:%S")
    session_end_timestamp = int(datetime.timestamp(session_end_time))
    await bwrapper.download_all_data(meta_data_pool, session_start_timestamp*1000, session_end_timestamp*1000)
    #bwrapper.downloaded_data
    fplot.buy_sell_dashboard(dashboard_data_pack=dashboard_data_pack, title=f'Visualizing Time Frame: {config["backtest"]["start_time"]} - {config["backtest"]["end_time"]}')
    pass


if __name__ == '__main__':
    

    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

