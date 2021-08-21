import asyncio
import copy
import logging
import talib as ta
import json
from Ikarus.objects import ObjectEncoder, GenericObject
from Ikarus.exceptions import NotImplementedException

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
            'moving_average': asyncio.create_task(self._ind_moving_average()),
            'bband': asyncio.create_task(self._ind_bband()),
        }
        return all_indicators

    async def sample_analyzer(self, data_dict):
        analysis_dict=dict()
        for pair,data_obj in data_dict.items():
            analysis_obj = dict()

            for time_scale, time_df in data_obj.items():
                self.current_time_df = copy.deepcopy(time_df)

                # Generate coroutines
                # NOTE: live-engine contains the newly created candle as well
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

        return analysis_dict


    async def dump(self, js_obj):
        js_file = open("run-time-objs/analysis.json", "w")
        json.dump(js_obj, js_file, indent=4, cls=ObjectEncoder)
        js_file.close()

        return True

    # TODO: NEXT: If the received data contains the newly started candle, consider this when giving index
    async def _ind_low(self): return list(self.current_time_df['low'])
    async def _ind_high(self): return list(self.current_time_df['high'])
    async def _ind_llow(self): return self.current_time_df['low'].min()
    async def _ind_hhigh(self): return self.current_time_df['high'].max()
    async def _ind_trange(self): return list(ta.TRANGE( self.current_time_df['high'],  self.current_time_df['low'],  self.current_time_df['close']))
    async def _ind_obv(self): return list(ta.OBV(self.current_time_df['close'], self.current_time_df['volume']))


    # Overlap Studies
    async def _ind_bband(self):
        upperband, middleband, lowerband = ta.BBANDS(self.current_time_df['close'], 
                                                        timeperiod=self.config['analysis']['params']['bband']['timeperiod'], 
                                                        nbdevup=self.config['analysis']['params']['bband']['nbdevup'], 
                                                        nbdevdn=self.config['analysis']['params']['bband']['nbdevdn'], 
                                                        matype=0) # No config option for matype yet!
        return {'upper':list(upperband), 'middle': list(middleband), 'lower':list(lowerband)}
    async def _ind_dema(self): raise NotImplementedException('indicator')
    async def _ind_ema(self): raise NotImplementedException('indicator')
    async def _ind_ht_trendline(self): raise NotImplementedException('indicator')
    async def _ind_kama(self): raise NotImplementedException('indicator')
    async def _ind_ma(self):
        ma = {}
        for param in self.config['analysis']['params']['moving_average']:
            ma[param] = list(ta.MA(self.current_time_df['close'], timeperiod=param, matype=0))
        return ma
    async def _ind_mama(self): raise NotImplementedException('indicator')
    async def _ind_mavp(self): raise NotImplementedException('indicator')
    async def _ind_midpoint(self): raise NotImplementedException('indicator')
    async def _ind_midprice(self): raise NotImplementedException('indicator')
    async def _ind_sar(self): raise NotImplementedException('indicator')
    async def _ind_sarext(self): raise NotImplementedException('indicator')
    async def _ind_sma(self): raise NotImplementedException('indicator')
    async def _ind_t3(self): raise NotImplementedException('indicator')
    async def _ind_tema(self): raise NotImplementedException('indicator')
    async def _ind_trima(self): raise NotImplementedException('indicator')
    async def _ind_wma(self): raise NotImplementedException('indicator')


    # Momentum Indicators
    async def _ind_adx(self): raise NotImplementedException('indicator')
    async def _ind_adxr(self): raise NotImplementedException('indicator')
    async def _ind_apo(self): raise NotImplementedException('indicator')
    async def _ind_aroon(self): raise NotImplementedException('indicator')
    async def _ind_aroonosc(self): raise NotImplementedException('indicator')
    async def _ind_bop(self): raise NotImplementedException('indicator')
    async def _ind_cci(self): raise NotImplementedException('indicator')
    async def _ind_cmo(self): raise NotImplementedException('indicator')
    async def _ind_dx(self): raise NotImplementedException('indicator')
    async def _ind_macd(self):
        upperband, middleband, lowerband = ta.BBANDS(self.current_time_df['close'], 
                                                        timeperiod=self.config['analysis']['params']['bband']['timeperiod'], 
                                                        nbdevup=self.config['analysis']['params']['bband']['nbdevup'], 
                                                        nbdevdn=self.config['analysis']['params']['bband']['nbdevdn'], 
                                                        matype=0) # No config option for matype yet!
        return {'upper':list(upperband), 'middle': list(middleband), 'lower':list(lowerband)}
    async def _ind_macdext(self): raise NotImplementedException('indicator')
    async def _ind_macdfix(self): raise NotImplementedException('indicator')
    async def _ind_mfi(self): raise NotImplementedException('indicator')
    async def _ind_minus_di(self): raise NotImplementedException('indicator')
    async def _ind_minus_dm(self): raise NotImplementedException('indicator')
    async def _ind_mom(self): raise NotImplementedException('indicator')
    async def _ind_plus_di(self): raise NotImplementedException('indicator')
    async def _ind_plus_dm(self): raise NotImplementedException('indicator')
    async def _ind_ppo(self): raise NotImplementedException('indicator')
    async def _ind_roc(self): raise NotImplementedException('indicator')
    async def _ind_rocp(self): raise NotImplementedException('indicator')
    async def _ind_rocr(self): raise NotImplementedException('indicator')
    async def _ind_rocr100(self): raise NotImplementedException('indicator')
    async def _ind_rsi(self): raise NotImplementedException('indicator')
    async def _ind_stoch(self): raise NotImplementedException('indicator')
    async def _ind_stochhf(self): raise NotImplementedException('indicator')
    async def _ind_stochrsi(self): raise NotImplementedException('indicator')
    async def _ind_trix(self): raise NotImplementedException('indicator')
    async def _ind_ultosc(self): raise NotImplementedException('indicator')
    async def _ind_willr(self): raise NotImplementedException('indicator')

    # Volume indicators
    # Volatility indicators
    # Price Transform
    # Cycle Indicators
    # Pattern Recognition
    # Statistic Functions