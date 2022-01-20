import logging
import statistics as st
from ..objects import GenericObject
from ..enums import *
from .StrategyBase import StrategyBase
import copy
import itertools
from ..utils import time_scale_to_minute, time_scale_to_milisecond
import json
from ..exceptions import FatalException

class UpTrenderMarket(StrategyBase):

    def __init__(self, _config, _symbol_info={}):
        super().__init__("UpTrenderMarket", _config, _symbol_info)
        self.lower_limit = 30
        self.upper_limit = 70
        return


    async def run(self, analysis_dict, lto_list, ikarus_time, total_qc, free_qc):
        return await super().run_logic(self, analysis_dict, lto_list, ikarus_time, total_qc, free_qc)


    async def make_decision(self, analysis_dict, ao_pair, ikarus_time, pairwise_alloc_share):

            time_dict = analysis_dict[ao_pair]
            last_uptrend = time_dict['1d']['market_classifier']['uptrend'][-1]
            
            # If there is
            diff = int((ikarus_time - last_uptrend['validation_point'])/time_scale_to_milisecond(self.min_period))
            #print(diff,'\n')
            #self.logger.debug(f'diff: {diff}')

            # Check the last closed candle is in the uptrend or not


            # No need to check for validation_point because the class_item exist if the validation passes
            # TODO: validaiton might be removed from analysis and left to strategies


            if diff == 1:

                trade_obj = copy.deepcopy(GenericObject.trade)
                trade_obj['status'] = STAT_OPEN_ENTER
                trade_obj['strategy'] = self.name
                trade_obj['pair'] = ao_pair
                trade_obj['history'].append(trade_obj['status'])
                trade_obj['decision_time'] = int(ikarus_time) # Set decision_time to timestamp which is the open time of the current kline (newly started not closed kline)

                # Calculate enter/exit prices
                # NOTE: For Market enters, the enter_price value is just a value to determine the quantity
                #       It is simply a rough estimation to go forward
                enter_price = float(time_dict[self.min_period]['close'])

                enter_ref_amount=pairwise_alloc_share

                # Fill enter module
                enter_type = self.config['enter']['type'] # TYPE_MARKET
                trade_obj['enter'] = await StrategyBase._create_enter_module(
                    enter_type, 
                    enter_price, 
                    enter_ref_amount, 
                    0)

                # Fill exit module
                # TODO: Check if the exit moudle creation is really required
                exit_type = self.config['exit']['type']
                trade_obj['exit'] = await StrategyBase._create_exit_module(
                    exit_type,
                    enter_price,
                    trade_obj['enter'][enter_type]['quantity'],
                    0,
                    0)
                
                return trade_obj

            else:
                return None


    async def on_update(self, lto, ikarus_time):
        raise NotImplementedError(f'This function does not supported by {self.name}')


    async def on_exit_postpone(self, lto, ikarus_time):
        raise NotImplementedError(f'This function does not supported by {self.name}')


    async def on_enter_postpone(self, lto, ikarus_time):
        raise NotImplementedError(f'This function does not supported by {self.name}')


    async def on_cancel(self, lto):
        raise NotImplementedError(f'This function does not supported by {self.name}')


    async def on_waiting_exit(self, lto, analysis_dict, ikarus_time):

        if self.config['exit']['type'] == TYPE_MARKET:
            time_dict = analysis_dict[lto['pair']]
            last_uptrend = time_dict['1d']['market_classifier']['uptrend'][-1]

            diff = int((ikarus_time - last_uptrend['end'])/time_scale_to_milisecond(self.min_period))

            if diff != 1:

                # TODO: Add info log: market exit decided
                lto['exit'] = await StrategyBase._create_exit_module(
                    TYPE_MARKET,
                    0,
                    lto['result'][PHASE_ENTER]['quantity'],
                    analysis_dict[lto['pair']][self.min_period]['close'],
                    0)
            else:
                return lto
        else:
            raise FatalException(f"Unexpected exit type: {self.config['exit']['type']}")

        lto['action'] = ACTN_EXEC_EXIT
        lto['exit'][self.config['exit']['type']] = await StrategyBase.apply_exchange_filters(lto, self.symbol_info[lto['pair']])
        return lto

    async def on_closed(self, lto):
        return lto
