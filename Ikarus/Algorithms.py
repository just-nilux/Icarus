import backtrader as bt
import datetime
import pandas as pd
from backtesting.ws_backtrader.strategies import *
import logging
from Ikarus import Analyzer, Plot

# Configure logger for the current file
logger = logging.getLogger('app.{}'.format(__name__))

async def algorithm(pairlist, periodic_feed):
    logger.debug("func algorithm started")

    logger.debug("Periodic feed[0]: {}".format(periodic_feed))
    decision = {'operation': None}

    cerebro = bt.Cerebro(stdstats=False)

    print(periodic_feed)
    kline_columns = ['Opentime', 'Open', 'High', 'Low', 'Close', 'Volume', 'Closetime', 'Quote asset volume',
                     'Number of trades', 'Taker by base', 'Taker buy quote', 'Ignore']
    df = pd.DataFrame(periodic_feed, columns=kline_columns)
    df['Opentime'] = pd.to_datetime(df['Opentime'], unit='ms')
    df.set_index(['Opentime'], inplace=True)
    df = df.apply(pd.to_numeric)

    logger.debug(str(df))

    data = bt.feeds.PandasData(dataname=df, timeframe=bt.TimeFrame.Minutes)


    cerebro.adddata(data)
    '''
    cerebro.addstrategy(
        OrderExecutionStrategy,
        exectype="Market",
        perc1=1,
        perc2=0.5,
        valid=20,
        smaperiod=15
    )
    '''
    cerebro.addstrategy(
        RSIStrategy
    )
    cerebro.run()
    cerebro.plot(style='candlestick',barup='green', bardown='red')
    logger.debug("func algorithm ended")
    return decision

async def empty_algorithm(pairlist, periodic_feed):
    logger.debug('empty_algorithm started')
    decision = {'operation': None}
    logger.debug('empty_algorithm completed')
    return decision

async def algo_analysis(pairlist, periodic_feed):
    logger.debug('empty_algorithm started')
    decision = {'operation': None}
    print(periodic_feed)
    #atr = await Analyzer.get_atr(periodic_feed)
    logger.debug('empty_algorithm completed')
    #await Plot.multi_plot(periodic_feed,atr)
    return decision

async def default_algorithm(analysis_objs):
    '''
    For the sake of performance, analysis objs can be saved to not to calculate redundant parts that has been
    perivously calculated. For Example calculating monthly or weekly sections should only be performed once in a month
    adn week.

    Return
        None: No action
        trade_objs
    '''
    logger.debug('default_algorithm started')
    trade_objs = []
    for ao in analysis_objs:
        trade_obj = dict()
        trade_obj["status"] = "open"
        trade_obj["enter"] = {}
        trade_obj["exit"] = {}
        trade_obj["result"] = {}
        trade_objs.append(trade_obj)
    logger.debug('default_algorithm completed')

    return trade_objs