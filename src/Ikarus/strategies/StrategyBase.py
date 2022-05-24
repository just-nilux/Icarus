import json
import logging
from binance.helpers import round_step_size
from sqlalchemy import false
from ..enums import *
import bson
import abc
import itertools
from ..objects import EState, EOrderType, ECommand, EnhancedJSONEncoder
from ..utils import safe_sum, round_step_downward, truncate, safe_multiply, safe_substract
from .. import binance_filters as filters
from ..exceptions import NotImplementedException

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
    def is_lto_dead(trade):
      
        if trade.command == ECommand.CANCEL or trade.status == EState.CLOSED:
            return True     # Trade is dead
        else:
            return False    # Trade is alive # Skip evaluation if non of this is true (LTO will be alive until the next cycle)


    @staticmethod
    async def run_logic(self, analysis_dict, trade_list, ikarus_time, total_qc, free_qc):
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
        for lto_idx in range(len(trade_list)):
            trade_list[lto_idx] = await StrategyBase.handle_lto_logic(self, analysis_dict, trade_list[lto_idx], ikarus_time)
            pair_grouped_ltos[trade_list[lto_idx].pair] = trade_list[lto_idx]
            
            # It is needed to know how many of LTOs are dead or will be dead
            if not StrategyBase.is_lto_dead(trade_list[lto_idx]): 
                # NOTE: in_trade_capital is only calcualted for LTOs that will last until at least next candle
                #in_trade_capital += lto_list[lto_idx][PHASE_ENTER][TYPE_LIMIT]['amount']
                # NOTE: For the enter_expire, PHASE_ENTER can be directly reflected to balance
                #       market_exit is not considered as dead lto
                #       The result of the OCO orders is unknown
                in_trade_capital = safe_sum(in_trade_capital, trade_list[lto_idx].enter.amount)
                alive_lto_counter += 1
                # NOTE: TYPE_MARKET PHASE:_EXIT LTOs are considered as alive right here. Not sure if it is a good approach
            else:
                # Dead capital
                dead_lto_capital = safe_sum(dead_lto_capital, trade_list[lto_idx].enter.amount)

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
                if not StrategyBase.is_lto_dead(pair_grouped_ltos[ao_pair]): 
                    continue

            # Perform evaluation
            if trade:= await self.make_decision(analysis_dict, ao_pair, ikarus_time, pairwise_alloc_share):
                
                # Apply exchange filters
                if not StrategyBase.apply_exchange_filters(trade.enter, self.symbol_info[ao_pair]): 
                    continue

                trade_objects.append(trade)
                empty_lto_slot -= 1

        return trade_objects


    @staticmethod
    async def handle_lto_logic(self, analysis_dict, trade, ikarus_time):

        """
        This function decides what to do for the LTOs based on their 'status'
        """        
        
        if trade.status == EState.ENTER_EXP:
            if self.config['action_mapping'][EState.ENTER_EXP] == ECommand.CANCEL:
                await self.on_cancel(trade)

        elif trade.status == EState.EXIT_EXP:
            if self.config['action_mapping'][EState.EXIT_EXP] == ECommand.UPDATE:
                is_success = await self.on_update(trade, ikarus_time)

            elif self.config['action_mapping'][EState.EXIT_EXP] == ECommand.MARKET_EXIT:
                # NOTE: Market exit requires the exit prices to be known, thus provide the analysis_dict to that
                is_success = await StrategyBase.on_market_exit(self, trade, analysis_dict)

        elif trade.status == EState.WAITING_EXIT:
            # LTO is entered succesfully, so exit order should be executed
            # NOTE: expire of the exit_module can be calculated after the trade entered
            return await self.on_waiting_exit(trade, analysis_dict)

        return trade


    @abc.abstractclassmethod
    async def on_update(self):
        pass


    @staticmethod
    async def on_market_exit(self, trade, analysis_dict):
        # TODO: Create market exit logic
        raise NotImplementedException()
        '''
        #lto = await StrategyBase._config_market_exit(lto, self.config['exit']['type'])
                
        lto['exit'] = await StrategyBase._create_exit_module(
            TYPE_MARKET,
            0,
            lto['result'][PHASE_ENTER]['quantity'],
            analysis_dict[lto['pair']][self.min_period]['close'],
            0)
        
        lto['exit'][TYPE_MARKET] = await StrategyBase.apply_exchange_filters(lto, self.symbol_info[lto['pair']])
        trade.exi
        
        trade.command = ECommand.MARKET_EXIT

        self.logger.info(f'LTO: market exit configured') # TODO: Add orderId
        '''
        return trade
        


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
