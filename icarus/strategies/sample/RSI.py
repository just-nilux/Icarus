from objects import Market, Trade, ECommand, TradeResult
from strategies.StrategyBase import StrategyBase

class RSI(StrategyBase):

    def __init__(self, _tag, _config, _symbol_info):

        self.lower_limit = 30#kwargs.get('lower_limit', 30)
        self.upper_limit = 70#kwargs.get('upper_limit', 70)
        
        super().__init__(_tag, _config, _symbol_info)
        return


    async def run(self, analysis_dict, lto_list, ikarus_time, total_qc, free_qc):
        return await super().run_logic(self, analysis_dict, lto_list, ikarus_time, total_qc, free_qc)


    async def make_decision(self, analysis_dict, ao_pair, ikarus_time, pairwise_alloc_share):

            time_dict = analysis_dict[ao_pair]

            if time_dict[self.min_period]['rsi'][-2] < self.lower_limit and \
                self.lower_limit < time_dict[self.min_period]['rsi'][-1] < self.upper_limit:
                # BUY
                enter_price = time_dict[self.min_period]['close'][-1]
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
        time_dict = analysis_dict[trade.pair]

        if time_dict[self.min_period]['rsi'][-2] > self.upper_limit and \
            self.lower_limit < time_dict[self.min_period]['rsi'][-1] < self.upper_limit:

            trade.set_exit( Market(quantity=trade.result.enter.quantity, price=analysis_dict[trade.pair][self.min_period]['close'][-1]) )

            if not StrategyBase.apply_exchange_filters(trade.exit, self.symbol_info[trade.pair]):
                trade.reset_exit()
                return False
            
            trade.set_command(ECommand.EXEC_EXIT)
        return True


    async def on_closed(self, lto):
        return lto
