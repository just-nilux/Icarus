import asyncio
from Ikarus import mongo_utils
import pandas as pd
import argparse
import numpy as np
import fplot as fp

async def add_observer_columns2(df):
    # Read Database to get hist-trades and dump to a DataFrame
    hto_list = await mongocli.do_find('hist-trades',{})
    hto_closed_list = []
    hto_ent_exp_list = []
    for hto in hto_list:
        if hto['result']['cause'] == 'closed':
            hto_dict = {
                "_id": hto['_id'],
                "tradeid": hto['tradeid'],
                "enterTime": hto['enter']['enterTime'],
                "enterPrice": hto['enter']['limitBuy']['price'],
                "exitTime": hto['exit']['exitTime'],
                "exitPrice": hto['exit']['limitSell']['price']
            }
            hto_closed_list.append(hto_dict)
            
        elif hto['result']['cause'] == 'enter_expire':
            hto_dict = {
                "_id": hto['_id'],
                "tradeid": hto['tradeid'],                                # Trade created (>)
                "enterExpire": hto['enter']['expire'],
                "enterPrice": hto['enter']['limitBuy']['price'],
            }
            hto_ent_exp_list.append(hto_dict)
        elif hto['result']['cause'] == 'exit_expire':
            pass
    # TODO: Implement the viusalization for enter expire and exit expire cases
    # TODO: NEXT:

    df_hto = pd.DataFrame(hto_closed_list)
    df_ent_exp_hto = pd.DataFrame(hto_ent_exp_list)

    # Add tradeid, buyLimit and sellLimit to df columns to be visualized
    df['closed_tradeid'] = np.nan           # ts when the enter decision is made
    df['closed_buy'] = np.nan               # buy price
    df['closed_sell'] = np.nan              # sell price

    df['enter_tradeid'] = np.nan            # enter_expire: trade creation time
    df['enter_expire'] = np.nan             # enter_expire: expire time
    df['enter_buy'] = np.nan                # enter_expire: buy price

    df['exit_tradeid'] = np.nan             # exit_expire: trade creation time
    df['exit_expire'] = np.nan              # exit_expire: expire time
    df['exit_buy'] = np.nan                 # exit_expire: buy price
    df['exit_sell'] = np.nan                # exit_expire: sell price

    for idx in df.index:
        print(f"{idx}") 
        if idx in df_hto['tradeid'].values:
            print(f"closed_tradeid {idx}")
            df.loc[idx, 'closed_tradeid'] = int(df_hto[df_hto['tradeid'] == idx]['enterPrice'])
            pass

        if idx in df_hto['enterTime'].values:
            print(f"enterTime {idx}")
            df.loc[idx, 'closed_buy'] = float(df_hto[df_hto['enterTime'] == idx]['enterPrice'])
            pass

        if idx in df_hto['exitTime'].values:
            print(f"exitTime {idx}")
            df.loc[idx, 'closed_sell'] = float(df_hto[df_hto['exitTime'] == idx]['exitPrice'])
            pass

        # Store all expired data in the same row since they all together become a line
        if idx in df_ent_exp_hto['tradeid'].values:
            line = df_ent_exp_hto[df_ent_exp_hto['tradeid'] == idx]
            df.loc[idx, 'enter_tradeid'] = int(line['tradeid'])
            df.loc[idx, 'enter_expire'] = int(line['enterExpire'])
            df.loc[idx, 'enter_buy'] = float(line['enterPrice'])
            pass

        # TODO: NEXT: Implement exit_expire visualization
        
    # Dump df_csv_list[0] to a file for debug purposes
    f= open('out','w'); f.write(df.to_string()); f.close()

    return df


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
    enter_expire_list = df_hto['enter_expire_ti'].to_list()

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

    df = await add_observer_columns2(df)

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

