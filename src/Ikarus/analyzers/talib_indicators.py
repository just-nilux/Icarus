import talib as ta
from ..exceptions import NotImplementedException
import numpy as np

    
class TALibIndicators():
    async def _ind_bband(self, candlesticks, **kwargs):
        upperband, middleband, lowerband = ta.BBANDS(candlesticks['close'], **kwargs)
        return {'upper':list(upperband), 'middle': list(middleband), 'lower':list(lowerband)}
    async def _ind_dema(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_ema(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_ht_trendline(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_kama(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_ma(self, candlesticks, **kwargs): return list(ta.MA(candlesticks['close'], **kwargs))
    async def _ind_mama(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_mavp(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_midpoint(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_midprice(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_sar(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_sarext(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_sma(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_t3(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_tema(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_trima(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_wma(self, candlesticks, **kwargs): raise NotImplementedException('indicator')


    # Momentum Indicators
    async def _ind_adx(self, candlesticks, **kwargs): return list(ta.ADX(candlesticks['high'], candlesticks['low'], candlesticks['close'], **kwargs))
    async def _ind_adxr(self, candlesticks, **kwargs): return list(ta.ADXR(candlesticks['high'], candlesticks['low'], candlesticks['close'], **kwargs))
    async def _ind_apo(self, candlesticks, **kwargs): return list(ta.APO(candlesticks['high'], **kwargs))
    async def _ind_aroon(self, candlesticks, **kwargs): 
        aroondown, aroonup = ta.AROON(candlesticks['high'], candlesticks['low'], **kwargs)
        return {'aroonup':list(aroonup), 'aroondown': list(aroondown)}
    async def _ind_aroonosc(self, candlesticks, **kwargs): return list(ta.AROONOSC(candlesticks['high'], candlesticks['low'], **kwargs))
    async def _ind_bop(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_cci(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_cmo(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_dx(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_macd(self, candlesticks, **kwargs):
        macd, macdsignal, macdhist = ta.MACD(candlesticks['close'], **kwargs)
        return {'macd':list(macd), 'macdsignal': list(macdsignal), 'macdhist':list(macdhist)}
    async def _ind_macdext(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_macdfix(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_mfi(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_minus_di(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_minus_dm(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_mom(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_plus_di(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_plus_dm(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_ppo(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_roc(self, candlesticks, **kwargs): return list(ta.ROC(candlesticks['close'], **kwargs))
    async def _ind_rocp(self, candlesticks, **kwargs): return list(ta.ROCP(candlesticks['close'], **kwargs))
    async def _ind_rocr(self, candlesticks, **kwargs): return list(ta.ROCR(candlesticks['close'], **kwargs))
    async def _ind_rocr100(self, candlesticks, **kwargs): return list(ta.ROCR100(candlesticks['close'], **kwargs))
    async def _ind_rsi(self, candlesticks, **kwargs): 
        return list(ta.RSI(candlesticks['close'], **kwargs))
    async def _ind_stoch(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_stochhf(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_stochrsi(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_trix(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_ultosc(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_willr(self, candlesticks, **kwargs): raise NotImplementedException('indicator')


    # Volume indicators
    async def _ind_ad(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_adosc(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_obv(self, candlesticks, **kwargs): return list(ta.OBV(candlesticks['close'], candlesticks['volume']))


    # Volatility indicators
    async def _ind_atr(self, candlesticks, **kwargs): return list(ta.ATR( candlesticks['high'],  candlesticks['low'],  candlesticks['close']))
    async def _ind_natr(self, candlesticks, **kwargs): return list(ta.NATR( candlesticks['high'],  candlesticks['low'],  candlesticks['close']))
    async def _ind_trange(self, candlesticks, **kwargs): return list(ta.TRANGE( candlesticks['high'],  candlesticks['low'],  candlesticks['close']))


    # Price Transform
    async def _ind_avgprice(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_medprice(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_typprice(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_wclprice(self, candlesticks, **kwargs): raise NotImplementedException('indicator')


    # Cycle Indicators
    async def _ind_ht_dcperiod(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_ht_dcphase(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_ht_phasor(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_sine(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_trendmode(self, candlesticks, **kwargs): raise NotImplementedException('indicator')


    # Pattern Recognition
    async def _pat_trendmode(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdl2crows(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdl3blackcrows(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdl3inside(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdl3linestrike(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdl3outside(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdl3starsinsouth(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdl3whitesoldiers(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlabandonedbaby(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdladvanceblock(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlbelthold(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlbreakaway(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_closingmarubozu(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlconcealbabyswall(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlcounterattack(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdldarkcloudcover(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdldoji(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdldojistart(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdldragonflydoji(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlenfulging(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdleveningdojistar(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdleveningstar(self, candlesticks, **kwargs):
        # TODO: Optimize the logic
        flags = list(ta.CDLEVENINGSTAR(candlesticks['open'], candlesticks['high'], candlesticks['low'], candlesticks['close'], penetration=0))
        indices = np.where(np.array(flags) != 0)[0]
        result = [None]*len(flags)
        for idx in indices:
            # NOTE: The pattern has the length 3. Thus the returned values are the index that the pattern completed
            #       Thus, the star is the 2nd point in the patter which is 'idx-1'
            result[idx-1] = candlesticks['high'].iloc[idx-1]
        return result
    async def _pat_cdlgapsidesidewhite(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlgravestonedoji(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlhammer(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlhanginman(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlharami(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlharamicross(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlhighwave(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlhikkake(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlhikkakemod(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlhomingpigeon(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlidentical3crows(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlinneck(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlinvertedhammer(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlkicking(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlkickingbylength(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlladderbottom(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdllongleggeddoji(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdllongline(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlmarubozu(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlmatchinglow(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlmathold(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlmorningdojistar(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlmorningstar(self, candlesticks, **kwargs):
        # TODO: Optimize the logic
        flags = list(ta.CDLMORNINGSTAR(candlesticks['open'], candlesticks['high'], candlesticks['low'], candlesticks['close'], penetration=0))
        indices = np.where(np.array(flags) != 0)[0]
        result = [None]*len(flags)
        for idx in indices:
            # NOTE: The pattern has the length 3. Thus the returned values are the index that the pattern completed
            #       Thus, the star is the 2nd point in the patter which is 'idx-1'
            result[idx-1] = candlesticks['low'].iloc[idx-1]
        return result
    async def _pat_cdlonneck(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlpiercing(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlrickshawman(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlrisefall3methods(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlseparatinglines(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlshootingstar(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlshortline(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlspinningtop(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlstalledpattern(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlsticksandwich(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdltakuri(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdltasukigap(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlthrusting(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdltristar(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlunique3river(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlupsidegap2crows(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlxsidegap3methods(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
