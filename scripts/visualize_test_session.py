import asyncio
from Ikarus import mongo_utils
import pandas as pd
import argparse
import numpy as np
import fplot as fp

async def add_observer_columns(df):
    # Read Database to get hist-trades and dump to a DataFrame
    hto_closed_list = await mongocli.do_find('hist-trades',{"result.cause":"closed"})
    hto_list = []
    for hto in hto_closed_list:
        hto_dict = {
            "_id": hto['_id'],
            "tradeid": hto['tradeid'],
            "enterTime": hto['enter']['enterTime'],
            "enterPrice": hto['enter']['limitBuy']['price'],
            "exitTime": hto['exit']['exitTime'],
            "exitPrice": hto['exit']['limitSell']['price']
        }
        hto_list.append(hto_dict)
    df_hto = pd.DataFrame(hto_list)

    # Add tradeid, buyLimit and sellLimit to df columns to be visualized
    df['tradeid'] = np.nan          # ts when the enter decision is made
    df['buy'] = np.nan              # buy price
    df['sell'] = np.nan             # sell price

    tradid_list = df_hto['tradeid'].to_list()
    enterTime_list = df_hto['enterTime'].to_list()
    exitTime_list = df_hto['exitTime'].to_list()

    for idx in df.index:
        print(f"{idx}") 
        if idx in tradid_list:
            print(f"tradeid {idx}")
            df.loc[idx, 'tradeid'] = float(df_hto[df_hto['tradeid'] == idx]['enterPrice'])
            pass

        if idx in enterTime_list:
            print(f"enterTime {idx}")
            df.loc[idx, 'buy'] = float(df_hto[df_hto['enterTime'] == idx]['enterPrice'])
            pass

        if idx in exitTime_list:
            print(f"exitTime {idx}")
            df.loc[idx, 'sell'] = float(df_hto[df_hto['exitTime'] == idx]['exitPrice'])
            pass

    # Dump df_csv_list[0] to a file for debug purposes
    f= open('out','w'); f.write(df.to_string()); f.close()

    return df


async def visualize_db():
    # Read Database to get hist-trades and dump to a DataFrame

    df = pd.read_csv(args.filename)
    df = df.set_index(['open_time'])

    df = await add_observer_columns(df)

    fp.buy_sell(df)

    pass


if __name__ == '__main__':
    
    # python.exe .\scripts\visualize_test_session.py --filename .\test\data\btcusdt_15m_202005121212_202005191213.csv

    parser = argparse.ArgumentParser(description='Optional app description')
    parser.add_argument('--host', type=str, default='localhost')
    parser.add_argument('--port', type=str, default=27017)
    parser.add_argument('--db', type=str, default='test-bot')
    parser.add_argument('--filename', type=str, default=r'.\\test\\data\\btcusdt_15m_202005121212_202005191213.csv')
    args = parser.parse_args()
    print(args.host, args.port, args.db)
    mongocli = mongo_utils.MongoClient(args.host, args.port, args.db, clean=False)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(visualize_db())

