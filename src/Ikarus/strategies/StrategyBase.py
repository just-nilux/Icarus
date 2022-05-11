import json
import logging
from binance.helpers import round_step_size
from ..enums import *
import bson
import abc
import itertools
import statistics as st
from ..objects import EOrderType, EnhancedJSONEncoder
import math
from ..utils import get_lto_phase, safe_sum, round_step_downward, truncate, safe_multiply, safe_substract
from .. import binance_filters as filters
import more_itertools
import copy

logger = logging.getLogger('app')

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
    async def run_logic(self, analysis_dict, lto_list, ikarus_time, total_qc, free_qc):
        """[summary]

        Args:
            analysis_dict ([type]): [description]
            lto_list ([type]): [description]
            df_balance ([type]): [description]
            ikarus_time ([type]): [description]
            total_qc ([type]): [description]

        Returns:
            [type]: [description]
        """

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
            lto_list[lto_idx] = await StrategyBase.handle_lto_logic(self, analysis_dict, lto_list[lto_idx], ikarus_time)
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
                # NOTE: TYPE_MARKET PHASE:_EXIT LTOs are considered as alive right here. Not sure if it is a good approach
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
            if nto:= await self.make_decision(analysis_dict, ao_pair, ikarus_time, pairwise_alloc_share):
                
                # Apply exchange filters
                # NOTE: This only works for phase_enter
                if result := await StrategyBase.apply_exchange_filters(nto, self.symbol_info[ao_pair]): 
                    nto['enter'][self.config['enter']['type']] = result
                else: continue

                trade_objects.append(nto)
                empty_lto_slot -= 1

        return trade_objects


    @staticmethod
    async def handle_lto_logic(self, analysis_dict, lto, ikarus_time):

        """
        This function decides what to do for the LTOs based on their 'status'
        """        
        
        if lto['status'] == STAT_ENTER_EXP:
            if self.config['action_mapping'][STAT_ENTER_EXP] == ACTN_CANCEL or lto['history'].count(STAT_ENTER_EXP) > 1:
                return await self.on_cancel(lto)

            elif self.config['action_mapping'][STAT_ENTER_EXP] == ACTN_POSTPONE and lto['history'].count(STAT_ENTER_EXP) <= 1:
                # NOTE: postponed_candles = 1 means 2 candle
                #       If only 1 candle is desired to be postponed, then it means we will wait for newly started candle to close so postponed_candles will be 0
                return await self.on_enter_postpone(lto, ikarus_time)

        elif lto['status'] == STAT_EXIT_EXP:

            if self.config['action_mapping'][STAT_EXIT_EXP] == ACTN_UPDATE:
                return await self.on_update(lto, ikarus_time)

            elif self.config['action_mapping'][STAT_EXIT_EXP] == ACTN_POSTPONE and lto['history'].count(STAT_EXIT_EXP) <= 1:
                return await self.on_exit_postpone(lto, ikarus_time)

            elif self.config['action_mapping'][STAT_EXIT_EXP] == ACTN_MARKET_EXIT or lto['history'].count(STAT_EXIT_EXP) > 1:
                # NOTE: Market exit requires the exit prices to be known, thus provide the analysis_dict to that
                return await StrategyBase.on_market_exit(self, lto, analysis_dict)

        elif lto['status'] == STAT_WAITING_EXIT:
            # LTO is entered succesfully, so exit order should be executed
            # NOTE: expire of the exit_module can be calculated after the trade entered
            return await self.on_waiting_exit(lto, analysis_dict)

        return lto


    @abc.abstractclassmethod
    async def on_update(self):
        pass


    @staticmethod
    async def on_market_exit(self, lto, analysis_dict):
        #lto = await StrategyBase._config_market_exit(lto, self.config['exit']['type'])
        
        # NOTE: enter and exit modules represents the base idea before starting to a trade. Thus
        lto['update_history'].append(copy.deepcopy(lto['exit'][self.config['exit']['type']]))
        
        lto['exit'] = await StrategyBase._create_exit_module(
            TYPE_MARKET,
            0,
            lto['result'][PHASE_ENTER]['quantity'],
            analysis_dict[lto['pair']][self.min_period]['close'],
            0)
        
        lto['exit'][TYPE_MARKET] = await StrategyBase.apply_exchange_filters(lto, self.symbol_info[lto['pair']])
        
        lto['action'] = ACTN_MARKET_EXIT

        self.logger.info(f'LTO: market exit configured') # TODO: Add orderId

        return lto



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
    #async def run(self, analysis_dict, lto_list, df_balance, ikarus_time=None):
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
        # TODO: NEXT NEXT Integrate fee to market order
        #       Continue here
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
            trade_order.quantity = result
        else: 
            #logger.error(f"Filter failure: LOT_SIZE. {trade.strategy} in phase {phase} with quantity {str(trade.enter.quantity)}")
            return None

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
            trade_order.stopPrice = round_step_downward(trade_order.stopPrice, float(symbol_info['filters'][0]['tickSize']))
            trade_order.stopLimitPrice = round_step_downward(trade_order.stopLimitPrice, float(symbol_info['filters'][0]['tickSize']))

            if not filters.min_notional(trade_order.stopPrice, trade_order.quantity, symbol_info):
                logger.warn(f"Trade object skipped due to MIN_NOTIONAL filter for {symbol_info['symbol']}. NTO: {json.dumps(trade_order, cls=EnhancedJSONEncoder)}")
                return None

        # MIN_NOTIONAL
        # https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#min_notional
        if not filters.min_notional(trade_order.price, trade_order.quantity, symbol_info):
            logger.warn(f"Trade object skipped due to MIN_NOTIONAL filter for {symbol_info['symbol']}. NTO: {json.dumps(trade_order, cls=EnhancedJSONEncoder)}")
            return None

        return True
