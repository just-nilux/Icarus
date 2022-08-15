import numpy as np

class Patterns():
    async def _pat_bearish_fractal_5(self, candlesticks, **kwargs): return list(np.roll(candlesticks['high'].rolling(5).apply(Patterns.is_resistance), -1))
    async def _pat_bullish_fractal_5(self, candlesticks, **kwargs): return list(np.roll(candlesticks['low'].rolling(5).apply(Patterns.is_support), -1))
    async def _pat_bearish_fractal_3(self, candlesticks, **kwargs): return list(np.roll(candlesticks['high'].rolling(3).apply(Patterns.is_resistance), -1))
    async def _pat_bullish_fractal_3(self, candlesticks, **kwargs): return list(np.roll(candlesticks['low'].rolling(3).apply(Patterns.is_support), -1))

    def is_resistance(serie):
        if len(serie) == 3 and serie.iloc[0] < serie.iloc[1] > serie.iloc[2]:
            return serie.iloc[1]
        elif len(serie) == 5 and serie.iloc[0] < serie.iloc[1] < serie.iloc[2] > serie.iloc[3] > serie.iloc[4]:
            return serie.iloc[2]
        return np.NaN

    def is_support(serie):
        if len(serie) == 3 and serie.iloc[0] > serie.iloc[1] < serie.iloc[2]:
            return serie.iloc[1]
        elif len(serie) == 5 and serie.iloc[0] > serie.iloc[1] > serie.iloc[2] < serie.iloc[3] < serie.iloc[4]:
            return serie.iloc[2]
        return np.NaN
