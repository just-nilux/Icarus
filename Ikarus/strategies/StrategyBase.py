import logging
from binance.helpers import round_step_size
from Ikarus.enums import *
import bson
import abc
import itertools
import statistics as st
from ..objects import GenericObject
import copy
from ..utils import time_scale_to_minute


class StrategyBase(metaclass=abc.ABCMeta):

    def __init__(self, _name, _config, _symbol_info):
        self.name = _name
        self.alloc_ratio = 0
        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.config = _config['strategy'][self.name]
        self.max_lto = self.config.get('max_lto',1)
        # TODO: Rename this config as strategy config etc. because some modules means the whole config dict some are just a portion
        self.quote_currency = _config['broker']['quote_currency']
        # TODO: Make proper handling for symbol_info
        self.symbol_info = _symbol_info

        # NOTE: Hardcoded time-scales list (scales should be in ascending order)
        self.min_period = self.config['time_scales'][0]
        self.meta_do = list(itertools.product(self.config['time_scales'], self.config['pairs']))
        # TODO: Put the strategies in an structure so that the architecture would be solid
        #       Then assign functions in each implementation such as: on_STAT_EXIT_EXP() etc
        # It seems possible to have this on_STAT_EXIT_EXP() like approach. Surely needs to be tried again.
        # Since it facilitates so much new strategy creation and modular implementation
        
        # TODO: NEXT: Apply the self.alloc_perc to evaluation phase
        # TODO: NEXT: Find a way to implement pairwise allocation
        #       Pairwise allocation can be as follows:
        #       1. First one use it all,
        #       2. Share equal each strategy
        #       3. Adaptiove distribution
        self.pairwise_allocation = { pair for pair in self.config['pairs']}
        pass

    @staticmethod
    async def run_test(self, _input1, _input2):
        self.logger.info(f'{self.name} run test')
        await self.on_lto_eval(_input1)
        await self.on_decision(_input2)

    @staticmethod
    async def is_lto_dead(lto):
        conditions = [
            lto.get('action','') in [ACTN_CANCEL, ACTN_MARKET_EXIT], # evaluate nad make decision if TRUE
            lto.get('status','') == STAT_CLOSED # evaluate and make decision if TRUE
        ]
        if not any(conditions): # Skip evaluation if non of this is true (LTO will be alive until the next cycle)
            return False
        
        return True



    @staticmethod
    async def run_logic(self, analysis_dict, lto_list, df_balance, dt_index):
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
            list: nto_list
        """
        # TODO: Rename dt_index
        # Preliminary condition: all of the config['pairs'] exist in analysis_dict
        if not set(self.config['pairs']).issubset(analysis_dict.keys()):
            self.logger.warn(f"Configured pair \"{self.config['pairs']}\" does not exist in analysis_dict. Skipping {self.name}.run")
            return []

        # Initialize trade_dict to be filled
        trade_objects = []

        # Handle LTOs separately before the new evaluation
        # Create a mapping between the pair and lto such as {'BTCUSDT':{...}, ...}
        
        pair_grouped_ltos = {}
        alive_lto_counter = 0
        for lto_idx in range(len(lto_list)):
            lto_list[lto_idx] = await self.on_handle_lto(lto_list[lto_idx], dt_index)
            pair_grouped_ltos[lto_list[lto_idx]['pair']] = lto_list[lto_idx]
            
            # It is needed to know how many of LTOs are dead or will be dead
            if not await StrategyBase.is_lto_dead(lto_list[lto_idx]): 
                alive_lto_counter += 1

        # NOTE: Only iterate for the configured pairs. Do not run the strategy if any of them is missing in analysis_dict
        total_lto_slot = min(self.max_lto, len(self.config['pairs']))
        empty_lto_slot = total_lto_slot - alive_lto_counter

        for ao_pair in self.config['pairs']:

            # Break if there is no empty_lto_slot left
            if empty_lto_slot < 1:
                break 

            # Continue if the LTO of the pair is not dead
            if ao_pair in pair_grouped_ltos.keys():
                if not await StrategyBase.is_lto_dead(pair_grouped_ltos[ao_pair]): 
                    continue
                
            # Start evaluation
            # TODO: NEXT: Continue from heaer to add on_make_decision or whatever.
            #       One problem: you need to share trade_objects, empty_lto_slot etc. Find a solution
            time_dict = analysis_dict[ao_pair]
            trange_mean5 = st.mean(time_dict[self.min_period]['trange'][-5:])
            trange_mean20 = st.mean(time_dict[self.min_period]['trange'][-20:])

            # Make decision to enter or not
            if trange_mean5 < trange_mean20:
                self.logger.info(f"{ao_pair}: BUY SIGNAL")
                trade_obj = copy.deepcopy(GenericObject.trade)
                trade_obj['status'] = STAT_OPEN_ENTER
                trade_obj['strategy'] = self.name
                trade_obj['pair'] = ao_pair
                trade_obj['history'].append(trade_obj['status'])
                trade_obj['decision_time'] = int(dt_index) # Set decision_time to timestamp which is the open time of the current kline (newly started not closed kline)
                # TODO: give proper values to limit

                # Calculate enter/exit prices
                enter_price = min(time_dict[self.min_period]['low'][-10:])
                exit_price = max(time_dict[self.min_period]['high'][-10:])

                # Calculate enter/exit amount value

                #TODO: Amount calculation is performed to decide how much of the 'free' amount of 
                # the base asset will be used.

                free_ref_asset = df_balance.loc[self.quote_currency,'free']

                # Example: Buy XRP with 100$ in your account
                enter_ref_amount=20
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

                # Fill enter and exit modules
                enter_type = self.config['enter']['type']
                exit_type = self.config['exit']['type']

                trade_obj['enter'] = await StrategyBase._create_enter_module(enter_type, enter_price, enter_quantity, enter_ref_amount, 
                                                                        StrategyBase._eval_future_candle_time(dt_index,2,time_scale_to_minute(self.min_period)))
                trade_obj['exit'] = await StrategyBase._create_exit_module(exit_type, enter_price, enter_quantity, exit_price, exit_ref_amount, 
                                                                        StrategyBase._eval_future_candle_time(dt_index,9,time_scale_to_minute(self.min_period)))

                # TODO: Check the free amount of quote currency
                free_ref_asset = df_balance.loc[self.quote_currency,'free']

                trade_obj['enter'][self.config['enter']['type']] = await StrategyBase.apply_exchange_filters('enter', 
                                                                                                            enter_type, 
                                                                                                            trade_obj['enter'][enter_type], 
                                                                                                            self.symbol_info[ao_pair])
                # TODO: NEXT: A strategy may contain multiple pair thus the related symbol info should be given each time as argument
                if not await StrategyBase.check_min_notional(trade_obj['enter'][enter_type]['price'], trade_obj['enter'][enter_type]['quantity'], self.symbol_info[ao_pair]):
                    # TODO: Notification about min_notional
                    continue
                trade_objects.append(trade_obj)
                empty_lto_slot -= 1

            else:
                self.logger.info(f"{ao_pair}: NO SIGNAL")

        return trade_objects


    @abc.abstractclassmethod
    async def on_lto_eval(self, _inp1):
        pass

    @abc.abstractclassmethod
    async def on_make_decision(self, analysis_dict, lto_list, df_balance, dt_index):
        pass

    @abc.abstractclassmethod
    async def on_decision(self, _inp2):
        pass


    @abc.abstractclassmethod
    async def on_handle_lto(self, lto, dt_index):
        pass


    @abc.abstractclassmethod
    async def on_enter_expire(self):
        pass


    @abc.abstractclassmethod
    async def on_update(self):
        pass


    @abc.abstractclassmethod
    async def on_postpone(self):
        pass


    @abc.abstractclassmethod
    async def on_market_exit(self):
        pass


    @abc.abstractclassmethod
    async def on_waiting_exit(self):
        pass


    @abc.abstractclassmethod
    async def on_closed(self):
        pass


    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'run') and 
                callable(subclass.run) and 
                hasattr(subclass, 'dump_to') and 
                callable(subclass.dump_to) or 
                NotImplemented)

    #@abc.abstractmethod
    #async def run(self, analysis_dict, lto_list, df_balance, dt_index=None):
    #    """Load in the data set"""
    #    raise NotImplementedError

    @staticmethod
    def _eval_future_candle_time(start_time, count, minute): return bson.Int64(start_time + count*minute*60*1000)


    @staticmethod
    async def _postpone(lto, phase, type, expire_time):
        lto['action'] = ACTN_POSTPONE
        lto[phase][type]['expire'] = expire_time
        return lto


    @staticmethod
    async def _config_market_exit(lto, type):

        lto['action'] = ACTN_MARKET_EXIT
        lto['exit'][TYPE_MARKET] = {
            'amount': lto['exit'][type]['amount'],
            'quantity': lto['exit'][type]['quantity'],
            'orderId': '',
        }
        return lto


    @staticmethod
    async def _create_enter_module(type, enter_price, enter_quantity, enter_ref_amount, expire_time):

        if type == TYPE_LIMIT:
            enter_module = {
                "limit": {
                    "price": float(enter_price),
                    "quantity": float(enter_quantity),
                    "amount": float(enter_ref_amount),
                    "expire": expire_time,
                    "orderId": ""
                    },
                }
        elif type == TYPE_MARKET:
            # TODO: Create TYPE_MARKET orders to enter
            pass
        else: pass # Internal Error
        return enter_module


    @staticmethod
    async def _create_exit_module(type, enter_price, enter_quantity, exit_price, exit_ref_amount, expire_time):

        if type == TYPE_OCO:
            exit_module = {
                "oco": {
                    "limitPrice": float(exit_price),
                    "stopPrice": float(enter_price)*0.995,           # Auto-execute stop loss if the amount go below %0.05
                    "stopLimitPrice": float(enter_price)*0.994,      # Lose max %0.06 of the amount
                    "quantity": float(enter_quantity),
                    "amount": float(exit_ref_amount),
                    "expire": expire_time,
                    "orderId": "",
                    "stopLimit_orderId": ""
                }
            }
        elif type == TYPE_LIMIT:
            exit_module = {
                "limit": {
                    "price": float(exit_price),
                    "quantity": float(enter_quantity),
                    "amount": float(exit_ref_amount),
                    "expire": expire_time,
                    "orderId": ""
                    },
                }
        elif type == TYPE_MARKET:
            pass
        else: pass # Internal Error
        return exit_module


    @staticmethod
    async def apply_exchange_filters(phase, type, module, symbol_info, exit_qty=0):
        """
        - Call this method prior to any order placement
        - Apply the filter of exchange pair
        - This methhod does not check if the current conditiones are good to go.
            If a filter is not satisfied then it would create an exception. Validation
            costs time. Maybe in future 
        - Separating enter and exit does not make any sense since the filters are valid for both side.
        Returns:
            dict: enter or exit module
        """ 
        
        if phase == 'enter':
            module['price'] = round_step_size(module['price'], float(symbol_info['filters'][0]['tickSize']))                            # Fixing PRICE_FILTER: tickSize
            module['quantity'] = round_step_size(module['amount'] /module['price'], float(symbol_info['filters'][2]['minQty']))         # Fixing LOT_SIZE: minQty

        elif phase == 'exit':
            if type == TYPE_OCO:
                module['limitPrice'] = round_step_size(module['limitPrice'], float(symbol_info['filters'][0]['tickSize']))              # Fixing PRICE_FILTER: tickSize
                module['stopPrice'] = round_step_size(module['stopPrice'], float(symbol_info['filters'][0]['tickSize']))
                module['stopLimitPrice'] = round_step_size(module['stopLimitPrice'], float(symbol_info['filters'][0]['tickSize']))
                module['quantity'] = round_step_size(exit_qty, float(symbol_info['filters'][2]['minQty']))                              # NOTE: Enter quantity will be used to exit
            
            elif type == TYPE_LIMIT:
                module['price'] = round_step_size(module['price'], float(symbol_info['filters'][0]['tickSize']))
                module['quantity'] = round_step_size(exit_qty, float(symbol_info['filters'][2]['minQty']))                              # NOTE: Enter quantity will be used to exit

        else: pass

        return module


    @staticmethod
    async def check_min_notional(price, quantity, symbol_info): return ((price*quantity) > float(symbol_info['filters'][3]['minNotional']))  # if valid: True, else: False
