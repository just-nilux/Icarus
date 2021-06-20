import backtrader as bt
from backtrader import trade
import pandas as pd
#from backtesting.ws_backtrader.strategies import *
import logging
import statistics as st
import json
from Ikarus.objects import GenericObject, ObjectEncoder

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


    async def sample_algorithm(self, analysis_dict):
        """
        sample_algorithm

        Args:
            analysis_objs (dict): analysis.json
            - analysis objects contains where to buy and and where to sell

        Returns:
            dict: trade.json
        """
        self.logger.debug('sample_algorithm started')

        trade_dict = dict()
        for pair, time_dict in analysis_dict.items():
            
            # Since all parameters are handled in a different way, 
            # there needs to be different handlers for each type of indicator
            # TODO: Create a list of indicator handlers: [atr_handler()]
            

            #trange_mean5 = st.mean(time_dict['15m']['trange'][-5:])
            trange_mean5 = st.mean(time_dict.get(['15m', 'trange'])[-5:])

            #trange_mean20 = st.mean(time_dict['15m']['trange'][-20:])
            trange_mean20 = st.mean(time_dict.get(['15m', 'trange'])[-20:])

            if trange_mean5 < trange_mean20:
                self.logger.info(f"{pair}: BUY SIGNAL")
                trade_obj = GenericObject('trade')
                trade_obj.load('status','created')
                trade_obj.load('status','created')
                trade_dict[pair] = trade_obj

            else:
                self.logger.info(f"{pair}: NO SIGNAL")

            #for time_scale, stat_obj in time_dict.items():
                # TODO: Create a list of indicator handlers: 
                # [atr_handler(time_scale,stat_objne)]
                # Perform calculation
                #pass

        
        self.logger.debug('sample_algorithm completed')
        await self.dump(trade_dict)
        return trade_dict


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

        js_file = open("run-time-objs/trade.json", "w")
        json.dump(js_obj, js_file, indent=4, cls=ObjectEncoder)
        js_file.close()
        self.logger.debug("trade.json file created")

        return True

class BackTestAlgorithm():

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


    async def sample_algorithm(self, analysis_dict, dt_index=None):
        """
        sample_algorithm

        Args:
            analysis_objs (dict): analysis.json
            - analysis objects contains where to buy and and where to sell

        Returns:
            dict: trade.json
        """
        trade_dict = dict()
        for pair, time_dict in analysis_dict.items():
            
            # Since all parameters are handled in a different way, 
            # there needs to be different handlers for each type of indicator
            # TODO: Create a list of indicator handlers: [atr_handler()]
            

            #trange_mean5 = st.mean(time_dict['15m']['trange'][-5:])
            trange_mean5 = st.mean(time_dict.get(['15m', 'trange'])[-5:])

            #trange_mean20 = st.mean(time_dict['15m']['trange'][-20:])
            trange_mean20 = st.mean(time_dict.get(['15m', 'trange'])[-20:])

            if trange_mean5 < trange_mean20:
                self.logger.info(f"{pair}: BUY SIGNAL")
                trade_obj = GenericObject('trade')
                trade_obj.load('status','created')
                trade_obj.load('tradeid',str(dt_index))
                #TODO: give proper values to limitBuy
                trade_obj.load(['enter','limitBuy'],float(trange_mean5))

                trade_dict[pair] = trade_obj

            else:
                self.logger.info(f"{pair}: NO SIGNAL")

            #for time_scale, stat_obj in time_dict.items():
                # TODO: Create a list of indicator handlers: 
                # [atr_handler(time_scale,stat_objne)]
                # Perform calculation
                #pass
        await self.dump(trade_dict)
        return trade_dict


    async def dump(self, js_obj):
        """
        This functions dumps json objects to files for debug purposes

        Args:
            js_obj (dict): dict to be dumped

        Returns:
            True:
        """    

        js_file = open("run-time-objs/trade.json", "w")
        json.dump(js_obj, js_file, indent=4, cls=ObjectEncoder)
        js_file.close()
        self.logger.debug("trade.json file created")

        return True