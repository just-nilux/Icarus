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

class OCOBackTest(StrategyBase):

    def __init__(self,_config):
        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.config = _config
        '''
        self.config = {
            "enter": "limit",
            "exit": "oco",
            "action_mapping": {
                "enter_expire": "cancel",
                "exit_expire": "market_exit"
            },
            "max_lto": 1
        }
        '''
        return

    async def _postpone(self, lto, phase, planned_phase_type, expire_time):
        lto['action'] = 'postpone'
        lto[phase][planned_phase_type]['expire'] = expire_time
        return lto


    async def _do_market_exit(self, lto, planned_exit_type):

        lto['action'] = 'market_exit'
        lto['exit']['market'] = {
            'amount': lto['exit'][planned_exit_type]['amount'],
            'quantity': lto['exit'][planned_exit_type]['quantity']
        }
        return lto


    async def _create_enter_module(self, enter_price, enter_quantity, enter_ref_amount, expire_time):

        if self.config['enter']['type'] == 'limit':
            enter_module = {
                "limit": {
                    "price": float(enter_price),
                    "quantity": float(enter_quantity),
                    "amount": float(enter_ref_amount),
                    "expire": expire_time
                    },
                }
        elif self.config['enter']['type'] == 'market':
            # TODO: Create 'market' orders to enter
            pass
        else: pass # Internal Error
        return enter_module


    async def _create_exit_module(self, enter_price, enter_quantity, exit_price, exit_ref_amount, expire_time):

        if self.config['exit']['type'] == 'oco':
            exit_module = {
                "oco": {
                    "limitPrice": float(exit_price),
                    "stopPrice": float(enter_price)*0.995,           # Auto-execute stop loss if the amount go below %0.05
                    "stopLimitPrice": float(enter_price)*0.994,      # Lose max %0.06 of the amount
                    "quantity": float(enter_quantity),
                    "amount": float(exit_ref_amount),
                    "expire": expire_time
                }
            }
        elif self.config['exit']['type'] == 'limit':
            exit_module = {
                "limit": {
                    "price": float(exit_price),
                    "quantity": float(enter_quantity),
                    "amount": float(exit_ref_amount),
                    "expire": expire_time
                    },
                }
        elif self.config['exit']['type'] == 'market':
            pass
        else: pass # Internal Error
        return exit_module


    async def run(self, analysis_dict, lto_dict, df_balance, dt_index=None):
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

        # TODO: Update the iteration logic based on the trade id not the pair
        # TODO: Consider the fact that an pair have multiple to's going on. Max number can be restricted
        for pair in analysis_dict.keys():

            # Decide whether or not to make decision and how to make a decision

            # Check if there is already an lto for a specific pair
            if pair in lto_dict.keys():
                # NOTE: If a pair contains multiple to then there should be another level of iteration as well
                if lto_dict[pair]['status'] == 'enter_expire':
                    lto_dict[pair]['action'] = 'cancel'
                    lto_dict[pair]['result']['cause'] = 'enter_expire'

                elif lto_dict[pair]['status'] == 'exit_expire':                
                    # Do market exit
                    if 'limit' in lto_dict[pair]['exit'].keys(): exit_type = 'limit'
                    elif 'oco' in lto_dict[pair]['exit'].keys(): exit_type = 'oco'
                    else: pass #Internal Error

                    lto_dict[pair] = await self._do_market_exit(lto_dict[pair], exit_type)
                    # NOTE: In order to use the action postpone, history should be used. Otherwise it is not known if the trade is already postponed before
                    # Postpone the expiration
                    #lto_dict[pair] = await self._postpone(lto_dict[pair],'exit', exit_type, bson.Int64(dt_index + 2*15*60*1000))

                elif lto_dict[pair]['status'] == 'waiting_exit':
                    # LTO is entered succesfully, so exit order should be executed
                    # TODO: expire of the exit_module can be calculated after the trade entered

                    lto_dict[pair]['action'] = 'execute_exit'
                    continue

                elif lto_dict[pair]['status'] != 'closed':
                    # If the status is not closed, just skip the iteration. otherwise go on to make a decision
                    # NOTE: This logic contains the status: 'open_exit', 'open_enter', 'partially_closed_enter', 'partially_closed_exit'
                    continue
            else:
                # Make a brand new decision
                pass

            time_dict = analysis_dict[pair]
            # Since all parameters are handled in a different way, 
            # there needs to be different handlers for each type of indicator
            # TODO: Create a list of indicator handlers: [atr_handler()]

            trange_mean5 = st.mean(time_dict['15m']['trange'][-5:])
            trange_mean20 = st.mean(time_dict['15m']['trange'][-20:])

            # Make decision to enter or not
            if trange_mean5 < trange_mean20:
                self.logger.info(f"{pair}: BUY SIGNAL")
                trade_obj = copy.deepcopy(GenericObject.trade)
                trade_obj['status'] = 'open_enter'
                trade_obj['history'].append(trade_obj['status'])
                trade_obj['tradeid'] = int(dt_index) # Set tradeid to timestamp which is the open time of the current kline not the last closed kline
                #TODO: give proper values to limit


                # Calculate enter/exit prices
                enter_price = min(time_dict['15m']['low'][-10:])
                exit_price = max(time_dict['15m']['high'][-10:])

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
                trade_obj['enter'] = await self._create_enter_module(enter_price, enter_quantity, enter_ref_amount, bson.Int64(dt_index + 2*15*60*1000))

                # Fill exit module
                trade_obj['exit'] = await self._create_exit_module(enter_price, enter_quantity, exit_price, exit_ref_amount, bson.Int64(dt_index + 9*15*60*1000))

                trade_dict[pair] = trade_obj

            else:
                self.logger.info(f"{pair}: NO SIGNAL")

        await self.dump_to(trade_dict)
        return trade_dict

    async def dump_to(self, js_obj: dict):
        js_file = open("run-time-objs/trade.json", "w")
        json.dump(js_obj, js_file, indent=4, cls=ObjectEncoder)
        js_file.close()
        self.logger.debug("trade.json file created")

        return True


class LimitBackTest(StrategyBase):

    def __init__(self):
        self.logger = logging.getLogger('app.{}'.format(__name__))
        return

    async def run(self, analysis_dict, lto_dict, df_balance, dt_index=None):
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

        # TODO: Update the iteration logic based on the trade id not the pair
        # TODO: Consider the fact that an pair have multiple to's going on. Max number can be restricted
        for pair in analysis_dict.keys():

            # Decide whether or not to make decision and how to make a decision

            # Check if there is already an lto for a specific pair
            if pair in lto_dict.keys():
                # NOTE: If a pair contains multiple to then there should be another level of iteration as well
                if lto_dict[pair]['status'] == 'enter_expire':
                    lto_dict[pair]['action'] = 'cancel'
                    lto_dict[pair]['result']['cause'] = 'enter_expire'

                elif lto_dict[pair]['status'] == 'exit_expire':
                    # Do market exit               
                    if 'limit' in lto_dict[pair]['exit'].keys(): exit_type = 'limit'
                    elif 'oco' in lto_dict[pair]['exit'].keys(): exit_type = 'oco'
                    else: pass #Internal Error

                    lto_dict[pair]['action'] = 'market_exit'
                    lto_dict[pair]['exit']['market'] = {
                        'amount': lto_dict[pair]['exit'][exit_type]['amount'],
                        'quantity': lto_dict[pair]['exit'][exit_type]['quantity']
                    }
                    # NOTE: Since this trade will be cancelled before the execution of new trade, 
                    #       we can decide to whether or not to enter, 
                    #       instead of continue and not to enter
                    #continue

                elif lto_dict[pair]['status'] == 'waiting_exit':
                    # LTO is entered succesfully, so exit order should be executed
                    lto_dict[pair]['action'] = 'execute_exit'
                    continue

                elif lto_dict[pair]['status'] != 'closed':
                    # If the status is not closed, just skip the iteration. otherwise go on to make a decision
                    # NOTE: This logic contains the status: 'open_exit', 'open_enter', 'partially_closed_enter', 'partially_closed_exit'
                    continue
            else:
                # Make a brand new decision
                pass

            time_dict = analysis_dict[pair]
            # Since all parameters are handled in a different way, 
            # there needs to be different handlers for each type of indicator
            # TODO: Create a list of indicator handlers: [atr_handler()]

            trange_mean5 = st.mean(time_dict['15m']['trange'][-5:])
            trange_mean20 = st.mean(time_dict['15m']['trange'][-20:])

            # Make decision to enter or not
            if trange_mean5 < trange_mean20:
                self.logger.info(f"{pair}: BUY SIGNAL")
                trade_obj = copy.deepcopy(GenericObject.trade)
                trade_obj['status'] = 'open_enter'
                lto_dict[pair]['history'].append(lto_dict[pair]['status'])
                trade_obj['tradeid'] = int(dt_index) # Set tradeid to timestamp which is the open time of the current kline not the last closed kline
                #TODO: give proper values to limit


                # Calculate enter/exit prices
                enter_price = min(time_dict['15m']['low'][-10:])
                exit_price = max(time_dict['15m']['high'][-10:])

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
                    "limit": {
                        "price": float(enter_price),
                        "quantity": float(enter_quantity),
                        "amount": float(enter_ref_amount),
                        "expire": bson.Int64(dt_index + 2*15*60*1000) # If you want to give 3 iteration, then write 2
                        },
                    }

                #enter_module["expire"] = dt_index - 3*15*60*1000 # 3 15min block later
                trade_obj['enter'] = enter_module

                # Fill exit module
                exit_module = {
                    "limit": {
                        "price": float(exit_price),
                        "quantity": float(enter_quantity),
                        "amount": float(exit_ref_amount),
                        "expire": bson.Int64(dt_index + 9*15*60*1000)
                        },
                    }
                # expire of the exit_module can be calculated after the trade entered
                trade_obj['exit'] = exit_module

                trade_dict[pair] = trade_obj

            else:
                self.logger.info(f"{pair}: NO SIGNAL")

            #for time_scale, stat_obj in time_dict.items():
                # TODO: Create a list of indicator handlers: 
                # [atr_handler(time_scale,stat_objne)]
                # Perform calculation
                #pass
        await self.dump_to(trade_dict)
        return trade_dict

    async def dump_to(self, js_obj: dict):
        js_file = open("run-time-objs/trade.json", "w")
        json.dump(js_obj, js_file, indent=4, cls=ObjectEncoder)
        js_file.close()
        self.logger.debug("trade.json file created")

        return True
