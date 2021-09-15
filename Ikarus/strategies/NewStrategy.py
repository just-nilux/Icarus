import logging
import statistics as st
from ..objects import GenericObject
from ..enums import *
from .StrategyBase import StrategyBase
import copy
import itertools
from ..utils import time_scale_to_minute
from itertools import chain, groupby
import operator

class NewStrategy(StrategyBase):

    def __init__(self, _config, _symbol_info={}):
        super().__init__("NewStrategy", _config, _symbol_info)
        self.logger.info(f'{self.name} initialized')
        print(f'{self.name} initialized')
        return


    async def run_test(self, input1, input2):
        await super().run_test(self, input1, input2)


    async def on_lto_eval(self, _inp1):
        self.logger.info(f'{self.name} {_inp1}')


    async def on_decision(self, _inp2):
        self.logger.info(f'{self.name} {_inp2}')


    async def on_handle_lto(self, lto, dt_index):
        """
        This function decides what to do for the LTOs based on their 'status'
        """        
        
        if lto['status'] == STAT_ENTER_EXP:
            if self.config['action_mapping'][STAT_ENTER_EXP] == ACTN_CANCEL or lto['history'].count(STAT_ENTER_EXP) > 1:
                lto['action'] = ACTN_CANCEL
                lto['result']['cause'] = STAT_ENTER_EXP

            elif self.config['action_mapping'][STAT_ENTER_EXP] == ACTN_POSTPONE and lto['history'].count(STAT_ENTER_EXP) <= 1:
                # NOTE: postponed_candles = 1 means 2 candle
                #       If only 1 candle is desired to be postponed, then it means we will wait for newly started candle to close so postponed_candles will be 0
                postponed_candles = 1
                lto = await StrategyBase._postpone(lto,'enter', self.config['enter']['type'], StrategyBase._eval_future_candle_time(dt_index,postponed_candles,time_scale_to_minute(self.min_period))) 
            else: pass

        elif lto['status'] == STAT_EXIT_EXP:

            if self.config['action_mapping'][STAT_EXIT_EXP] == ACTN_UPDATE:
                # TODO: Give a call to methods that calculates exit point
                # NOTE: Things to change: price, limitPrice, stopLimitPrice, expire date
                lto['action'] = ACTN_UPDATE 
                lto['update_history'].append(copy.deepcopy(lto['exit'][self.config['exit']['type']])) # This is good for debugging and will be good for perf. evaluation in future
                if self.config['exit']['type'] == TYPE_LIMIT:
                    lto['exit'][TYPE_LIMIT]['price'] *= 1
                    lto['exit'][TYPE_LIMIT]['amount'] = lto['exit'][TYPE_LIMIT]['price'] * lto['exit'][TYPE_LIMIT]['quantity']
                    lto['exit'][TYPE_LIMIT]['expire'] = StrategyBase._eval_future_candle_time(dt_index,3,time_scale_to_minute(self.min_period))

                elif self.config['exit']['type'] == TYPE_OCO:
                    lto['exit'][TYPE_OCO]['limitPrice'] *= 1
                    lto['exit'][TYPE_OCO]['stopPrice'] *= 1
                    lto['exit'][TYPE_OCO]['stopLimitPrice'] *= 1
                    lto['exit'][TYPE_OCO]['amount'] = lto['exit'][TYPE_OCO]['limitPrice'] * lto['exit'][TYPE_OCO]['quantity']
                    lto['exit'][TYPE_OCO]['expire'] = StrategyBase._eval_future_candle_time(dt_index,3,time_scale_to_minute(self.min_period))

                # Apply the filters
                # TODO: Add min notional fix (No need to add the check because we are not gonna do anything with that)
                lto['exit'][self.config['exit']['type']] = await StrategyBase.apply_exchange_filters('exit', 
                                                                                                    self.config['exit']['type'], 
                                                                                                    lto['exit'][self.config['exit']['type']], 
                                                                                                    self.symbol_info[lto['pair']], 
                                                                                                    exit_qty=lto['result']['enter']['quantity'])

            elif self.config['action_mapping'][STAT_EXIT_EXP] == ACTN_POSTPONE and lto['history'].count(STAT_EXIT_EXP) <= 1:
                postponed_candles = 1
                lto = await StrategyBase._postpone(lto,'exit', self.config['exit']['type'], StrategyBase._eval_future_candle_time(dt_index,postponed_candles,time_scale_to_minute(self.min_period)))

            elif self.config['action_mapping'][STAT_EXIT_EXP] == ACTN_MARKET_EXIT or lto['history'].count(STAT_EXIT_EXP) > 1:
                lto = await StrategyBase._config_market_exit(lto, self.config['exit']['type'])
                self.logger.info(f'LTO: market exit configured') # TODO: Add orderId

            else: pass

        elif lto['status'] == STAT_WAITING_EXIT:
            # LTO is entered succesfully, so exit order should be executed
            # TODO: expire of the exit_module can be calculated after the trade entered

            lto['action'] = ACTN_EXEC_EXIT
            lto['exit'][self.config['exit']['type']] = await StrategyBase.apply_exchange_filters('exit', 
                                                                                                self.config['exit']['type'], 
                                                                                                lto['exit'][self.config['exit']['type']], 
                                                                                                self.symbol_info[lto['pair']], 
                                                                                                exit_qty=lto['result']['enter']['quantity'])

        elif lto['status'] != STAT_CLOSED:
            # If the status is not closed, just skip the iteration. otherwise go on to make a decision
            # NOTE: This logic contains the status: STAT_OPEN_EXIT, STAT_OPEN_ENTER, STAT_PART_CLOSED_ENTER, STAT_PART_CLOSED_EXIT
            pass
        return lto


    async def run(self, analysis_dict, lto_list, df_balance, dt_index):
        return await super().run_logic(self, analysis_dict, lto_list, df_balance, dt_index)

    async def on_lto_eval(self, _inp1):
        pass

    async def on_decision(self, _inp2):
        pass

    async def on_enter_expire(self):
        pass

    async def on_update(self):
        pass

    async def on_postpone(self):
        pass

    async def on_market_exit(self):
        pass

    async def on_waiting_exit(self):
        pass

    async def on_closed(self):
        pass

    async def on_make_decision(self, analysis_dict, lto_list, df_balance, dt_index):
        pass