import talib as ta
import pandas as pd


class Indicators():

    async def _fractal_aroon(self, candlesticks, **kwargs):
        fractal_line = await self._fractal_line_3(candlesticks)
        aroondown, aroonup = ta.AROON(pd.Series(fractal_line['bearish']), pd.Series(fractal_line['bullish']), timeperiod=25)
        return {'aroonup':list(aroonup), 'aroondown': list(aroondown)}

    async def _fractal_aroonosc(self, candlesticks, **kwargs):
        fractal_line = await self._fractal_line_3(candlesticks) 
        return list(ta.AROONOSC(pd.Series(fractal_line['bearish']), pd.Series(fractal_line['bullish']), timeperiod=25))

    async def _fractal_line_3(self, candlesticks, **kwargs):
        bearish_frac = list(pd.Series(await self._bearish_fractal_3(candlesticks)).bfill())
        bullish_frac = list(pd.Series(await self._bullish_fractal_3(candlesticks)).bfill())
        return {'bearish':bearish_frac, 'bullish':bullish_frac}

    async def _low(self, candlesticks, **kwargs): return list(candlesticks['low'])
    async def _high(self, candlesticks, **kwargs): return list(candlesticks['high'])
    async def _llow(self, candlesticks, **kwargs): return candlesticks['low'].min()
    async def _hhigh(self, candlesticks, **kwargs): return candlesticks['high'].max()
    async def _close(self, candlesticks, **kwargs): return float(candlesticks['close'].tail(1))
    async def _parallel_ma(self, candlesticks, **kwargs): 
        parallel_ma = {}
        for kwarg in kwargs:
            parallel_ma[kwarg['timeperiod']] = list(ta.MA(candlesticks['close'], **kwarg))
        return parallel_ma