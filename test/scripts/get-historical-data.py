from binance import Client, AsyncClient
import asyncio
import pandas as pd
from datetime import datetime, timedelta
import json
import argparse
import pandas as pd
import backtrader as bt
'''
[
  [
    1499040000000,      // Open time
    "0.01634790",       // Open
    "0.80000000",       // High
    "0.01575800",       // Low
    "0.01577100",       // Close
    "148976.11427815",  // Volume
    1499644799999,      // Close time
    "2434.19055334",    // Quote asset volume
    308,                // Number of trades
    "1756.87402397",    // Taker buy base asset volume
    "28.46694368",      // Taker buy quote asset volume
    "17928899.62484339" // Ignore.
  ]
]
'''

credential_file = r'./test_credentials.json'
with open(credential_file, 'r') as cred_file:
    cred_info = json.load(cred_file)

kline_column_names = ["open_time", "open", "high", "low", "close", "volume", "close_time","quote_asset_volume", 
                    "nbum_of_trades", "taker_buy_base_ast_vol", "taker_buy_quote_ast_vol", "ignore"]


async def plot(filename, kline):
    '''
        (Ticks, MicroSeconds, Seconds, Minutes,
     Days, Weeks, Months, Years, NoTimeFrame) = range(1, 10)

    Names = ['', 'Ticks', 'MicroSeconds', 'Seconds', 'Minutes',
             'Days', 'Weeks', 'Months', 'Years', 'NoTimeFrame']
    '''
    # 15m-> 15 m | 1h -> 60m
    timeframe = kline[-1]
    compression = int(kline[:-1])

    if timeframe == 'h':
        timeframe = 'm'
        compression = compression*60

    time_table = {'m':4, 'h':4, 'd':5, 'w':6, 'M':7}
    print(time_table[timeframe],compression)
    cerebro = bt.Cerebro(stdstats=False)
    data = bt.feeds.GenericCSVData(dataname=filename, dtformat=2, compression=compression,
                                   timeframe=time_table[timeframe])
    cerebro.adddata(data)
    cerebro.run()

    cerebro.plot(style='candlestick',barup='green', bardown='red')

async def get_kline(pair, kline, start, end):

    start_dt = datetime.strptime(start, '%Y-%m-%d %H:%M:%S')
    end_dt = datetime.strptime(end, '%Y-%m-%d %H:%M:%S')

    start_ts = int(datetime.timestamp(start_dt)) * 1000
    end_ts = int(datetime.timestamp(end_dt)) * 1000

    client = await AsyncClient.create()
    klines = await client.get_historical_klines(pair, kline, start_ts, end_ts)
    df = pd.DataFrame(klines)
    df.columns = kline_column_names
    #df = df.astype(float)
    df['open_time'] = df['open_time']/1000
    filename = './test/data/{}-{}-{}.csv'.format(pair.lower(), start_dt.strftime("%Y%m%d%H%M"), end_dt.strftime("%Y%m%d%H%M"))
    df.to_csv(filename, index = False, header=True)

    if args.plot:
        await plot(filename,kline)

    await client.close_connection()

if __name__ == '__main__':

    # Instantiate the parser
    # python get-historical-data.py --pair BTCUSDT --kline 1h --start "2020-05-12 12:12:12" --end "2020-05-12 23:13:12" --plot
    parser = argparse.ArgumentParser(description='Optional app description')
    parser.add_argument("--pair", type=str)
    parser.add_argument('--kline', type=str)
    parser.add_argument('--start', type=str,)
    parser.add_argument('--end', type=str)
    parser.add_argument('--plot', action='store_true')
    args = parser.parse_args()

    print(args.plot)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(get_kline(args.pair,args.kline,args.start,args.end))



