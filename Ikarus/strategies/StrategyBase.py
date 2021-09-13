import logging
from binance.helpers import round_step_size
from Ikarus.enums import *
import bson
import abc


class StrategyBase(metaclass=abc.ABCMeta):

    def __init__(self):
        # TODO: NEXT Add other trivial assignments to here
        self.alloc_perc = 0
        pass

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'run') and 
                callable(subclass.run) and 
                hasattr(subclass, 'dump_to') and 
                callable(subclass.dump_to) or 
                NotImplemented)

    @abc.abstractmethod
    async def run(self, analysis_dict, lto_list, df_balance, dt_index=None):
        """Load in the data set"""
        raise NotImplementedError

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
