import json
import logging
from binance.helpers import round_step_size
from sqlalchemy import false
import bson
import abc
import itertools
from ..objects import EState, EOrderType, ECommand, EnhancedJSONEncoder, Trade
from ..utils import safe_sum, round_step_downward, truncate, safe_multiply, safe_substract, safe_divide
from .. import binance_filters as filters
from .. import position_sizing
from dataclasses import asdict
from datetime import datetime

logger = logging.getLogger('app')

class StrategyBase(metaclass=abc.ABCMeta):

    def __init__(self, _name, _config, _symbol_info):
        self.name = _name
        self.alloc_ratio = 0
        self.config = _config['strategy'][self.name]
        self.max_live_trade = self.config.get('max_live_trade',len(self.config['pairs']))

        # TODO: Rename this config as strategy config etc. because some modules means the whole config dict some are just a portion
        self.quote_currency = _config['broker']['quote_currency']
        # TODO: Make proper handling for symbol_info
        self.symbol_info = _symbol_info

        # NOTE: Hardcoded time-scales list (scales should be in ascending order)
        self.min_period = self.config['time_scales'][0]
        self.meta_do = list(itertools.product(self.config['time_scales'], self.config['pairs']))


    @staticmethod
    async def run_logic(self, analysis_dict: dict, trade_list: 'list[Trade]', ikarus_time, strategy_capital):
        '''
            This function updates the trades in trade_list but does no return it
            This function only return new trades
        '''
        # Preliminary condition: all of the config['pairs'] exist in analysis_dict
        if not set(self.config['pairs']).issubset(analysis_dict.keys()):
            logger.warn(f"Configured pair \"{self.config['pairs']}\" does not exist in analysis_dict. Skipping {self.name}.run")
            return []

        for lto_idx in range(len(trade_list)):

            # If handle_lto_logic fails then it means that the trade_list[lto_idx] is unchanged.
            if not await StrategyBase.handle_lto_logic(self, analysis_dict, trade_list[lto_idx], ikarus_time, strategy_capital):
                logger.warn(f"Function failed: 'handle_lto_logic'. Trade info: '{trade_list[lto_idx]._id}', '{trade_list[lto_idx].strategy}'")

        new_trades = []
        position_sizes = position_sizing.evaluate_size(self.config['pairs'], self.max_live_trade, strategy_capital, trade_list)

        for pair, cap in position_sizes.items():

            # Perform evaluation
            if trade:= await self.make_decision(analysis_dict, pair, ikarus_time, cap):
                
                # Apply exchange filters
                if not StrategyBase.apply_exchange_filters(trade.enter, self.symbol_info[pair]): 
                    continue

                new_trades.append(trade)
                logger.info('New trade created: {}'.format(asdict(trade)))

                if hasattr(trade.enter, 'expire'):
                    logger.debug('Expire date: {}'.format(datetime.fromtimestamp(trade.enter.expire/1000)))

        return new_trades


    @staticmethod
    async def handle_lto_logic(self, analysis_dict, trade: Trade, ikarus_time, strategy_capital):

        """
        This function decides what to do for the LTOs based on their 'status'
        strategy_capital: It is used for position sizing
        """        
        is_success = False
        if trade.status == EState.ENTER_EXP:
            is_success = await self.on_cancel(trade)

        elif trade.status == EState.EXIT_EXP:
            is_success = await self.on_update(trade, ikarus_time, analysis_dict=analysis_dict, strategy_capital=strategy_capital)
            if hasattr(trade.exit, 'expire'):
                logger.debug('Expire date: {}'.format(datetime.fromtimestamp(trade.exit.expire/1000)))

        elif trade.status == EState.WAITING_EXIT:
            # LTO is entered succesfully, so exit order should be executed
            # NOTE: expire of the exit_module can be calculated after the trade entered
            is_success = await self.on_waiting_exit(trade, analysis_dict, ikarus_time=ikarus_time, strategy_capital=strategy_capital)
            if hasattr(trade.exit, 'expire'):
                logger.debug('Expire date: {}'.format(datetime.fromtimestamp(trade.exit.expire/1000)))

        elif trade.status == EState.CLOSED:
            is_success = await self.on_closed(trade)

        else:
            is_success = True
        return is_success
        

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


    @staticmethod
    def _eval_future_candle_time(start_time, count, minute): return bson.Int64(start_time + count*minute*60*1000)


    @staticmethod
    def apply_exchange_filters(trade_order,  symbol_info):
        # TODO: Make the function orer specific using trade_order instead of trade
        """
        - Call this method prior to any order placement
        - Apply the filter of exchange pair
        - This methhod does not check if the current conditiones are good to go.
            If a filter is not satisfied then it would create an exception. Validation
            costs time. Maybe in future 
        - Separating enter and exit does not make any sense since the filters are valid for both side.
        Returns:
            Order: enter or exit module
        """ 

        # LOT_SIZE
        # https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#lot_size
        if result := filters.lot_size(trade_order.quantity, symbol_info): 
            #trade_order.quantity = result
            trade_order.set_quantity(result)
        else: 
            #logger.error(f"Filter failure: LOT_SIZE. {trade.strategy} in phase {phase} with quantity {str(trade.enter.quantity)}")
            return False

        # PRICE_FILTER
        # https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#price_filter
        if type(trade_order).__name__ == EOrderType.MARKET:
            pass

        elif type(trade_order).__name__ == EOrderType.LIMIT:
            trade_order.set_price(round_step_downward(trade_order.price, float(symbol_info['filters'][0]['tickSize'])))                        # Fixing PRICE_FILTER: tickSize
            if trade_order.price > float(symbol_info['filters'][0]['maxPrice']):
                pass
                # TODO: BUG: NEXT: Add proper error handling or check for the prices

        elif type(trade_order).__name__ == EOrderType.OCO:
            trade_order.set_price(round_step_downward(trade_order.price, float(symbol_info['filters'][0]['tickSize'])))              # Fixing PRICE_FILTER: tickSize
            trade_order.stop_price = round_step_downward(trade_order.stop_price, float(symbol_info['filters'][0]['tickSize']))
            trade_order.stop_limit_price = round_step_downward(trade_order.stop_limit_price, float(symbol_info['filters'][0]['tickSize']))

            if not filters.min_notional(trade_order.stop_price, trade_order.quantity, symbol_info):
                logger.warn(f"Trade object skipped due to MIN_NOTIONAL filter for {symbol_info['symbol']}. NTO: {json.dumps(trade_order, cls=EnhancedJSONEncoder)}")
                return False



        # TODO: Create a mechanism to properly apply min notional filter to market orders
        # NOTE: Temporary workaround for min_notional evaluation for the Market orders.
        #       The issue is min notional is applicable to market orders as well but it requires 5min average



        # MIN_NOTIONAL
        # https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#min_notional
        if not filters.min_notional(trade_order.price, trade_order.quantity, symbol_info):
            logger.warn(f"Trade object skipped due to MIN_NOTIONAL filter for {symbol_info['symbol']}. NTO: {json.dumps(trade_order, cls=EnhancedJSONEncoder)}")
            return False

        return True

