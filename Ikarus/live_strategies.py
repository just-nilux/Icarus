import logging
import statistics as st
import json
from Ikarus.objects import GenericObject, ObjectEncoder
import bson
import copy
import abc

class StrategyBase(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def __init__(self):
        pass

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'run') and 
                callable(subclass.run) and 
                hasattr(subclass, 'dump_to') and 
                callable(subclass.dump_to) or 
                NotImplemented)

    @abc.abstractmethod
    async def run(self, analysis_dict, lto_dict, df_balance, dt_index=None):
        """Load in the data set"""
        raise NotImplementedError

    abc.abstractmethod
    async def dump_to(self, js_obj: dict):
        js_file = open("run-time-objs/trade.json", "w")
        json.dump(js_obj, js_file, indent=4, cls=ObjectEncoder)
        js_file.close()
        self.logger.debug("trade.json file created")

        return True


class Strategy():
    """
    For the sake of simplicity, it is assumed that all trade pairs contain
        the quote_currency (most probably USDT)
    As a result when you remove the quote_currency from the pair, base_currency is obtained
    """

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
                trade_obj = copy.deepcopy(GenericObject.trade)
                trade_obj['status'] = 'created' # TODO: Fix to open_enter
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


    async def dump(self, js_obj):
        """
        This functions dumps json objects to files for debug purposes

        Args:
            js_obj (dict): dict to be dumped

        Returns:
            True:
        """    

        js_file = open("run-time-objs/trade.json", "w")
        # TODO: remove Object Encoder
        json.dump(js_obj, js_file, indent=4, cls=ObjectEncoder)
        js_file.close()
        self.logger.debug("trade.json file created")

        return True
