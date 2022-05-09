import statistics as st
from ..objects import Trade, LimitOrder
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

                trade = Trade( int(ikarus_time), self.name, ao_pair)
                # Set decision_time to timestamp which is the open time of the current kline (newly started not closed kline)

                # Calculate enter/exit prices
                enter_price = min(time_dict[self.min_period]['low'][-10:])
                exit_price = max(time_dict[self.min_period]['high'][-10:])

                enter_ref_amount=pairwise_alloc_share

                # Fill enter module
                enter_limit_order = LimitOrder(
                    StrategyBase._eval_future_candle_time(ikarus_time,15,time_scale_to_minute(self.min_period)),
                    enter_price,
                    amount=enter_ref_amount
                )

                trade.set_enter(enter_limit_order)

                # Fill exit module
                exit_limit_order = LimitOrder(
                    StrategyBase._eval_future_candle_time(ikarus_time,15,time_scale_to_minute(self.min_period)),
                    exit_price,
                    quantity=enter_limit_order.quantity
                )
                trade.set_exit(exit_limit_order)

                return trade

            else:
                return None


    async def on_update(self, lto, ikarus_time):
        # TODO: Give a call to methods that calculates exit point
        # NOTE: Things to change: price, limitPrice, stopLimitPrice, expire date
        lto['action'] = ACTN_UPDATE 
        lto['update_history'].append(copy.deepcopy(lto['exit'][self.config['exit']['type']])) # This is good for debugging and will be good for perf. evaluation in future
        if self.config['exit']['type'] == TYPE_LIMIT:
            lto['exit'][TYPE_LIMIT]['price'] *= 0.9
            lto['exit'][TYPE_LIMIT]['amount'] = lto['exit'][TYPE_LIMIT]['price'] * lto['exit'][TYPE_LIMIT]['quantity']
            lto['exit'][TYPE_LIMIT]['expire'] = StrategyBase._eval_future_candle_time(ikarus_time,3,time_scale_to_minute(self.min_period))

        elif self.config['exit']['type'] == TYPE_OCO:
            lto['exit'][TYPE_OCO]['limitPrice'] *= 0.9
            lto['exit'][TYPE_OCO]['stopPrice'] *= 0.9
            lto['exit'][TYPE_OCO]['stopLimitPrice'] *= 0.9
            lto['exit'][TYPE_OCO]['amount'] = lto['exit'][TYPE_OCO]['limitPrice'] * lto['exit'][TYPE_OCO]['quantity']
            lto['exit'][TYPE_OCO]['expire'] = StrategyBase._eval_future_candle_time(ikarus_time,3,time_scale_to_minute(self.min_period))

        # Apply the filters
        # TODO: Add min notional fix (No need to add the check because we are not gonna do anything with that)
        lto['exit'][self.config['exit']['type']] = await StrategyBase.apply_exchange_filters(lto, self.symbol_info[lto['pair']])
        return lto


    async def on_exit_postpone(self, lto, ikarus_time):
        postponed_candles = 1
        lto = await StrategyBase._postpone(lto,'exit', self.config['exit']['type'], StrategyBase._eval_future_candle_time(ikarus_time,postponed_candles,time_scale_to_minute(self.min_period)))
        return lto


    async def on_enter_postpone(self, lto, ikarus_time):
        postponed_candles = 1
        lto = await StrategyBase._postpone(lto,'enter', self.config['enter']['type'], StrategyBase._eval_future_candle_time(ikarus_time,postponed_candles,time_scale_to_minute(self.min_period))) 
        return lto


    async def on_cancel(self, lto):
        lto['action'] = ACTN_CANCEL
        lto['result']['cause'] = STAT_ENTER_EXP
        return lto


    async def on_waiting_exit(self, lto, analysis_dict):
        lto['action'] = ACTN_EXEC_EXIT
        lto['exit'][self.config['exit']['type']] = await StrategyBase.apply_exchange_filters(lto, self.symbol_info[lto['pair']])
        return lto


    async def on_closed(self, lto):
        return lto
