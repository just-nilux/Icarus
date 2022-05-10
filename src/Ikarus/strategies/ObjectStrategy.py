import statistics as st
from ..objects import ECause, Trade, Limit, EAction
from ..enums import *
from .StrategyBase import StrategyBase
import copy
from ..utils import time_scale_to_minute

class ObjectStrategy(StrategyBase):

    def __init__(self, _config, _symbol_info={}):
        super().__init__("ObjectStrategy", _config, _symbol_info)
        return


    async def run(self, analysis_dict, lto_list, ikarus_time, total_qc, free_qc):
        return await super().run_logic(self, analysis_dict, lto_list, ikarus_time, total_qc, free_qc)


    async def make_decision(self, analysis_dict, ao_pair, ikarus_time, pairwise_alloc_share):

            time_dict = analysis_dict[ao_pair]
            trange_mean5 = st.mean(time_dict[self.min_period]['trange'][-5:])
            trange_mean20 = st.mean(time_dict[self.min_period]['trange'][-20:])

            # Make decision to enter or not
            if trange_mean5 < trange_mean20:

                # Calculate enter/exit prices
                enter_price = min(time_dict[self.min_period]['low'][-10:])
                exit_price = max(time_dict[self.min_period]['high'][-10:])
                enter_ref_amount=pairwise_alloc_share

                enter_limit_order = Limit(
                    enter_price,
                    amount=enter_ref_amount,
                    expire=StrategyBase._eval_future_candle_time(ikarus_time,15,time_scale_to_minute(self.min_period))
                )

                exit_limit_order = Limit(
                    exit_price,
                    quantity=enter_limit_order.quantity,
                    expire=StrategyBase._eval_future_candle_time(ikarus_time,15,time_scale_to_minute(self.min_period))
                )

                # Set decision_time to timestamp which is the open time of the current kline (newly started not closed kline)
                trade = Trade(int(ikarus_time), self.name, ao_pair)
                trade.set_enter(enter_limit_order)
                trade.set_exit(exit_limit_order)

                return trade

            else:
                return None


    async def on_update(self, trade, ikarus_time):
        # TODO: Give a call to methods that calculates exit point
        # NOTE: Things to change: price, limitPrice, stopLimitPrice, expire date
        trade.set_action(EAction.UPDATE)
        trade.expire = StrategyBase._eval_future_candle_time(ikarus_time,3,time_scale_to_minute(self.min_period))
        trade.set_price(trade.price*0.9)

        # Apply the filters
        # TODO: Add min notional fix (No need to add the check because we are not gonna do anything with that)
        lto['exit'][self.config['exit']['type']] = await StrategyBase.apply_exchange_filters(lto, self.symbol_info[lto['pair']])
        return trade


    async def on_cancel(self, trade):
        trade.action = EAction.CANCEL
        trade.result.cause = ECause.ENTER_EXP
        return trade


    async def on_waiting_exit(self, trade, analysis_dict):
        trade.action = EAction.EXEC_EXIT
        lto['exit'][self.config['exit']['type']] = await StrategyBase.apply_exchange_filters(lto, self.symbol_info[lto['pair']])
        return trade


    async def on_closed(self, lto):
        return lto
