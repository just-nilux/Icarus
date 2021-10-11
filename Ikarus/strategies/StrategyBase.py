import logging
from binance.helpers import round_step_size
from Ikarus.enums import *
import bson
import abc
import itertools
import statistics as st
from ..objects import GenericObject
import math
from ..utils import safe_sum, time_scale_to_minute, round_step_downward, truncate, safe_multiply, safe_substract
import more_itertools

class StrategyBase(metaclass=abc.ABCMeta):
    # NOTE: fee can stay here until a better place is found
    fee = 0

    def __init__(self, _name, _config, _symbol_info):
        self.name = _name
        self.alloc_ratio = 0
        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.config = _config['strategy'][self.name]
        self.max_lto = self.config.get('max_lto',1)

        # NOTE: Assigning the fee multiple times is not the most optimal solution
        StrategyBase.fee = _config['broker'].get('fee', 0)
        # TODO: Rename this config as strategy config etc. because some modules means the whole config dict some are just a portion
        self.quote_currency = _config['broker']['quote_currency']
        # TODO: Make proper handling for symbol_info
        self.symbol_info = _symbol_info

        # NOTE: Hardcoded time-scales list (scales should be in ascending order)
        self.min_period = self.config['time_scales'][0]
        self.meta_do = list(itertools.product(self.config['time_scales'], self.config['pairs']))

        # It seems possible to have this on_STAT_EXIT_EXP() like approach. Surely needs to be tried again.
        # Since it facilitates so much new strategy creation and modular implementation

        # NOTE: strategywise_alloc_rate determines the available rate of use from the main capital
        #       If self.strategywise_alloc_rate is 0.25 then this strategy can use max %25 of the main capital
        self.strategywise_alloc_rate = 0 # Will be filled by the strategy manager

        # NOTE: pairwise_alloc_rate determines the available rate of use from the strategywise allocated capital
        #       If self.strategywise_alloc_rate is 0.25 then this strategy can use max %25 of the main capital
        pass


    @staticmethod
    async def is_lto_dead(lto):
        conditions = [
            # lto.get('action','') in [ACTN_CANCEL, ACTN_MARKET_EXIT], # evaluate nad make decision if TRUE
            lto.get('action','') == ACTN_CANCEL,                       # evaluate nad make decision if TRUE
            lto.get('status','') == STAT_CLOSED                        # evaluate and make decision if TRUE
        ]
        if not any(conditions): # Skip evaluation if non of this is true (LTO will be alive until the next cycle)
            return False
        
        return True


    @staticmethod
    async def run_logic(self, analysis_dict, lto_list, dt_index, total_qc, free_qc):
        """[summary]

        Args:
            analysis_dict ([type]): [description]
            lto_list ([type]): [description]
            df_balance ([type]): [description]
            dt_index ([type]): [description]
            total_qc ([type]): [description]

        Returns:
            [type]: [description]
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
        in_trade_capital = 0
        dead_lto_capital = 0
        for lto_idx in range(len(lto_list)):
            lto_list[lto_idx] = await StrategyBase.handle_lto_logic(self, analysis_dict, lto_list[lto_idx], dt_index)
            pair_grouped_ltos[lto_list[lto_idx]['pair']] = lto_list[lto_idx]
            
            # It is needed to know how many of LTOs are dead or will be dead
            # TODO: Make this function non-awaitable
            if not await StrategyBase.is_lto_dead(lto_list[lto_idx]): 
                # NOTE: in_trade_capital is only calcualted for LTOs that will last until at least next candle
                #in_trade_capital += lto_list[lto_idx][PHASE_ENTER][TYPE_LIMIT]['amount']
                # NOTE: For the enter_expire, PHASE_ENTER can be directly reflected to balance
                #       market_exit is not considered as dead lto
                #       The result of the OCO orders is unknown
                in_trade_capital = safe_sum(in_trade_capital, more_itertools.one(lto_list[lto_idx][PHASE_ENTER].values())['amount'])
                alive_lto_counter += 1
            
            else:
                # Dead capital
                dead_lto_capital = safe_sum(dead_lto_capital, more_itertools.one(lto_list[lto_idx][PHASE_ENTER].values())['amount'])

        # NOTE: Only iterate for the configured pairs. Do not run the strategy if any of them is missing in analysis_dict
        total_lto_slot = min(self.max_lto, len(self.config['pairs']))
        empty_lto_slot = total_lto_slot - alive_lto_counter

        if empty_lto_slot < 1:
            return [] # TODO Debug this ansync LTO issue buy doing debugging around here

        # Evaluate pairwise_alloc_share
        strategy_capital = safe_multiply(total_qc, self.strategywise_alloc_rate)
        
        #for lto in lto_list:
        #    in_trade_capital += lto[PHASE_ENTER][TYPE_LIMIT]['amount']
        free_strategy_capital = safe_substract(strategy_capital, in_trade_capital)

        available_capital = min(free_strategy_capital, safe_sum(free_qc, dead_lto_capital))
        # TODO: This can be updated to use some kind of precision from the symbol info instead of hardcoded 8
        pairwise_alloc_share = truncate(available_capital/empty_lto_slot, 8)

        #available_lto_capital = min(pairwise_alloc_share, free_qc+dead_lto_capital)
        
        # Iterate over pairs and make decisions about them
        for ao_pair in self.config['pairs']:

            # Break if there is no empty_lto_slot left
            if empty_lto_slot < 1:
                break 

            # Continue if the LTO of the pair is not dead
            if ao_pair in pair_grouped_ltos.keys():
                if not await StrategyBase.is_lto_dead(pair_grouped_ltos[ao_pair]): 
                    continue

            # Perform evaluation
            decision = await self.make_decision(analysis_dict, ao_pair, dt_index, pairwise_alloc_share)
            if decision:
                trade_objects.append(decision)
                empty_lto_slot -= 1

        return trade_objects


    @staticmethod
    async def handle_lto_logic(self, analysis_dict, lto, dt_index):

        """
        This function decides what to do for the LTOs based on their 'status'
        """        
        
        if lto['status'] == STAT_ENTER_EXP:
            if self.config['action_mapping'][STAT_ENTER_EXP] == ACTN_CANCEL or lto['history'].count(STAT_ENTER_EXP) > 1:
                return await self.on_cancel(lto)

            elif self.config['action_mapping'][STAT_ENTER_EXP] == ACTN_POSTPONE and lto['history'].count(STAT_ENTER_EXP) <= 1:
                # NOTE: postponed_candles = 1 means 2 candle
                #       If only 1 candle is desired to be postponed, then it means we will wait for newly started candle to close so postponed_candles will be 0
                return await self.on_enter_postpone(lto, dt_index)

        elif lto['status'] == STAT_EXIT_EXP:

            if self.config['action_mapping'][STAT_EXIT_EXP] == ACTN_UPDATE:
                return await self.on_update(lto, dt_index)

            elif self.config['action_mapping'][STAT_EXIT_EXP] == ACTN_POSTPONE and lto['history'].count(STAT_EXIT_EXP) <= 1:
                return await self.on_exit_postpone(lto, dt_index)

            elif self.config['action_mapping'][STAT_EXIT_EXP] == ACTN_MARKET_EXIT or lto['history'].count(STAT_EXIT_EXP) > 1:
                return await self.on_market_exit(lto)

        elif lto['status'] == STAT_WAITING_EXIT:
            # LTO is entered succesfully, so exit order should be executed
            # TODO: expire of the exit_module can be calculated after the trade entered
            return await self.on_waiting_exit(lto, analysis_dict)

        return lto


    @abc.abstractclassmethod
    async def on_update(self):
        pass


    @abc.abstractclassmethod
    async def on_enter_postpone(self):
        pass


    @abc.abstractclassmethod
    async def on_exit_postpone(self):
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
        # TODO: Integrate fee to market order
        # TODO: Integrate price to market order, even if it has no use
        #       For now, it works and I am not gonna touch it for a rework
        lto['action'] = ACTN_MARKET_EXIT
        lto['exit'][TYPE_MARKET] = {
            'amount': lto['exit'][type]['amount'],
            'quantity': lto['exit'][type]['quantity'],
            'orderId': '',
        }
        return lto


    @staticmethod
    async def _create_enter_module(type, enter_price, enter_ref_amount, expire_time):

        # NOTE: amount = enter_price * enter_quantity
        #       amount is excluded from the fees

        # NOTE: enter_ref_amount is the total quantity of the quote currency that will be used for the trade.
        #       It includes the stake amount and the transaction fee (comission)
        
        # NOTE: It is assumed that the fee is paid in the quote currency not BNB.
        #       For BNB, some generalizations and details needs to be implemented
        enter_quantity = enter_ref_amount / (enter_price * (1 + StrategyBase.fee))

        if type == TYPE_LIMIT:
            enter_module = {
                TYPE_LIMIT: {
                    "price": float(enter_price),
                    "quantity": float(enter_quantity),
                    "fee": float(enter_price * enter_quantity * StrategyBase.fee),
                    "amount": float(enter_quantity * enter_price),
                    "expire": expire_time,
                    "orderId": ""
                    },
                }
        elif type == TYPE_MARKET:
            # TODO: For market buy it, the quantity is needed, but the price is volatile and unknown.
            #       It is impossible to know the fee exactly. Some guess might be added, or simply
            #       the quantity might be guessed roughly to not to exceed the max allowed capital
            enter_module = {
                TYPE_MARKET: {
                    "price": float(enter_price),
                    "quantity": float(enter_quantity),
                    "fee": float(enter_price * enter_quantity * StrategyBase.fee),
                    "amount": float(enter_quantity * enter_price),
                    "orderId": ""
                    },
                }
        else: pass # Internal Error

        # NOTE: Actually no difference in the objects, in terms of value and te stucture
        #       Only the difference is, one is full of certain values, the other is about expectations
        return enter_module


    @staticmethod
    async def _create_exit_module(type, enter_price, enter_quantity, exit_price, expire_time):
        
        # NOTE: amount = exit_price * enter_quantity

        # TODO: receive stopPrice and stopLimitPrice directly as argument
        if type == TYPE_OCO:
            exit_module = {
                TYPE_OCO: {
                    "limitPrice": float(exit_price),
                    "stopPrice": float(enter_price)*0.995,           # Auto-execute stop loss if the amount go below %0.05
                    "stopLimitPrice": float(enter_price)*0.994,      # Lose max %0.06 of the amount
                    "quantity": float(enter_quantity),
                    "fee": float(enter_quantity * exit_price * StrategyBase.fee),
                    "amount": float(exit_price * enter_quantity),
                    "expire": expire_time,
                    "orderId": "",
                    "stopLimit_orderId": ""
                }
            }
        elif type == TYPE_LIMIT:
            exit_module = {
                TYPE_LIMIT: {
                    "price": float(exit_price),
                    "quantity": float(enter_quantity),
                    "fee": float(enter_quantity * exit_price * StrategyBase.fee),
                    "amount": float(exit_price * enter_quantity),
                    "expire": expire_time,
                    "orderId": ""
                    },
                }
        elif type == TYPE_MARKET:
            # NOTE: Even if there is no exact price to calcualte fee, some rough valuyes can be given
            #       It would also be helpful if this last closed price method works as expected.
            exit_module = {
                TYPE_MARKET: {
                    "price": float(exit_price),
                    "quantity": float(enter_quantity),
                    "fee": float(enter_quantity * exit_price * StrategyBase.fee),
                    "amount": float(exit_price * enter_quantity),
                    "orderId": ""
                    },
                }
            pass
        else: pass # Internal Error
        return exit_module


    @staticmethod
    async def apply_exchange_filters(phase, type, module, symbol_info, exit_qty=0):
        # TODO: NEXT: Get rid of this exit_qty bullshit
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
        # TODO: Do proper rounding to not to exceed target amount. Temporary fix is the max_capital_ratio values smaller than 1
        #       round_step_size may round up: 1.1359267447385257 -> 1.13593
        if phase == 'enter':
            if type == TYPE_LIMIT:
                module['price'] = round_step_downward(module['price'], float(symbol_info['filters'][0]['tickSize']))                        # Fixing PRICE_FILTER: tickSize
                module['quantity'] = round_step_downward(module['quantity'], float(symbol_info['filters'][2]['minQty']))                    # Fixing LOT_SIZE: minQty
            
            elif type == TYPE_MARKET:
                module['quantity'] = round_step_downward(module['quantity'], float(symbol_info['filters'][2]['minQty']))                    # Fixing LOT_SIZE: minQty

        elif phase == 'exit':
            if type == TYPE_OCO:
                module['limitPrice'] = round_step_downward(module['limitPrice'], float(symbol_info['filters'][0]['tickSize']))              # Fixing PRICE_FILTER: tickSize
                module['stopPrice'] = round_step_downward(module['stopPrice'], float(symbol_info['filters'][0]['tickSize']))
                module['stopLimitPrice'] = round_step_downward(module['stopLimitPrice'], float(symbol_info['filters'][0]['tickSize']))
                module['quantity'] = round_step_downward(exit_qty, float(symbol_info['filters'][2]['minQty']))                              # NOTE: Enter quantity will be used to exit
            
            elif type == TYPE_LIMIT:
                module['price'] = round_step_downward(module['price'], float(symbol_info['filters'][0]['tickSize']))
                module['quantity'] = round_step_downward(exit_qty, float(symbol_info['filters'][2]['minQty']))                              # NOTE: Enter quantity will be used to exit
            
            elif type == TYPE_MARKET:
                module['quantity'] = round_step_downward(exit_qty, float(symbol_info['filters'][2]['minQty']))
                # TODO: NEXT: Remove the exit_qty

        else: pass

        module['amount'] = safe_multiply(module['quantity'], module['price'])
        module['fee'] = safe_multiply(module['amount'], StrategyBase.fee)

        return module


    @staticmethod
    async def check_min_notional(price, quantity, symbol_info): 
        return (safe_multiply(price, quantity) > float(symbol_info['filters'][3]['minNotional']))  # if valid: True, else: False
