import asyncio
from Ikarus import mongo_utils
from Ikarus.enums import *
import pandas as pd
import argparse
import fplot as fp

async def get_enter_expire(df):
    # Read Database to get hist-trades and dump to a DataFrame
    hto_list = await mongocli.do_find('hist-trades',{'result.cause':STAT_ENTER_EXP})
    hto_ent_exp_list = []
    for hto in hto_list:
        # NOTE: HIGH: We dont know it the exit type is limit or not
        hto_dict = {
            "_id": hto['_id'],
            "tradeid": hto['tradeid'],
            "enterExpire": hto['enter'][TYPE_LIMIT]['expire'],
            "enterPrice": hto['enter'][TYPE_LIMIT]['price'],
        }
        hto_ent_exp_list.append(hto_dict)

    df = pd.DataFrame(hto_ent_exp_list)
    return df


async def get_closed(df):
    # Read Database to get hist-trades and dump to a DataFrame
    hto_list = await mongocli.do_find('hist-trades',{'result.cause':STAT_CLOSED})
    hto_closed = []
    for hto in hto_list:
        if TYPE_OCO in hto['exit'].keys():  plannedExitType = TYPE_OCO; plannedPriceName = 'limitPrice'
        elif TYPE_LIMIT in hto['exit'].keys(): plannedExitType = TYPE_LIMIT; plannedPriceName = 'price'

        hto_dict = {
            "_id": hto['_id'],
            "tradeid": hto['tradeid'],
            "enterTime": hto['result']['enter']['time'],
            "enterPrice": hto['enter'][TYPE_LIMIT]['price'],
            "exitTime": hto['result']['exit']['time'],
            "exitPrice": hto['exit'][plannedExitType][plannedPriceName],
            "sellPrice": hto['result']['exit']['price']
        }
        hto_closed.append(hto_dict)


    df = pd.DataFrame(hto_closed)

    return df


async def get_exit_expire(df):
    # Read Database to get hist-trades and dump to a DataFrame
    
    hto_list = await mongocli.do_find('hist-trades',{'result.cause':STAT_EXIT_EXP})
    hto_closed_list = []
    for hto in hto_list:
        if TYPE_OCO in hto['exit'].keys():  plannedExitType = TYPE_OCO; plannedPriceName = 'limitPrice'
        elif TYPE_LIMIT in hto['exit'].keys(): plannedExitType = TYPE_LIMIT; plannedPriceName = 'price'

        hto_dict = {
            "_id": hto['_id'],
            "tradeid": hto['tradeid'],
            "enterTime": hto['result']['enter']['time'],
            "enterPrice": hto['enter'][TYPE_LIMIT]['price'],
            "exitPrice": hto['exit'][plannedExitType][plannedPriceName],
            "sellPrice": hto['result']['exit']['price'],
            "exitExpire": hto['exit'][plannedExitType]['expire']
        }
        hto_closed_list.append(hto_dict)
    df = pd.DataFrame(hto_closed_list)

    return df


async def visualize_db():
    # Read Database to get hist-trades and dump to a DataFrame

    df = pd.read_csv(args.filename)
    df = df.set_index(['open_time'])

    #df = await add_observer_columns(df)
    df_enter_expire = await get_enter_expire(df)
    df_exit_expire = await get_exit_expire(df)
    df_closed = await get_closed(df)

    fp.buy_sell(df, df_closed, df_enter_expire, df_exit_expire)

    pass


if __name__ == '__main__':
    
    # TODO: In order to visualize test session:
    #       1. Get the trade data from db
    #       2. Get the candle data from either file or api. (provide option)

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

