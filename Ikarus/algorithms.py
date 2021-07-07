import backtrader as bt
from backtrader import trade
import pandas as pd
#from backtesting.ws_backtrader.strategies import *
import logging
import statistics as st
import json
from Ikarus.objects import GenericObject, ObjectEncoder
import bson
class Algorithm():
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


    async def sample_algorithm(self, analysis_dict, lto_dict, df_balance, dt_index=None):
        """
        It requires to feed analysis_dict and lto_dict so that it may decide to:
        - not to enter a new trade if there is already an open trade
        - cancel the trade if an drawdown is detected

        Args:
            analysis_dict (dict): analysis.json
            - analysis objects contains where to buy and and where to sell

            lto_dict (dict): live-trade-objects coming from the [live-trades]

            df_balance (pd.DataFrame): live-trade-objects coming from the [live-trades]

            dt_index (int): timestamp in ms for trade_object identifier
            
        Returns:
            dict: trade.json
        """
        #Initialize trade_dict to be filled
        trade_dict = dict()


        #for pair, time_dict in analysis_dict.items():
        self.logger.info(f"lto_dict.keys(): {set(lto_dict.keys())}")
        self.logger.info(f"analysis_dict.keys(): {set(analysis_dict.keys())}")
        self.logger.info(f"diff.keys(): {(set(analysis_dict.keys()) - set(lto_dict.keys()))}")

        # Only evaluate the analysis dict if there is no open trade belongs to a pair (1 trade at a time for 1 pair)
        # TODO: NEXT: Test the feature
        for pair in (set(analysis_dict.keys()) - set(lto_dict.keys())):
            time_dict = analysis_dict[pair]
            # Since all parameters are handled in a different way, 
            # there needs to be different handlers for each type of indicator
            # TODO: Create a list of indicator handlers: [atr_handler()]

            #trange_mean5 = st.mean(time_dict['15m']['trange'][-5:])
            trange_mean5 = st.mean(time_dict.get(['15m', 'trange'])[-5:])

            #trange_mean20 = st.mean(time_dict['15m']['trange'][-20:])
            trange_mean20 = st.mean(time_dict.get(['15m', 'trange'])[-20:])

            # Make decision to enter or not          
            if trange_mean5 < trange_mean20:
                self.logger.info(f"{pair}: BUY SIGNAL")
                trade_obj = GenericObject('trade')
                trade_obj.load('status','open_enter') # Set initial status to 'open'
                trade_obj.load('tradeid',int(dt_index)) # Set tradeid to timestamp
                #TODO: give proper values to limitBuy


                # Calculate enter/exit prices
                enter_price = min(time_dict.get(['15m', 'low'])[-10:])
                exit_price = max(time_dict.get(['15m', 'high'])[-10:])

                # Calculate enter/exit amount value

                #TODO: Amount calculation is performed to decide how much of the 'free' amount of 
                # the base asset will be used.
                
                #TODO: V2: 'USDT' should not be hardcoded
                free_ref_asset = df_balance.loc['USDT','free']

                # Example: Buy XRP with 100$ in your account
                enter_ref_amount=100
                # TODO: HIGH: Check mininum amount to trade and add this section to here
                if free_ref_asset > 10:
                    if free_ref_asset < enter_ref_amount:
                        enter_ref_amount = free_ref_asset
                else:
                    # TODO: Add error logs and send notification
                    return {}

                # TODO: HIGH: In order to not to face with an issue with dust, exit amount might be "just a bit less" then what it should be
                # Example:
                #   Buy XRP from the price XRPUSDT: 0.66 (Price of 1XRP = 0.66$), use 100$ to make the trade
                #   151,51 = 100$ / 0.66
                enter_quantity = enter_ref_amount / enter_price

                #   Sell the bought XRP from the price 0.70
                #   exit_ref_amount = 151,4 * 0.70 = 105.98
                exit_ref_amount = enter_quantity * exit_price

                # Fill enter module
                enter_module = {
                    "enterTime": "",
                    "limitBuy": {
                        "price": float(enter_price),
                        "quantity": float(enter_quantity),
                        "amount": float(enter_ref_amount),
                        },
                    "expire": bson.Int64(dt_index + 3*15*60*1000)
                    }
                #enter_module["expire"] = dt_index - 3*15*60*1000 # 3 15min block later
                trade_obj.load('enter', enter_module)

                # Fill exit module
                exit_module = {
                    "exitTime": "",
                    "limitSell": {
                        "price": float(exit_price),
                        "quantity": float(enter_quantity),
                        "amount": float(exit_ref_amount),
                        },
                    "expire": bson.Int64(dt_index + 10*15*60*1000)
                    }
                # expire of the exit_module can be calculated after the trade entered
                trade_obj.load('exit', exit_module)

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