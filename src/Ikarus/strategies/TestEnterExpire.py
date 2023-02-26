import statistics as st
from ..objects import ECause, Result, Trade, Limit, ECommand, TradeResult
from .StrategyBase import StrategyBase
import json
from ..utils import time_scale_to_minute

class TestEnterExpire(StrategyBase):

    def __init__(self, _tag, _config, _symbol_info):
        super().__init__(_tag, _config, _symbol_info)
        return


    async def run(self, analysis_dict, lto_list, ikarus_time, strategy_capital):
        return await super().run_logic(self, analysis_dict, lto_list, ikarus_time, strategy_capital)


    async def make_decision(self, analysis_dict, ao_pair, ikarus_time, pairwise_alloc_share):

        time_dict = analysis_dict[ao_pair]

        # Calculate enter/exit prices
        enter_price = time_dict[self.min_period]['close'][-1] * 0.5 # Expect to never enter
        enter_ref_amount=pairwise_alloc_share

        enter_limit_order = Limit(
            enter_price,
            amount=enter_ref_amount,
            expire=StrategyBase._eval_future_candle_time(ikarus_time,3,time_scale_to_minute(self.min_period))
        )

        # Set decision_time to timestamp which is the open time of the current kline (newly started not closed kline)
        trade = Trade(int(ikarus_time), self.name, ao_pair, command=ECommand.EXEC_ENTER)
        trade.set_enter(enter_limit_order)
        result = TradeResult()
        trade.result = result

        return trade


    async def on_update(self, trade, ikarus_time, **kwargs):
        return True


    async def on_cancel(self, trade):
        trade.command = ECommand.CANCEL
        trade.result.cause = ECause.ENTER_EXP
        return True


    async def on_waiting_exit(self, trade, analysis_dict, **kwargs):
        return True


    async def on_closed(self, trade):
        return True
