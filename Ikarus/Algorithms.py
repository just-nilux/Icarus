import backtrader as bt
import datetime
import pandas as pd
from backtesting.ws_backtrader.strategies import *

async def algorithm(periodic_feed):
    print(periodic_feed)
    decision = {'operation': None}

    cerebro = bt.Cerebro(stdstats=False)

    print(periodic_feed)
    kline_columns = ['Opentime', 'Open', 'High', 'Low', 'Close', 'Volume', 'Closetime', 'Quote asset volume', 'Number of trades',
     'Taker by base', 'Taker buy quote', 'Ignore']
    df = pd.DataFrame(periodic_feed, columns=kline_columns)
    df['Opentime'] = pd.to_datetime(df['Opentime'], unit='ms')
    df.set_index(['Opentime'], inplace=True)
    df = df.apply(pd.to_numeric)
    data = bt.feeds.PandasData(dataname=df, timeframe=bt.TimeFrame.Minutes)


    cerebro.adddata(data)
    cerebro.addstrategy(
        OrderExecutionStrategy,
        exectype="Market",
        perc1=1,
        perc2=0.5,
        valid=20,
        smaperiod=15
    )

    cerebro.run()
    cerebro.plot(style='candlestick',barup='green', bardown='red')

    return decision

async def empty_algorithm(periodic_feed):
    decision = {'operation': None}
    return decision
