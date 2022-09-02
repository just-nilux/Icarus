import talib as ta
from ..exceptions import NotImplementedException
import numpy as np

    
class TALibIndicators():
    async def _bband(self, candlesticks, **kwargs):
        upperband, middleband, lowerband = ta.BBANDS(candlesticks['close'], **kwargs)
        return {'upper':list(upperband), 'middle': list(middleband), 'lower':list(lowerband)}
    async def _dema(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ema(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ht_trendline(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _kama(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ma(self, candlesticks, **kwargs): return list(ta.MA(candlesticks['close'], **kwargs))
    async def _mama(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _mavp(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _midpoint(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _midprice(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _sar(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _sarext(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _sma(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _t3(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _tema(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _trima(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _wma(self, candlesticks, **kwargs): raise NotImplementedException('indicator')


    # Momentum Indicators
    async def _adx(self, candlesticks, **kwargs): return list(ta.ADX(candlesticks['high'], candlesticks['low'], candlesticks['close'], **kwargs))
    async def _adxr(self, candlesticks, **kwargs): return list(ta.ADXR(candlesticks['high'], candlesticks['low'], candlesticks['close'], **kwargs))
    async def _apo(self, candlesticks, **kwargs): return list(ta.APO(candlesticks['high'], **kwargs))
    async def _aroon(self, candlesticks, **kwargs): 
        aroondown, aroonup = ta.AROON(candlesticks['high'], candlesticks['low'], **kwargs)
        return {'aroonup':list(aroonup), 'aroondown': list(aroondown)}
    async def _aroonosc(self, candlesticks, **kwargs): return list(ta.AROONOSC(candlesticks['high'], candlesticks['low'], **kwargs))
    async def _bop(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cci(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cmo(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _dx(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _macd(self, candlesticks, **kwargs):
        macd, macdsignal, macdhist = ta.MACD(candlesticks['close'], **kwargs)
        return {'macd':list(macd), 'macdsignal': list(macdsignal), 'macdhist':list(macdhist)}
    async def _macdext(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _macdfix(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _mfi(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _minus_di(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _minus_dm(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _mom(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _plus_di(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _plus_dm(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ppo(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _roc(self, candlesticks, **kwargs): return list(ta.ROC(candlesticks['close'], **kwargs))
    async def _rocp(self, candlesticks, **kwargs): return list(ta.ROCP(candlesticks['close'], **kwargs))
    async def _rocr(self, candlesticks, **kwargs): return list(ta.ROCR(candlesticks['close'], **kwargs))
    async def _rocr100(self, candlesticks, **kwargs): return list(ta.ROCR100(candlesticks['close'], **kwargs))
    async def _rsi(self, candlesticks, **kwargs): 
        return list(ta.RSI(candlesticks['close'], **kwargs))
    async def _stoch(self, candlesticks, **kwargs):
        slowk, slowd = ta.STOCH(candlesticks['high'], candlesticks['low'], candlesticks['close'], **kwargs)
        return {'slowk':list(slowk), 'slowd': list(slowd)}
    async def _stochf(self, candlesticks, **kwargs):
        fastk, fastd = ta.STOCHF(candlesticks['high'], candlesticks['low'], candlesticks['close'], **kwargs)
        return {'fastk':list(fastk), 'fastd': list(fastd)}
    async def _stochrsi(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _trix(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ultosc(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _willr(self, candlesticks, **kwargs): raise NotImplementedException('indicator')


    # Volume indicators
    async def _ad(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _adosc(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _obv(self, candlesticks, **kwargs): return list(ta.OBV(candlesticks['close'], candlesticks['volume']))


    # Volatility indicators
    async def _atr(self, candlesticks, **kwargs): return list(ta.ATR( candlesticks['high'],  candlesticks['low'],  candlesticks['close']))
    async def _natr(self, candlesticks, **kwargs): return list(ta.NATR( candlesticks['high'],  candlesticks['low'],  candlesticks['close']))
    async def _trange(self, candlesticks, **kwargs): return list(ta.TRANGE( candlesticks['high'],  candlesticks['low'],  candlesticks['close']))


    # Price Transform
    async def _avgprice(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _medprice(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _typprice(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _wclprice(self, candlesticks, **kwargs): raise NotImplementedException('indicator')


    # Cycle Indicators
    async def _ht_dcperiod(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ht_dcphase(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ht_phasor(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _sine(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _trendmode(self, candlesticks, **kwargs): raise NotImplementedException('indicator')


    # Pattern Recognition
    async def _trendmode(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdl2crows(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdl3blackcrows(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdl3inside(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdl3linestrike(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdl3outside(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdl3starsinsouth(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdl3whitesoldiers(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlabandonedbaby(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdladvanceblock(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlbelthold(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlbreakaway(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _closingmarubozu(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlconcealbabyswall(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlcounterattack(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdldarkcloudcover(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdldoji(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdldojistart(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdldragonflydoji(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlenfulging(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdleveningdojistar(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdleveningstar(self, candlesticks, **kwargs):
        # TODO: Optimize the logic
        flags = list(ta.CDLEVENINGSTAR(candlesticks['open'], candlesticks['high'], candlesticks['low'], candlesticks['close'], penetration=0))
        indices = np.where(np.array(flags) != 0)[0]
        result = [None]*len(flags)
        for idx in indices:
            # NOTE: The pattern has the length 3. Thus the returned values are the index that the pattern completed
            #       Thus, the star is the 2nd point in the patter which is 'idx-1'
            result[idx-1] = candlesticks['high'].iloc[idx-1]
        return result
    async def _cdlgapsidesidewhite(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlgravestonedoji(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlhammer(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlhanginman(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlharami(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlharamicross(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlhighwave(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlhikkake(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlhikkakemod(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlhomingpigeon(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlidentical3crows(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlinneck(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlinvertedhammer(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlkicking(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlkickingbylength(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlladderbottom(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdllongleggeddoji(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdllongline(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlmarubozu(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlmatchinglow(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlmathold(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlmorningdojistar(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlmorningstar(self, candlesticks, **kwargs):
        # TODO: Optimize the logic
        flags = list(ta.CDLMORNINGSTAR(candlesticks['open'], candlesticks['high'], candlesticks['low'], candlesticks['close'], penetration=0))
        indices = np.where(np.array(flags) != 0)[0]
        result = [None]*len(flags)
        for idx in indices:
            # NOTE: The pattern has the length 3. Thus the returned values are the index that the pattern completed
            #       Thus, the star is the 2nd point in the patter which is 'idx-1'
            result[idx-1] = candlesticks['low'].iloc[idx-1]
        return result
    async def _cdlonneck(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlpiercing(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlrickshawman(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlrisefall3methods(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlseparatinglines(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlshootingstar(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlshortline(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlspinningtop(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlstalledpattern(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlsticksandwich(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdltakuri(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdltasukigap(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlthrusting(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdltristar(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlunique3river(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlupsidegap2crows(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _cdlxsidegap3methods(self, candlesticks, **kwargs): raise NotImplementedException('indicator')
