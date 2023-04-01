from objects import ECause, Market, Result, Trade, ECommand, TradeResult
from strategies.StrategyBase import StrategyBase
import json
from utils import time_scale_to_minute

class TestMarketMarket(StrategyBase):

    def __init__(self, _tag, _config, _symbol_info):
        super().__init__(_tag, _config, _symbol_info)
        return


    async def run(self, analysis_dict, lto_list, ikarus_time, strategy_capital):
        return await super().run_logic(self, analysis_dict, lto_list, ikarus_time, strategy_capital)


    async def make_decision(self, analysis_dict, ao_pair, ikarus_time, pairwise_alloc_share):

            time_dict = analysis_dict[ao_pair]

            # Calculate enter/exit prices
            enter_price = time_dict[self.min_period]['close'][-1]
            enter_ref_amount=pairwise_alloc_share

            enter_order = Market(amount=enter_ref_amount, price=enter_price)

            # Set decision_time to timestamp which is the open time of the current kline (newly started not closed kline)
            trade = Trade(int(ikarus_time), self.name, ao_pair, command=ECommand.EXEC_ENTER)
            trade.set_enter(enter_order)
            result = TradeResult()
            trade.result = result

            return trade


# NOTE: No update needed
#    async def on_update(self, trade, ikarus_time, **kwargs):


# NOTE: No cancel needed
#    async def on_cancel(self, trade):


    async def on_waiting_exit(self, trade, analysis_dict, **kwargs):
        trade.command = ECommand.EXEC_EXIT

        # NOTE: The orders contain the initial idea. For market orders, it is meaningless to have others except quantity
        trade.set_exit( Market(quantity=trade.result.enter.quantity, price=analysis_dict[trade.pair][self.min_period]['close'][-1]) )

        if not StrategyBase.apply_exchange_filters(trade.exit, self.symbol_info[trade.pair]):
            return False
        return True


    async def on_closed(self, lto):
        return lto
