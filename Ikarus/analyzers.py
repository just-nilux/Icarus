import asyncio
import copy
import logging
import talib as ta
import json
from Ikarus.objects import ObjectEncoder, GenericObject

class Analyzer():
    """
    The duty of Analyzer class is to provide analysis objects.
    It is configurable via the config file
    """

    # This initiation may not be needed
    # TODO: Normally lambda functions would be quite useful to have one-liner functions, 
    #       however they are not "awaitable". Thus each one-liner lambda expression should be an awaitable method

    def __init__(self, _config):
        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.config = _config
        self.current_time_df={}
        return

    async def generate_coroutines(self):
        # NOTE: Coroutine objects creates Runtime warning when they are not called.
        #       But tasks do not create warning when they are not called
        all_indicators = {
            'low': asyncio.create_task(self._ind_low()),
            'high': asyncio.create_task(self._ind_high()),
            'llow': asyncio.create_task(self._ind_llow()),
            'hhigh': asyncio.create_task(self._ind_hhigh()),
            'trange': asyncio.create_task(self._ind_trange()),
            'moving_average': asyncio.create_task(self._ind_moving_average())
        }
        return all_indicators

    async def sample_analyzer(self, data_dict):
        analysis_dict=dict()
        for pair,data_obj in data_dict.items():
            analysis_obj = dict()

            for time_scale, time_df in data_obj.items():
                self.current_time_df = copy.deepcopy(time_df)

                # Generate coroutines
                all_indicators = await self.generate_coroutines()
                indicator_coroutines = []
                for ind in self.config['analysis']['indicators']:
                    if ind in all_indicators.keys(): indicator_coroutines.append(all_indicators[ind])
                    else: raise RuntimeError(f'Unknown indicator: "{ind}"')

                analysis_output = list(await asyncio.gather(*indicator_coroutines))

                # NOTE: Since coroutines are not reuseable, they require to be created in each cycle
                # NOTE: pd.Series needs to be casted to list
                stats = dict()
                for key, value in zip(self.config['analysis']['indicators'], analysis_output):
                    stats[key] = value
                # Assign "stats" to each "time_scale"
                analysis_obj[time_scale] = stats

            analysis_dict[pair] = analysis_obj

        # await self.dump(analysis_dict)
        return analysis_dict


    async def dump(self, js_obj):
        js_file = open("run-time-objs/analysis.json", "w")
        json.dump(js_obj, js_file, indent=4, cls=ObjectEncoder)
        js_file.close()

        return True

    # TODO: If the received data contains the newly started candle, consider this when giving index
    async def _ind_low(self): return list(self.current_time_df['low'])
    async def _ind_high(self): return list(self.current_time_df['high'])
    async def _ind_llow(self): return self.current_time_df['low'].min()
    async def _ind_hhigh(self): return self.current_time_df['high'].max()
    async def _ind_trange(self): return list(ta.TRANGE( self.current_time_df['high'],  self.current_time_df['low'],  self.current_time_df['close']))
    async def _ind_obv(self): return list(ta.OBV(self.current_time_df['close'], self.current_time_df['volume']))
    async def _ind_moving_average(self):
        ma = {}
        for param in self.config['analysis']['params']['moving_average']:
            ma[param] = list(ta.MA(self.current_time_df['close'], timeperiod=param, matype=0))
        return ma
