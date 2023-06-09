import json
import sys
import os
import asyncio
from binance import AsyncClient
from brokers import backtest_wrapper
import datetime
from itertools import chain
import itertools
import pandas as pd
import json

def write_to_json(config_dict, filename):
    report_folder = os.path.dirname(str(sys.argv[1])) + '/' + config.get('report_folder_name', 'reports')
    f = open(report_folder + '/' + filename,'w')
    json.dump(config_dict, f)
    f.close()


async def main():

    client = await AsyncClient.create(**cred_info['Binance']['Production'])
    bwrapper = backtest_wrapper.BacktestWrapper(client, config)
    start_time = datetime.datetime.strptime(config['backtest']['start_time'], "%Y-%m-%d %H:%M:%S")
    start_timestamp = int(datetime.datetime.timestamp(start_time))*1000
    end_time = datetime.datetime.strptime(config['backtest']['end_time'], "%Y-%m-%d %H:%M:%S")
    end_timestamp = int(datetime.datetime.timestamp(end_time))*1000

    # Create pools for pair-scales
    time_scale_pool = []
    pair_pool = []
    for strategy in config['strategy'].values():
        time_scale_pool.append(strategy['time_scales'])
        pair_pool.append(strategy['pairs'])

    time_scale_pool = list(set(chain(*time_scale_pool)))
    pair_pool = list(set(chain(*pair_pool)))

    meta_data_pool = list(itertools.product(time_scale_pool, pair_pool))

    await bwrapper.obtain_candlesticks(meta_data_pool, start_timestamp, end_timestamp)

    volume_dict_list = []
    for pair, data in bwrapper.downloaded_data.items():
        if not data['1M']['volume'].empty:
            volume_dict_list.append({'pair':pair, 'num_of_trades':int(data['1M']['num_of_trades'].sum()), 'volume':float(data['1M']['volume'].sum())})

    df = pd.DataFrame(volume_dict_list)
    df_sorted_numoftrades = df.sort_values(by=['num_of_trades'], ascending=False).reset_index(drop=True)
    df_sorted_volume = df.sort_values(by=['volume'], ascending=False).reset_index(drop=True)

    pair_dict = {
        'num_of_trades': list(df_sorted_numoftrades.loc[:50]['pair'].values), 
        'volume': list(df_sorted_volume.loc[:50]['pair'].values)
    }
    write_to_json(pair_dict, 'ordered_pairs.json')
    print(json.dumps(pair_dict))


if __name__ == '__main__':
    print(sys.argv)
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

