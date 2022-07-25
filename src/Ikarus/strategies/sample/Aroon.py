from ...objects import Market, Trade, ECommand, TradeResult
from ..StrategyBase import StrategyBase

class Aroon(StrategyBase):

    def __init__(self, _config, _symbol_info, **kwargs):
        super().__init__("Aroon", _config, _symbol_info)
        return


    async def run(self, analysis_dict, lto_list, ikarus_time, total_qc, free_qc):
        return await super().run_logic(self, analysis_dict, lto_list, ikarus_time, total_qc, free_qc)


    async def make_decision(self, analysis_dict, ao_pair, ikarus_time, pairwise_alloc_share):

            aroon = analysis_dict[ao_pair][self.min_period]['aroon']

            if aroon['aroonup'][-1] > aroon['aroondown'][-1] and aroon['aroonup'][-2] < aroon['aroondown'][-2]:
                # BUY
                enter_price = analysis_dict[ao_pair][self.min_period]['close']
                enter_ref_amount=pairwise_alloc_share

                enter_order = Market(amount=enter_ref_amount, price=enter_price)

                # Set decision_time to timestamp which is the open time of the current kline (newly started not closed kline)
                trade = Trade(int(ikarus_time), self.name, ao_pair, command=ECommand.EXEC_ENTER)
                trade.set_enter(enter_order)
                result = TradeResult()
                trade.result = result
                return trade

            else:
                return None


    async def on_waiting_exit(self, trade, analysis_dict, **kwargs):
        #time_dict = analysis_dict[trade.pair]
        aroon = analysis_dict[trade.pair][self.min_period]['aroon']

        if aroon['aroondown'][-1] > aroon['aroonup'][-1] and aroon['aroondown'][-2] < aroon['aroonup'][-2]:

            trade.set_exit( Market(quantity=trade.result.enter.quantity, price=analysis_dict[trade.pair][self.min_period]['close']) )

            if not StrategyBase.apply_exchange_filters(trade.exit, self.symbol_info[trade.pair]):
                trade.reset_exit()
                return False
            
            trade.set_command(ECommand.EXEC_EXIT)
        return True


    async def on_closed(self, lto):
        return lto
