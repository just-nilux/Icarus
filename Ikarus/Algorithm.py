import backtrader as bt
import pandas as pd
from backtesting.ws_backtrader.strategies import *
import logging


class Algorithm():

    def __init__(self):
        self.logger = logging.getLogger('app.{}'.format(__name__))

        return


    async def default_algorithm(self, analysis_objs):
        """This function uses backtrader strategy class

        Args:
            analysis_objs (list): list of analysis.json

        Returns:
            list: list of trade.json
        """
        self.logger.debug('default_algorithm started')
        trade_objs = []
        for ao in analysis_objs:
            trade_obj = dict()
            trade_obj["status"] = "open"
            trade_obj["enter"] = {}
            trade_obj["exit"] = {}
            trade_obj["result"] = {}
            trade_objs.append(trade_obj)
        self.logger.debug('default_algorithm completed')

        return trade_objs


    async def sample_algorithm(self, analysis_obj):
        """
        sample_algorithm

        Args:
            analysis_objs (dict): analysis.json

        Returns:
            dict: trade.json
        """
        self.logger.debug('sample_algorithm started')

        for pair, time_dict in analysis_obj.items():
            
            # Since all parameters are handled in a different way, 
            # there needs to be different handlers for each type of indicator
            # TODO: Create a list of indicator handlers: [atr_handler()]
            
            for time_scale, stat_obj in time_dict.items():
                # TODO: Create a list of indicator handlers: 
                # [atr_handler(time_scale,stat_objne)]

                # Perform calculation
                pass

        trade_objs = []
        for pair, time_obj in analysis_obj:
            # Create result
            trade_obj = dict()
            trade_obj["status"] = "open"
            trade_obj["enter"] = {}
            trade_obj["exit"] = {}
            trade_obj["result"] = {}
            trade_objs.append(trade_obj)
        self.logger.debug('sample_algorithm completed')

        return trade_objs


    async def algorithm(self, pairlist, periodic_feed):
        self.logger.debug("func algorithm started")

        self.logger.debug("Periodic feed[0]: {}".format(periodic_feed))
        decision = {'operation': None}

        cerebro = bt.Cerebro(stdstats=False)

        print(periodic_feed)
        kline_columns = ['Opentime', 'Open', 'High', 'Low', 'Close', 'Volume', 'Closetime', 'Quote asset volume',
                        'Number of trades', 'Taker by base', 'Taker buy quote', 'Ignore']
        df = pd.DataFrame(periodic_feed, columns=kline_columns)
        df['Opentime'] = pd.to_datetime(df['Opentime'], unit='ms')
        df.set_index(['Opentime'], inplace=True)
        df = df.apply(pd.to_numeric)

        self.logger.debug(str(df))

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
        self.logger.debug("func algorithm ended")
        return decision
