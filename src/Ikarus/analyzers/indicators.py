import asyncio
import copy
import logging
import talib as ta
from ..exceptions import NotImplementedException
from sklearn.cluster import KMeans, DBSCAN, MeanShift, OPTICS, Birch
import pandas as pd
import numpy as np
from itertools import groupby
from operator import itemgetter
from ..utils import time_scale_to_milisecond
import sys
logger = logging.getLogger('app')

class Indicators():

    async def _ind_market_classifier(candlesticks, **kwargs):
        # TODO: Market status receives the name of some other indicators and runs
        #       a secondary analysis.
        #       Maybe the secondary analysis such as  S/R levels should be put under
        #       another category

        analyzer = "_ind_" + self.analysis_config['indicators']['market_classifier']
        if hasattr(self, analyzer):
            analysis_output = await getattr(self, analyzer)()
        
        classification = {}
        if analyzer == '_ind_aroonosc':
            uptrend_filter = np.where(np.array(analysis_output) > 0)[0]
            downtrend_filter = np.where(np.array(analysis_output) < 0)[0]
            classification = {'downtrend':downtrend_filter, 'uptrend':uptrend_filter}

        elif analyzer == '_ind_fractal_aroon':
            uptrend_filter = np.where(np.nan_to_num(analysis_output['aroonup']) > 80)[0]
            downtrend_filter = np.where(np.nan_to_num(analysis_output['aroondown']) > 80)[0]
            classification = {'downtrend':downtrend_filter, 'uptrend':uptrend_filter}

        ts_index = self.current_time_df.index
        result = {}
        # TODO: Make validation counter generic
        validation_counter = 5
        for class_name, filter_idx in classification.items():
            class_item_list = []
            for k, g in groupby(enumerate(filter_idx), lambda ix: ix[0] - ix[1]):
                seq_idx = list(map(itemgetter(1), g))
                # NOTE: If the sq. length is 1 than it will not be displayed. Apply "seq_idx[-1]+1" if you need to
                #if len(seq_idx) >= validation_counter:
                #    class_item = {'start':ts_index[seq_idx[0]], 'end':ts_index[seq_idx[-1]], 'validation_point':ts_index[seq_idx[0]+validation_counter -1]}
                #    class_item_list.append(class_item)
                class_item = {'start':ts_index[seq_idx[0]], 'end':ts_index[seq_idx[-1]]}
                class_item_list.append(class_item)
            result[class_name] = class_item_list
        '''
        Sample: result
        {
            downtrend:[
                {
                    start_ts:
                    end_ts:
                    validation_point:
                },
                ...
            ]
        }
        '''
        # if last closed candle is in uptrend, then then 'end' parameter wikk be equal to its timestamp
        # so the day_diff will be 1
        result['is_daydiff']=int((self.current_time_df.index[-1] - result['uptrend'][-1]['end'])/time_scale_to_milisecond('1d'))
        result['is_lastidx']=int(analysis_output['aroonup'][-1] > 80)
        return result

    async def _ind_fractal_aroon(candlesticks, **kwargs):
        fractal_line = await self._ind_fractal_line_3()
        aroondown, aroonup = ta.AROON(pd.Series(fractal_line['bearish']), pd.Series(fractal_line['bullish']), timeperiod=25)
        return {'aroonup':list(aroonup), 'aroondown': list(aroondown)}

    async def _ind_fractal_aroonosc(candlesticks, **kwargs):
        fractal_line = await self._ind_fractal_line_3() 
        return list(ta.AROONOSC(pd.Series(fractal_line['bearish']), pd.Series(fractal_line['bullish']), timeperiod=25))

    async def _ind_fractal_line_3(candlesticks, **kwargs):
        bearish_frac = list(pd.Series(await self._pat_bearish_fractal_3()).bfill())
        bullish_frac = list(pd.Series(await self._pat_bullish_fractal_3()).bfill())
        return {'bearish':bearish_frac, 'bullish':bullish_frac}


    async def eval_sup_res_clusters(algorithm, data_points, min_cluster_members, chart_price_range):
        cluster_predictions = algorithm.fit_predict(data_points)
        cls_tokens = np.unique(cluster_predictions)
        sr_levels = []
        for token in cls_tokens:
            # NOTE: Ignore outliers
            if token == -1:
                continue

            indices = np.where(cluster_predictions == token)
            sr_level = {}
            sr_level['centroids'] = data_points[indices].reshape(1,-1)[0].tolist()

            # NOTE: Ignore the cluster if all of the members are 0, or the not enough cluster members
            if not any(sr_level['centroids']) or len(indices[0])<=min_cluster_members:
                continue

            sr_level['validation_point'] = indices[0][min_cluster_members]
            sr_level['min_cluster_members'] = min_cluster_members
            sr_level['horizontal_distribution_score'] = await Indicators.eval_sup_res_cluster_horizontal_score(indices, len(cluster_predictions))
            sr_level['vertical_distribution_score'] = await Indicators.eval_sup_res_cluster_vertical_score(sr_level['centroids'], chart_price_range)

            sr_levels.append(sr_level)
        return sr_levels


    async def eval_sup_res_cluster_horizontal_score(indices, num_of_candle):
        # NOTE: By dividing the indice diferences to len(dbscan_bear), we manage to represent the distance without the dependecy of number of candles:
        weights = list(range(1,len(indices[0])))
        return np.round(np.average(np.diff(indices)[0] / num_of_candle, weights=weights),4)


    async def eval_sup_res_cluster_vertical_score(centroids, chart_price_range):
        cluster_price_range = max(centroids) - min(centroids)
        cluster_price_range_perc = cluster_price_range / chart_price_range
        return np.round(cluster_price_range_perc/len(centroids), 4)


    async def _ind_support_birch(candlesticks, **kwargs):
        source = '_pat_' + kwargs.get('source','bullish_fractal_3')

        bullish_frac = np.nan_to_num(await getattr(self, source)()).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # NOTE: Band of %0.5 unless optimized
        min_samples = max(round(candlesticks.shape[0]/100),3)
        birch = Birch(branching_factor=15, n_clusters = None, threshold=eps)
        return await Indicators.eval_sup_res_clusters(birch, bullish_frac, min_samples, chart_price_range)


    async def _ind_resistance_birch(candlesticks, **kwargs):
        source = '_pat_' + kwargs.get('source','bearish_fractal_3')

        bullish_frac = np.nan_to_num(await getattr(self, source)()).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # NOTE: Band of %0.5 unless optimized
        min_samples = max(round(candlesticks.shape[0]/100),3)
        birch = Birch(branching_factor=15, n_clusters = None, threshold=eps)
        return await Indicators.eval_sup_res_clusters(birch, bullish_frac, min_samples, chart_price_range)


    async def _ind_support_optics(self, candlesticks, **kwargs):
        source = '_pat_' + kwargs.get('source','bullish_fractal_3')
        cluster_method = kwargs.get('cluster_method','xi')   

        bullish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # NOTE: Band of %0.5 unless optimized
        min_samples = max(round(candlesticks.shape[0]/100),3)
        optics = OPTICS(eps=eps, min_samples=min_samples, cluster_method=cluster_method)
        return await Indicators.eval_sup_res_clusters(optics, bullish_frac, optics.min_samples, chart_price_range)


    async def _ind_resistance_optics(candlesticks, **kwargs):
        source = '_pat_' + kwargs.get('source','bearish_fractal_3')
        cluster_method = kwargs.get('cluster_method','xi')   

        bearish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # TODO: Optimize this epsilon value based on volatility or sth else
        min_samples = max(round(candlesticks.shape[0]/100),3)
        optics = OPTICS(eps=eps, min_samples=min_samples, cluster_method=cluster_method)
        return await Indicators.eval_sup_res_clusters(optics, bearish_frac, optics.min_samples, chart_price_range)


    async def _ind_support_dbscan(candlesticks, **kwargs):
        source = '_pat_' + kwargs.get('source','bullish_fractal_3')
        bullish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # NOTE: Band of %0.5 unless optimized
        min_samples = max(round(candlesticks.shape[0]/100),3)
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        return await Indicators.eval_sup_res_clusters(dbscan, bullish_frac, dbscan.min_samples, chart_price_range)


    async def _ind_resistance_dbscan(candlesticks, **kwargs):
        source = '_pat_' + kwargs.get('source','bearish_fractal_3')
        # NOTE: In order to yield validation points, nan values are assigned to 0. 
        #       They are visualized but not in the appeared window        

        bearish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # TODO: Optimize this epsilon value based on volatility or sth else
        min_samples = max(round(candlesticks.shape[0]/100),3)
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        return await Indicators.eval_sup_res_clusters(dbscan, bearish_frac, dbscan.min_samples, chart_price_range)


    async def _ind_support_meanshift(candlesticks, **kwargs):
        source = '_pat_' + kwargs.get('source','bullish_fractal_3')
        min_cluster_members = kwargs.get('min_cluster_members', 3)

        bearish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        bandwidth = float(chart_price_range * 0.01) # TODO: Optimize this epsilon value based on volatility or sth else
        min_samples = max(round(candlesticks.shape[0]/100),3)
        meanshift = MeanShift(bandwidth=bandwidth) 
        
        # TODO: Specifying bandwith halps a bit. I dont know why the estimation did not worked or how it is calculated
        #       Things to improve:
        #       - Min number of members can be added as post filter (seems like does not working well)
        #       - 
        return await Indicators.eval_sup_res_clusters(meanshift, bearish_frac, min_samples, chart_price_range)


    async def _ind_resistance_meanshift(candlesticks, **kwargs):
        source = '_pat_' + kwargs.get('source','bearish_fractal_3')
        min_cluster_members = kwargs.get('min_cluster_members', 3)

        bearish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        bandwidth = float(chart_price_range * 0.005) # TODO: Optimize this epsilon value based on volatility or sth else
        min_samples = max(round(candlesticks.shape[0]/100),3)
        meanshift = MeanShift(bandwidth=bandwidth) # TODO use bandwidth
        return await Indicators.eval_sup_res_clusters(meanshift, bearish_frac, min_samples, chart_price_range)


    async def _ind_support_kmeans(candlesticks, **kwargs):

        source = '_pat_' + kwargs.get('source','bullish_fractal_3')
        min_cluster_members = kwargs.get('min_cluster_members', 3)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        data_points = np.nan_to_num(await getattr(self, source)()).reshape(-1,1)

        km = KMeans(
            n_clusters=5, init='random',
            n_init=13, max_iter=300, 
            tol=1e-04, random_state=0
        )

        return await Indicators.eval_sup_res_clusters(km, data_points, min_cluster_members, chart_price_range)

    async def _ind_resistance_kmeans(candlesticks, **kwargs):
        source = '_pat_' + kwargs.get('source','bearish_fractal_3')
        min_cluster_members = kwargs.get('min_cluster_members', 3)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        data_points = np.nan_to_num(await getattr(self, source)()).reshape(-1,1)

        km = KMeans(
            n_clusters=5, init='random',
            n_init=13, max_iter=300, 
            tol=1e-04, random_state=0
        )

        return await Indicators.eval_sup_res_clusters(km, data_points, min_cluster_members, chart_price_range)

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

    async def _pat_bearish_fractal_5(candlesticks, **kwargs): return list(np.roll(candlesticks['high'].rolling(5).apply(Indicators.is_resistance), -1))
    async def _pat_bullish_fractal_5(candlesticks, **kwargs): return list(np.roll(candlesticks['low'].rolling(5).apply(Indicators.is_support), -1))
    async def _pat_bearish_fractal_3(candlesticks, **kwargs): return list(np.roll(candlesticks['high'].rolling(3).apply(Indicators.is_resistance), -1))
    async def _pat_bullish_fractal_3(candlesticks, **kwargs): return list(np.roll(candlesticks['low'].rolling(3).apply(Indicators.is_support), -1))

    # Custom Indicators
    async def _ind_low(candlesticks, **kwargs): return list(candlesticks['low'])
    async def _ind_high(candlesticks, **kwargs): return list(candlesticks['high'])
    async def _ind_llow(candlesticks, **kwargs): return candlesticks['low'].min()
    async def _ind_hhigh(candlesticks, **kwargs): return candlesticks['high'].max()
    async def _ind_close(self, candlesticks, kwargs): return float(candlesticks['close'].tail(1))
    async def _ind_parallel_ma(candlesticks, **kwargs): 
        parallel_ma = {}
        for kwarg in kwargs:
            parallel_ma[kwarg['timeperiod']] = list(ta.MA(candlesticks['close'], **kwarg))
        return parallel_ma

    #########################################################################################################################################
    # Overlap Studies
    async def _ind_bband(candlesticks, **kwargs):
        upperband, middleband, lowerband = ta.BBANDS(candlesticks['close'], **kwargs)
        return {'upper':list(upperband), 'middle': list(middleband), 'lower':list(lowerband)}
    async def _ind_dema(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_ema(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_ht_trendline(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_kama(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_ma(candlesticks, **kwargs): return list(ta.MA(candlesticks['close'], **kwargs))
    async def _ind_mama(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_mavp(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_midpoint(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_midprice(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_sar(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_sarext(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_sma(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_t3(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_tema(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_trima(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_wma(candlesticks, **kwargs): raise NotImplementedException('indicator')


    # Momentum Indicators
    async def _ind_adx(candlesticks, **kwargs): return list(ta.ADX(candlesticks['high'], candlesticks['low'], candlesticks['close'], **kwargs))
    async def _ind_adxr(candlesticks, **kwargs): return list(ta.ADXR(candlesticks['high'], candlesticks['low'], candlesticks['close'], **kwargs))
    async def _ind_apo(candlesticks, **kwargs): return list(ta.APO(candlesticks['high'], **kwargs))
    async def _ind_aroon(candlesticks, **kwargs): 
        aroondown, aroonup = ta.AROON(candlesticks['high'], candlesticks['low'], **kwargs)
        return {'aroonup':list(aroonup), 'aroondown': list(aroondown)}
    async def _ind_aroonosc(candlesticks, **kwargs): return list(ta.AROONOSC(candlesticks['high'], candlesticks['low'], **kwargs))
    async def _ind_bop(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_cci(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_cmo(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_dx(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_macd(candlesticks, **kwargs):
        macd, macdsignal, macdhist = ta.MACD(candlesticks['close'], **kwargs)
        return {'macd':list(macd), 'macdsignal': list(macdsignal), 'macdhist':list(macdhist)}
    async def _ind_macdext(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_macdfix(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_mfi(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_minus_di(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_minus_dm(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_mom(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_plus_di(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_plus_dm(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_ppo(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_roc(candlesticks, **kwargs): return list(ta.ROC(candlesticks['close'], **kwargs))
    async def _ind_rocp(candlesticks, **kwargs): return list(ta.ROCP(candlesticks['close'], **kwargs))
    async def _ind_rocr(candlesticks, **kwargs): return list(ta.ROCR(candlesticks['close'], **kwargs))
    async def _ind_rocr100(candlesticks, **kwargs): return list(ta.ROCR100(candlesticks['close'], **kwargs))
    async def _ind_rsi(candlesticks, **kwargs): 
        return list(ta.RSI(candlesticks['close'], **kwargs))
    async def _ind_stoch(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_stochhf(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_stochrsi(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_trix(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_ultosc(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_willr(candlesticks, **kwargs): raise NotImplementedException('indicator')


    # Volume indicators
    async def _ind_ad(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_adosc(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_obv(candlesticks, **kwargs): return list(ta.OBV(candlesticks['close'], candlesticks['volume']))


    # Volatility indicators
    async def _ind_atr(candlesticks, **kwargs): return list(ta.ATR( candlesticks['high'],  candlesticks['low'],  candlesticks['close']))
    async def _ind_natr(candlesticks, **kwargs): return list(ta.NATR( candlesticks['high'],  candlesticks['low'],  candlesticks['close']))
    async def _ind_trange(candlesticks, **kwargs): return list(ta.TRANGE( candlesticks['high'],  candlesticks['low'],  candlesticks['close']))


    # Price Transform
    async def _ind_avgprice(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_medprice(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_typprice(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_wclprice(candlesticks, **kwargs): raise NotImplementedException('indicator')


    # Cycle Indicators
    async def _ind_ht_dcperiod(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_ht_dcphase(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_ht_phasor(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_sine(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _ind_trendmode(candlesticks, **kwargs): raise NotImplementedException('indicator')


    # Pattern Recognition
    async def _pat_trendmode(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdl2crows(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdl3blackcrows(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdl3inside(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdl3linestrike(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdl3outside(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdl3starsinsouth(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdl3whitesoldiers(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlabandonedbaby(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdladvanceblock(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlbelthold(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlbreakaway(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_closingmarubozu(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlconcealbabyswall(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlcounterattack(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdldarkcloudcover(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdldoji(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdldojistart(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdldragonflydoji(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlenfulging(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdleveningdojistar(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdleveningstar(candlesticks, **kwargs):
        # TODO: Optimize the logic
        flags = list(ta.CDLEVENINGSTAR(candlesticks['open'], candlesticks['high'], candlesticks['low'], candlesticks['close'], penetration=0))
        indices = np.where(np.array(flags) != 0)[0]
        result = [None]*len(flags)
        for idx in indices:
            # NOTE: The pattern has the length 3. Thus the returned values are the index that the pattern completed
            #       Thus, the star is the 2nd point in the patter which is 'idx-1'
            result[idx-1] = candlesticks['high'].iloc[idx-1]
        return result
    async def _pat_cdlgapsidesidewhite(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlgravestonedoji(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlhammer(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlhanginman(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlharami(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlharamicross(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlhighwave(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlhikkake(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlhikkakemod(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlhomingpigeon(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlidentical3crows(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlinneck(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlinvertedhammer(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlkicking(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlkickingbylength(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlladderbottom(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdllongleggeddoji(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdllongline(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlmarubozu(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlmatchinglow(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlmathold(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlmorningdojistar(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlmorningstar(candlesticks, **kwargs):
        # TODO: Optimize the logic
        flags = list(ta.CDLMORNINGSTAR(candlesticks['open'], candlesticks['high'], candlesticks['low'], candlesticks['close'], penetration=0))
        indices = np.where(np.array(flags) != 0)[0]
        result = [None]*len(flags)
        for idx in indices:
            # NOTE: The pattern has the length 3. Thus the returned values are the index that the pattern completed
            #       Thus, the star is the 2nd point in the patter which is 'idx-1'
            result[idx-1] = candlesticks['low'].iloc[idx-1]
        return result
    async def _pat_cdlonneck(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlpiercing(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlrickshawman(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlrisefall3methods(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlseparatinglines(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlshootingstar(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlshortline(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlspinningtop(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlstalledpattern(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlsticksandwich(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdltakuri(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdltasukigap(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlthrusting(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdltristar(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlunique3river(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlupsidegap2crows(candlesticks, **kwargs): raise NotImplementedException('indicator')
    async def _pat_cdlxsidegap3methods(candlesticks, **kwargs): raise NotImplementedException('indicator')

    # Statistic Functions
    # Not needed