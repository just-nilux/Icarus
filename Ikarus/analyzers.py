import asyncio
import copy
import logging
import talib as ta
from Ikarus.exceptions import NotImplementedException
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score
import pandas as pd
import numpy as np

class Analyzer():
    """
    The duty of Analyzer class is to provide analysis objects.
    It is configurable via the config file
    Use case does not require multiple instance
    """

    # This initiation may not be needed
    # TODO: Normally lambda functions would be quite useful to have one-liner functions, 
    #       however they are not "awaitable". Thus each one-liner lambda expression should be an awaitable method

    def __init__(self, _config):
        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.config = _config
        self.current_time_df={}
        return


    async def sample_analyzer(self, data_dict):
        analysis_dict=dict()
        for pair,data_obj in data_dict.items():
            analysis_obj = dict()

            for time_scale, time_df in data_obj.items():
                self.current_time_df = copy.deepcopy(time_df)

                # Generate coroutines
                indicator_coroutines = []
                header = '_ind_'
                indicator_method_names = list(map(lambda orig_string: header + orig_string, self.config['analysis']['indicators'].keys()))
                for ind in indicator_method_names:
                    if hasattr(self, ind): indicator_coroutines.append(getattr(self, ind)())
                    else: raise RuntimeError(f'Unknown indicator: "{ind}"')

                analysis_output = list(await asyncio.gather(*indicator_coroutines))

                # NOTE: Since coroutines are not reuseable, they require to be created in each cycle
                # NOTE: pd.Series needs to be casted to list
                stats = dict()
                for key, value in zip(self.config['analysis']['indicators'].keys(), analysis_output):
                    stats[key] = value
                # Assign "stats" to each "time_scale"
                analysis_obj[time_scale] = stats

            analysis_dict[pair] = analysis_obj

        return analysis_dict


    async def visual_analysis(self, data_dict):
        analysis_dict=dict()
        for pair,data_obj in data_dict.items():
            analysis_obj = dict()

            for time_scale, time_df in data_obj.items():
                self.current_time_df = copy.deepcopy(time_df)

                # Generate coroutines
                indicator_coroutines = []
                header = '_ind_'
                indicator_method_names = list(map(lambda orig_string: header + orig_string, self.config['visualization']['indicators'].keys()))
                for ind in indicator_method_names:
                    if hasattr(self, ind): indicator_coroutines.append(getattr(self, ind)())
                    else: raise RuntimeError(f'Unknown indicator: "{ind}"')

                header = '_pat_'
                pattern_method_names = list(map(lambda orig_string: header + orig_string, self.config['visualization']['patterns'])) # Patterns do not take arg
                for pat in pattern_method_names:
                    if hasattr(self, pat): indicator_coroutines.append(getattr(self, pat)())
                    else: raise RuntimeError(f'Unknown pattern: "{pat}"')

                analysis_output = list(await asyncio.gather(*indicator_coroutines))

                # NOTE: Since coroutines are not reuseable, they require to be created in each cycle
                # NOTE: pd.Series needs to be casted to list
                stats = dict()
                for key, value in zip(list(self.config['visualization']['indicators'].keys()) + self.config['visualization']['patterns'], analysis_output):
                    stats[key] = value
                # Assign "stats" to each "time_scale"
                analysis_obj[time_scale] = stats

            analysis_dict[pair] = analysis_obj

        return analysis_dict


    # Analyzers
    async def _ind_support_dbscan(self):
        bullish_frac = np.array(await self._pat_bullish_fractal_3())
        bullish_frac = bullish_frac[~np.isnan(bullish_frac)].reshape(-1,1)

        # Perform unidimentional clustering     
        eps = float(max(bullish_frac)* 0.005) # NOTE: Band of %0.5 unless optimized
        dbscan = DBSCAN(eps=eps, min_samples=3) # It requires at least 3 point to call a cluster a region of s/r

        dbscan_bull = dbscan.fit_predict(bullish_frac)
        cls_tokens = np.unique(dbscan_bull)
        bullish_centroids = []
        for token in cls_tokens:
            if token != -1:
                bullish_centroids.append(bullish_frac[np.where(dbscan_bull == token)].reshape(1,-1)[0].tolist())
        return bullish_centroids

    async def _ind_resistance_dbscan(self):

        bearish_frac = np.array(await self._pat_bearish_fractal_3())
        bearish_frac = bearish_frac[~np.isnan(bearish_frac)].reshape(-1,1)

        # Perform unidimentional clustering     
        eps = float(max(bearish_frac)* 0.005) # NOTE: Band of %0.5 unless optimized
        dbscan = DBSCAN(eps=eps, min_samples=3) # It requires at least 3 point to call a cluster a region of s/r

        dbscan_bear = dbscan.fit_predict(bearish_frac)
        cls_tokens = np.unique(dbscan_bear)
        bearish_centroids = []
        for token in cls_tokens:
            if token != -1:
                bearish_centroids.append(bearish_frac[np.where(dbscan_bear == token)].reshape(1,-1)[0].tolist())

        return bearish_centroids

    async def _ind_kmeans(self):
        # Obtain the (time,high) and (time,low) pairs and merge
        lows = np.array(self.current_time_df['low']).reshape(-1,1)
        highs = np.array(self.current_time_df['high']).reshape(-1,1)

        # Perform unidimentional clustering     
        km = KMeans(
            n_clusters=5, init='random',
            n_init=13, max_iter=300, 
            tol=1e-04, random_state=0
        )
        # TODO: Filter out the anomalies

        # Low Cluster
        y_km = km.fit_predict(lows)
        low_clusters = km.cluster_centers_[:,0]
        cls_tokens = np.unique(y_km)
        cls_centroids = []
        for token in cls_tokens:
            cls_centroids.append(lows[np.where(y_km == token)].reshape(1,-1)[0].tolist())
    
        # High Cluster
        y_km = km.fit_predict(highs)
        high_clusters = km.cluster_centers_[:,0]
        high_cls_tokens = np.unique(y_km)
        high_cls_centroids = []
        for token in high_cls_tokens:
            high_cls_centroids.append(highs[np.where(y_km == token)].reshape(1,-1)[0].tolist())
    
        return {'high_cls':high_cls_centroids, 'low_cls':cls_centroids}

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

    async def _pat_bearish_fractal(self): return list(np.roll(self.current_time_df['high'].rolling(5).apply(Analyzer.is_resistance), -1))
    async def _pat_bullish_fractal(self): return list(np.roll(self.current_time_df['low'].rolling(5).apply(Analyzer.is_support), -1))
    async def _pat_bearish_fractal_3(self): return list(np.roll(self.current_time_df['high'].rolling(3).apply(Analyzer.is_resistance), -1))
    async def _pat_bullish_fractal_3(self): return list(np.roll(self.current_time_df['low'].rolling(3).apply(Analyzer.is_support), -1))

    # Custom Indicators
    async def _ind_low(self): return list(self.current_time_df['low'])
    async def _ind_high(self): return list(self.current_time_df['high'])
    async def _ind_llow(self): return self.current_time_df['low'].min()
    async def _ind_hhigh(self): return self.current_time_df['high'].max()
    async def _ind_close(self): return float(self.current_time_df['close'].tail(1))
    # TODO: Find a way to standardize the low/high/close

    # Overlap Studies
    async def _ind_bband(self):
        upperband, middleband, lowerband = ta.BBANDS(self.current_time_df['close'], 
                                                        timeperiod=self.config['analysis']['indicators']['bband']['timeperiod'], 
                                                        nbdevup=self.config['analysis']['indicators']['bband']['nbdevup'], 
                                                        nbdevdn=self.config['analysis']['indicators']['bband']['nbdevdn'], 
                                                        matype=0) # No config option for matype yet!
        return {'upper':list(upperband), 'middle': list(middleband), 'lower':list(lowerband)}
    async def _ind_dema(self): raise NotImplementedException('indicator')
    async def _ind_ema(self): raise NotImplementedException('indicator')
    async def _ind_ht_trendline(self): raise NotImplementedException('indicator')
    async def _ind_kama(self): raise NotImplementedException('indicator')
    async def _ind_ma(self):
        ma = {}
        for param in self.config['analysis']['indicators']['ma']:
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
        macd, macdsignal, macdhist = ta.MACD(self.current_time_df['close'], fastperiod=12, slowperiod=26, signalperiod=9)
        return {'macd':list(macd), 'macdsignal': list(macdsignal), 'macdhist':list(macdhist)}
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
    async def _ind_rsi(self): return list(ta.RSI(self.current_time_df['close'], timeperiod=14))
    async def _ind_stoch(self): raise NotImplementedException('indicator')
    async def _ind_stochhf(self): raise NotImplementedException('indicator')
    async def _ind_stochrsi(self): raise NotImplementedException('indicator')
    async def _ind_trix(self): raise NotImplementedException('indicator')
    async def _ind_ultosc(self): raise NotImplementedException('indicator')
    async def _ind_willr(self): raise NotImplementedException('indicator')


    # Volume indicators
    async def _ind_ad(self): raise NotImplementedException('indicator')
    async def _ind_adosc(self): raise NotImplementedException('indicator')
    async def _ind_obv(self): return list(ta.OBV(self.current_time_df['close'], self.current_time_df['volume']))


    # Volatility indicators
    async def _ind_atr(self): raise NotImplementedException('indicator')
    async def _ind_natr(self): return list(ta.NATR( self.current_time_df['high'],  self.current_time_df['low'],  self.current_time_df['close']))
    async def _ind_trange(self): return list(ta.TRANGE( self.current_time_df['high'],  self.current_time_df['low'],  self.current_time_df['close']))


    # Price Transform
    async def _ind_avgprice(self): raise NotImplementedException('indicator')
    async def _ind_medprice(self): raise NotImplementedException('indicator')
    async def _ind_typprice(self): raise NotImplementedException('indicator')
    async def _ind_wclprice(self): raise NotImplementedException('indicator')


    # Cycle Indicators
    async def _ind_ht_dcperiod(self): raise NotImplementedException('indicator')
    async def _ind_ht_dcphase(self): raise NotImplementedException('indicator')
    async def _ind_ht_phasor(self): raise NotImplementedException('indicator')
    async def _ind_sine(self): raise NotImplementedException('indicator')
    async def _ind_trendmode(self): raise NotImplementedException('indicator')


    # Pattern Recognition
    async def _pat_trendmode(self): raise NotImplementedException('indicator')
    async def _pat_cdl2crows(self): raise NotImplementedException('indicator')
    async def _pat_cdl3blackcrows(self): raise NotImplementedException('indicator')
    async def _pat_cdl3inside(self): raise NotImplementedException('indicator')
    async def _pat_cdl3linestrike(self): raise NotImplementedException('indicator')
    async def _pat_cdl3outside(self): raise NotImplementedException('indicator')
    async def _pat_cdl3starsinsouth(self): raise NotImplementedException('indicator')
    async def _pat_cdl3whitesoldiers(self): raise NotImplementedException('indicator')
    async def _pat_cdlabandonedbaby(self): raise NotImplementedException('indicator')
    async def _pat_cdladvanceblock(self): raise NotImplementedException('indicator')
    async def _pat_cdlbelthold(self): raise NotImplementedException('indicator')
    async def _pat_cdlbreakaway(self): raise NotImplementedException('indicator')
    async def _pat_closingmarubozu(self): raise NotImplementedException('indicator')
    async def _pat_cdlconcealbabyswall(self): raise NotImplementedException('indicator')
    async def _pat_cdlcounterattack(self): raise NotImplementedException('indicator')
    async def _pat_cdldarkcloudcover(self): raise NotImplementedException('indicator')
    async def _pat_cdldoji(self): raise NotImplementedException('indicator')
    async def _pat_cdldojistart(self): raise NotImplementedException('indicator')
    async def _pat_cdldragonflydoji(self): raise NotImplementedException('indicator')
    async def _pat_cdlenfulging(self): raise NotImplementedException('indicator')
    async def _pat_cdleveningdojistar(self): raise NotImplementedException('indicator')
    async def _pat_cdleveningstar(self):
        # TODO: Optimize the logic
        flags = list(ta.CDLEVENINGSTAR(self.current_time_df['open'], self.current_time_df['high'], self.current_time_df['low'], self.current_time_df['close'], penetration=0))
        indices = np.where(np.array(flags) != 0)[0]
        result = [None]*len(flags)
        for idx in indices:
            # NOTE: The pattern has the length 3. Thus the returned values are the index that the pattern completed
            #       Thus, the star is the 2nd point in the patter which is 'idx-1'
           result[idx-1] = self.current_time_df['high'].iloc[idx-1]
        return result
    async def _pat_cdlgapsidesidewhite(self): raise NotImplementedException('indicator')
    async def _pat_cdlgravestonedoji(self): raise NotImplementedException('indicator')
    async def _pat_cdlhammer(self): raise NotImplementedException('indicator')
    async def _pat_cdlhanginman(self): raise NotImplementedException('indicator')
    async def _pat_cdlharami(self): raise NotImplementedException('indicator')
    async def _pat_cdlharamicross(self): raise NotImplementedException('indicator')
    async def _pat_cdlhighwave(self): raise NotImplementedException('indicator')
    async def _pat_cdlhikkake(self): raise NotImplementedException('indicator')
    async def _pat_cdlhikkakemod(self): raise NotImplementedException('indicator')
    async def _pat_cdlhomingpigeon(self): raise NotImplementedException('indicator')
    async def _pat_cdlidentical3crows(self): raise NotImplementedException('indicator')
    async def _pat_cdlinneck(self): raise NotImplementedException('indicator')
    async def _pat_cdlinvertedhammer(self): raise NotImplementedException('indicator')
    async def _pat_cdlkicking(self): raise NotImplementedException('indicator')
    async def _pat_cdlkickingbylength(self): raise NotImplementedException('indicator')
    async def _pat_cdlladderbottom(self): raise NotImplementedException('indicator')
    async def _pat_cdllongleggeddoji(self): raise NotImplementedException('indicator')
    async def _pat_cdllongline(self): raise NotImplementedException('indicator')
    async def _pat_cdlmarubozu(self): raise NotImplementedException('indicator')
    async def _pat_cdlmatchinglow(self): raise NotImplementedException('indicator')
    async def _pat_cdlmathold(self): raise NotImplementedException('indicator')
    async def _pat_cdlmorningdojistar(self): raise NotImplementedException('indicator')
    async def _pat_cdlmorningstar(self):
        # TODO: Optimize the logic
        flags = list(ta.CDLMORNINGSTAR(self.current_time_df['open'], self.current_time_df['high'], self.current_time_df['low'], self.current_time_df['close'], penetration=0))
        indices = np.where(np.array(flags) != 0)[0]
        result = [None]*len(flags)
        for idx in indices:
            # NOTE: The pattern has the length 3. Thus the returned values are the index that the pattern completed
            #       Thus, the star is the 2nd point in the patter which is 'idx-1'
           result[idx-1] = self.current_time_df['low'].iloc[idx-1]
        return result
    async def _pat_cdlonneck(self): raise NotImplementedException('indicator')
    async def _pat_cdlpiercing(self): raise NotImplementedException('indicator')
    async def _pat_cdlrickshawman(self): raise NotImplementedException('indicator')
    async def _pat_cdlrisefall3methods(self): raise NotImplementedException('indicator')
    async def _pat_cdlseparatinglines(self): raise NotImplementedException('indicator')
    async def _pat_cdlshootingstar(self): raise NotImplementedException('indicator')
    async def _pat_cdlshortline(self): raise NotImplementedException('indicator')
    async def _pat_cdlspinningtop(self): raise NotImplementedException('indicator')
    async def _pat_cdlstalledpattern(self): raise NotImplementedException('indicator')
    async def _pat_cdlsticksandwich(self): raise NotImplementedException('indicator')
    async def _pat_cdltakuri(self): raise NotImplementedException('indicator')
    async def _pat_cdltasukigap(self): raise NotImplementedException('indicator')
    async def _pat_cdlthrusting(self): raise NotImplementedException('indicator')
    async def _pat_cdltristar(self): raise NotImplementedException('indicator')
    async def _pat_cdlunique3river(self): raise NotImplementedException('indicator')
    async def _pat_cdlupsidegap2crows(self): raise NotImplementedException('indicator')
    async def _pat_cdlxsidegap3methods(self): raise NotImplementedException('indicator')

    # Statistic Functions
    # Not needed