import talib as ta
import pandas as pd


class Indicators():

    async def _fractal_aroon(self, candlesticks, **kwargs):
        fractal_line = await self._fractal_line_3(candlesticks)
        aroondown, aroonup = ta.AROON(pd.Series(fractal_line['bearish']), pd.Series(fractal_line['bullish']), **kwargs)
        return {'aroonup':list(aroonup), 'aroondown': list(aroondown)}

    async def _fractal_aroonosc(self, candlesticks, **kwargs):
        fractal_line = await self._fractal_line_3(candlesticks) 
        return list(ta.AROONOSC(pd.Series(fractal_line['bearish']), pd.Series(fractal_line['bullish']), **kwargs))

    async def _fractal_line_3(self, candlesticks, **kwargs):
        # TODO: Decide what to use: bfill or ffill
        bearish_frac = list(pd.Series(await self._bearish_fractal_3(candlesticks)).bfill().ffill())
        bullish_frac = list(pd.Series(await self._bullish_fractal_3(candlesticks)).bfill().ffill())
        return {'bearish':bearish_frac, 'bullish':bullish_frac}

    async def _low(self, candlesticks, **kwargs): return list(candlesticks['low'])
    async def _high(self, candlesticks, **kwargs): return list(candlesticks['high'])
    async def _llow(self, candlesticks, **kwargs): return candlesticks['low'].min()
    async def _hhigh(self, candlesticks, **kwargs): return candlesticks['high'].max()
    async def _last_close(self, candlesticks, **kwargs): return float(candlesticks['close'].tail(1))
    async def _close(self, candlesticks, **kwargs): return list(candlesticks['close'])
    async def _open(self, candlesticks, **kwargs): return list(candlesticks['open'])
    async def _index(self, candlesticks, **kwargs): return list(candlesticks.index)


    async def _percentage_possible_change(self, candlesticks, **kwargs):
        timeperiod = kwargs.get('timeperiod',24)
        digit = kwargs.get('digit',3)

        # TODO: FIX THE WARNINGS
        df = candlesticks[['open', 'high', 'low']]
        df['index'] = df.index
        df.reset_index()
        df.set_index(df['index'].astype('int64').astype('datetime64[ms]'), inplace=True)
        del df['index']


        df['high'] = df['high'].rolling(window=timeperiod).apply(max)
        df['low'] = df['low'].rolling(window=timeperiod).apply(min)
        df[['high','low']] = df[['high','low']].shift(-timeperiod+1)
        df.dropna(inplace=True)

        df['pos_change'] = round(df['high']/df['open'] - 1, 3)
        df['neg_change'] = round(df['low']/df['open'] - 1, 3)
        df.drop(['open', 'high', 'low'], axis=1, inplace=True)

        return df

    async def _parallel_ma(self, candlesticks, **kwargs): 
        parallel_ma = {}
        for kwarg in kwargs:
            parallel_ma[kwarg['timeperiod']] = list(ta.MA(candlesticks['close'], **kwarg))
        return parallel_ma

    async def _rvol(self, candlesticks, **kwargs):
        '''
        The logic:
        - Compare the volume of 13:00 on 1h timeframe by using the average of last x day
        - Compare the volume of 13:15 on 15m timeframe by using the average of last x day
        
        The reason why the period is taken as a day is because of the human perception for dividing time is based on days.
        Ofcourse in the timeframes like 1d we can check the Monthly or weekly patterns if exists
           
        For 1h timeframe the ts diff is 3600sec
        There are 86400 secondds in a day

        Lets say that this indicator is only valid for timeframes less than a day
        '''
        # Get current timeframe:
        diff_in_ms = int((candlesticks.index[1]-candlesticks.index[0]))
        ms_in_day = 86400000

        if ms_in_day <= diff_in_ms:
            return []
        
        rvol_df = pd.DataFrame(index=candlesticks.index, columns=['rvol'])
        for ms_delta in range(0,ms_in_day,diff_in_ms):
            test = candlesticks['volume'].iloc[(candlesticks.index % ms_in_day) - ms_delta == 0] # For 1h
            ma_volume_test = test.rolling(kwargs.get('period',10)).mean()
            rvol_df['rvol'].loc[test.index] = (test/ma_volume_test).round(2)

        return list(rvol_df['rvol'])

    def mkfi_categorizer(mkfi_diff_sign, volume_diff_sign): # Market Facilitation Index
        '''
            1: green
            2: fade_brown
            3: fake_blue
            4: squat_pink
        '''
        if mkfi_diff_sign:
            if volume_diff_sign:
                return 1
            else:
                return 3
        else:
            if volume_diff_sign:
                return 4
            else:
                return 2

    async def _mkfi(self, candlesticks, **kwargs): # Market Facilitation Index
        mkfi = pd.DataFrame(index=candlesticks.index)
        mkfi['mkfi'] = (candlesticks['high'] - candlesticks['low']) / candlesticks['volume']
        mkfi['mkfi_diff_sign'] = mkfi.diff() > 0
        mkfi['volume_diff_sign'] = candlesticks['volume'].diff() > 0

        mkfi['tokens'] = mkfi.apply(lambda row: Indicators.mkfi_categorizer(row['mkfi_diff_sign'],row['volume_diff_sign']),axis=1)

        return {'mkfi': mkfi['mkfi'], 'tokens': mkfi['tokens']}


    # Noise Measuring Indicators
    async def _kaufman_efficiency_ratio(self, candlesticks, **kwargs):
        direction = candlesticks['close'].diff(kwargs.get('timeperiod',20)).abs()
        #volatility = pd.rolling_sum(candlesticks['close'].diff().abs(), kwargs.get('timeperiod',20))
        volatility = candlesticks['close'].diff().abs().rolling(kwargs.get('timeperiod',20)).sum()
        return list(direction/volatility)


    async def _price_density(self, candlesticks, **kwargs):
        timeperiod = kwargs.get('timeperiod',20)
        candle_volatility = candlesticks['high'] - candlesticks['low']
        highest_highs = candlesticks['high'].rolling(timeperiod).max()
        lowest_lows = candlesticks['low'].rolling(timeperiod).min()

        price_density = candle_volatility.rolling(timeperiod).sum() / (highest_highs - lowest_lows)
        return list(price_density)