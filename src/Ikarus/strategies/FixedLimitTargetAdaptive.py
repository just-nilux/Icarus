import statistics as st
from ..objects import ECause, Result, Trade, Limit, ECommand, TradeResult, Market
from .StrategyBase import StrategyBase
import json
from ..utils import time_scale_to_minute

class FixedLimitTargetAdaptive(StrategyBase):

    def __init__(self, _tag, _config, _symbol_info):
        super().__init__(_tag, _config, _symbol_info)
        self.stop_entry_counter=0
        return


    async def run(self, analysis_dict, lto_list, ikarus_time, strategy_capital):
        return await super().run_logic(self, analysis_dict, lto_list, ikarus_time, strategy_capital)


    async def make_decision(self, analysis_dict, ao_pair, ikarus_time, pairwise_alloc_share):
            if self.stop_entry_counter > 0:
                self.stop_entry_counter -= 1
                return None
            
            time_dict = analysis_dict[ao_pair]

            enter_price = time_dict[self.min_period]['close'][-1]
            enter_ref_amount=pairwise_alloc_share

            enter_order = Market(amount=enter_ref_amount, price=enter_price)

            # Set decision_time to timestamp which is the open time of the current kline (newly started not closed kline)
            trade = Trade(int(ikarus_time), self.name, ao_pair, command=ECommand.EXEC_ENTER)
            trade.set_enter(enter_order)
            result = TradeResult()
            trade.result = result

            return trade


    async def on_update(self, trade, ikarus_time, **kwargs):
        # NOTE: Things to change: price, limitPrice, stopLimitPrice, expire date
        trade.command = ECommand.UPDATE
        trade.stash_exit()
        close_price = kwargs['analysis_dict'][trade.pair][self.min_period]['close'][-1]
        trade.set_exit( Market(quantity=trade.result.enter.quantity, price=close_price) )


        # Apply the filters
        # TODO: Add min notional fix (No need to add the check because we are not gonna do anything with that)
        if not StrategyBase.apply_exchange_filters(trade.exit, self.symbol_info[trade.pair]):
            # TODO: This is a critical case where the exit order failed to pass filters. Decide what to do
            return False
        return True


    async def on_waiting_exit(self, trade, analysis_dict, **kwargs):

        exit_price = trade.result.enter.price * self.config['kwargs'].get('target_profit_coeff')

        exit_limit_order = Limit(
            exit_price,
            quantity=trade.result.enter.quantity,
            expire=StrategyBase._eval_future_candle_time(kwargs['ikarus_time'],self.config['kwargs'].get('exit_duration'),time_scale_to_minute(self.min_period))
        )
        trade.set_exit(exit_limit_order)

        trade.command = ECommand.EXEC_EXIT
        if not StrategyBase.apply_exchange_filters(trade.exit, self.symbol_info[trade.pair]):
            return False
        return True

    async def on_closed(self, trade):
        # If the trade is a losing trade then stop the new entries for x iteration
        if trade.result.exit.type != 'limit':
            self.stop_entry_counter = self.config['kwargs'].get('stop_entry_counter',1)
        return trade
