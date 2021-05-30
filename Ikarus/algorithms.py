import backtrader as bt
import pandas as pd
from backtesting.ws_backtrader.strategies import *
import logging
import statistics as st
import json

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
            

            mean5 = st.mean(time_dict['15m']['trange'][-5:])
            mean20 = st.mean(time_dict['15m']['trange'][-5:])
            if mean5 < mean20:
                self.logger.info(f"{pair}: BUY SIGNAL")
            else:
                self.logger.info(f"{pair}: NO SIGNAL")
            '''  
            for time_scale, stat_obj in time_dict.items():
                # TODO: Create a list of indicator handlers: 
                # [atr_handler(time_scale,stat_objne)]
                # Perform calculation
                pass
            '''
        
        trade_obj = dict()
        for pair, time_obj in analysis_obj.items():
            # Create result
            trade_pair = dict()
            trade_pair["status"] = "open"
            trade_pair["enter"] = {}
            trade_pair["exit"] = {}
            trade_pair["result"] = {}
            trade_obj[pair] = trade_pair

        
        self.logger.debug('sample_algorithm completed')
        await self.dump(trade_obj)
        return trade_obj


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


    async def dump(self, js_obj):
        """
        This functions dumps json objects to files for debug purposes

        Args:
            js_obj (dict): dict to be dumped

        Returns:
            True:
        """    

        self.logger.debug("trade.json file created")
        js_file = open("run-time-objs/trade.json", "w")
        json.dump(js_obj, js_file, indent=4)
        js_file.close()

        return True