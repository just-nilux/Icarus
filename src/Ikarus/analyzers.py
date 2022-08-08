import asyncio
import copy
import logging
import talib as ta
from .exceptions import NotImplementedException
from sklearn.cluster import KMeans, DBSCAN, MeanShift
import pandas as pd
import numpy as np
from itertools import groupby
from operator import itemgetter
from .utils import time_scale_to_milisecond

logger = logging.getLogger('app')


class Analyzer():
    """
    The duty of Analyzer class is to provide analysis objects.
    It is configurable via the config file
    Use case does not require multiple instance
    """

    # This initiation may not be needed
    # TODO: Normally lambda functions would be quite useful to have one-liner functions, 
    #       however they are not "awaitable". Thus each one-liner lambda expression should be an awaitable method

    def __init__(self, analysis_config):
        self.analysis_config = analysis_config
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
                indicator_method_names = list(map(lambda orig_string: header + orig_string, self.analysis_config['indicators'].keys()))
                for ind in indicator_method_names:
                    if hasattr(self, ind): indicator_coroutines.append(getattr(self, ind)())
                    else: raise RuntimeError(f'Unknown indicator: "{ind}"')

                analysis_output = list(await asyncio.gather(*indicator_coroutines))

                # NOTE: Since coroutines are not reuseable, they require to be created in each cycle
                # NOTE: pd.Series needs to be casted to list
                stats = dict()
                for key, value in zip(self.analysis_config['indicators'].keys(), analysis_output):
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
                indicator_method_names = list(map(lambda orig_string: header + orig_string, self.analysis_config['indicators'].keys()))
                for ind in indicator_method_names:
                    if hasattr(self, ind): indicator_coroutines.append(getattr(self, ind)())
                    else: raise RuntimeError(f'Unknown indicator: "{ind}"')

                header = '_pat_'
                pattern_method_names = list(map(lambda orig_string: header + orig_string, self.analysis_config['patterns'])) # Patterns do not take arg
                for pat in pattern_method_names:
                    if hasattr(self, pat): indicator_coroutines.append(getattr(self, pat)())
                    else: raise RuntimeError(f'Unknown pattern: "{pat}"')

                analysis_output = list(await asyncio.gather(*indicator_coroutines))

                # NOTE: Since coroutines are not reuseable, they require to be created in each cycle
                # NOTE: pd.Series needs to be casted to list
                stats = dict()
                for key, value in zip(list(self.analysis_config['indicators'].keys()) + self.analysis_config['patterns'], analysis_output):
                    stats[key] = value
                # Assign "stats" to each "time_scale"
                analysis_obj[time_scale] = stats

            analysis_dict[pair] = analysis_obj

        return analysis_dict


    # Analyzers

    async def _ind_market_classifier(self):
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

    async def _ind_fractal_aroon(self):
        fractal_line = await self._ind_fractal_line_3()
        aroondown, aroonup = ta.AROON(pd.Series(fractal_line['bearish']), pd.Series(fractal_line['bullish']), timeperiod=25)
        return {'aroonup':list(aroonup), 'aroondown': list(aroondown)}

    async def _ind_fractal_aroonosc(self):
        fractal_line = await self._ind_fractal_line_3() 
        return list(ta.AROONOSC(pd.Series(fractal_line['bearish']), pd.Series(fractal_line['bullish']), timeperiod=25))

    async def _ind_fractal_line_3(self):
        bearish_frac = list(pd.Series(await self._pat_bearish_fractal_3()).bfill())
        bullish_frac = list(pd.Series(await self._pat_bullish_fractal_3()).bfill())
        return {'bearish':bearish_frac, 'bullish':bullish_frac}

    async def _ind_support_dbscan(self):
        source = '_pat_' + self.analysis_config['indicators']['support_dbscan']['source']
        bullish_frac = np.nan_to_num(await getattr(self, source)()).reshape(-1,1)
        chart_price_range = self.current_time_df['high'].max() - self.current_time_df['low'].min()
        eps = float(chart_price_range * 0.005) # NOTE: Band of %0.5 unless optimized
        min_samples = max(round(self.current_time_df.shape[0]/100),3)
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        return await Analyzer.eval_sup_res_clusters(dbscan, bullish_frac, dbscan.min_samples-1, chart_price_range)


    async def _ind_resistance_dbscan(self):
        source = '_pat_' + self.analysis_config['indicators']['resistance_dbscan']['source']
        # NOTE: In order to yield validation points, nan values are assigned to 0. 
        #       They are visualized but not in the appeared window        

        bearish_frac = np.nan_to_num(await getattr(self, source)()).reshape(-1,1)
        chart_price_range = self.current_time_df['high'].max() - self.current_time_df['low'].min()
        eps = float(chart_price_range * 0.005) # TODO: Optimize this epsilon value based on volatility or sth else
        min_samples = max(round(self.current_time_df.shape[0]/100),3)
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        return await Analyzer.eval_sup_res_clusters(dbscan, bearish_frac, dbscan.min_samples-1, chart_price_range)


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
            sr_level['horizontal_distribution_score'] = await Analyzer.eval_sup_res_cluster_horizontal_score(indices, len(cluster_predictions))
            sr_level['vertical_distribution_score'] = await Analyzer.eval_sup_res_cluster_vertical_score(sr_level['centroids'], chart_price_range)

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

    async def _ind_support_meanshift(self):
        source = '_pat_' + self.analysis_config['indicators']['support_meanshift'].get('source','bullish_fractal_3')
        min_cluster_members = self.analysis_config['indicators']['support_meanshift'].get('min_cluster_members', 3)

        bearish_frac = np.nan_to_num(await getattr(self, source)()).reshape(-1,1)
        chart_price_range = self.current_time_df['high'].max() - self.current_time_df['low'].min()
        bandwidth = float(chart_price_range * 0.01) # TODO: Optimize this epsilon value based on volatility or sth else
        min_samples = max(round(self.current_time_df.shape[0]/100),3)
        meanshift = MeanShift(bandwidth=bandwidth) 
        
        # TODO: Specifying bandwith halps a bit. I dont know why the estimation did not worked or how it is calculated
        #       Things to improve:
        #       - Min number of members can be added as post filter (seems like does not working well)
        #       - 
        return await Analyzer.eval_sup_res_clusters(meanshift, bearish_frac, min_samples-1, chart_price_range)


    async def _ind_resistance_meanshift(self):
        source = '_pat_' + self.analysis_config['indicators']['resistance_meanshift'].get('source','bearish_fractal_3')
        min_cluster_members = self.analysis_config['indicators']['resistance_meanshift'].get('min_cluster_members', 3)

        bearish_frac = np.nan_to_num(await getattr(self, source)()).reshape(-1,1)
        chart_price_range = self.current_time_df['high'].max() - self.current_time_df['low'].min()
        bandwidth = float(chart_price_range * 0.005) # TODO: Optimize this epsilon value based on volatility or sth else
        min_samples = max(round(self.current_time_df.shape[0]/100),3)
        meanshift = MeanShift(bandwidth=bandwidth) # TODO use bandwidth
        return await Analyzer.eval_sup_res_clusters(meanshift, bearish_frac, min_samples-1, chart_price_range)


    async def _ind_support_kmeans(self):

        source = '_pat_' + self.analysis_config['indicators']['support_kmeans'].get('source','bullish_fractal_3')
        min_cluster_members = self.analysis_config['indicators']['support_kmeans'].get('min_cluster_members', 3)
        chart_price_range = self.current_time_df['high'].max() - self.current_time_df['low'].min()
        data_points = np.nan_to_num(await getattr(self, source)()).reshape(-1,1)

        km = KMeans(
            n_clusters=5, init='random',
            n_init=13, max_iter=300, 
            tol=1e-04, random_state=0
        )

        return await Analyzer.eval_sup_res_clusters(km, data_points, min_cluster_members, chart_price_range)

    async def _ind_resistance_kmeans(self):
        source = '_pat_' + self.analysis_config['indicators']['resistance_kmeans'].get('source','bearish_fractal_3')
        min_cluster_members = self.analysis_config['indicators']['resistance_kmeans'].get('min_cluster_members', 3)
        chart_price_range = self.current_time_df['high'].max() - self.current_time_df['low'].min()
        data_points = np.nan_to_num(await getattr(self, source)()).reshape(-1,1)

        km = KMeans(
            n_clusters=5, init='random',
            n_init=13, max_iter=300, 
            tol=1e-04, random_state=0
        )

        return await Analyzer.eval_sup_res_clusters(km, data_points, min_cluster_members, chart_price_range)

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

    async def _pat_bearish_fractal_5(self): return list(np.roll(self.current_time_df['high'].rolling(5).apply(Analyzer.is_resistance), -1))
    async def _pat_bullish_fractal_5(self): return list(np.roll(self.current_time_df['low'].rolling(5).apply(Analyzer.is_support), -1))
    async def _pat_bearish_fractal_3(self): return list(np.roll(self.current_time_df['high'].rolling(3).apply(Analyzer.is_resistance), -1))
    async def _pat_bullish_fractal_3(self): return list(np.roll(self.current_time_df['low'].rolling(3).apply(Analyzer.is_support), -1))

    # Custom Indicators
    async def _ind_low(self): return list(self.current_time_df['low'])
    async def _ind_high(self): return list(self.current_time_df['high'])
    async def _ind_llow(self): return self.current_time_df['low'].min()
    async def _ind_hhigh(self): return self.current_time_df['high'].max()
    async def _ind_close(self): return float(self.current_time_df['close'].tail(1))
    async def _ind_parallel_ma(self): 
        parallel_ma = {}
        for kwargs in self.analysis_config['indicators']['parallel_ma']:
            parallel_ma[kwargs['timeperiod']] = list(ta.MA(self.current_time_df['close'], **kwargs))
        return parallel_ma

    #########################################################################################################################################
    # Overlap Studies
    async def _ind_bband(self):
        upperband, middleband, lowerband = ta.BBANDS(self.current_time_df['close'], **self.analysis_config['indicators']['bband'])
        return {'upper':list(upperband), 'middle': list(middleband), 'lower':list(lowerband)}
    async def _ind_dema(self): raise NotImplementedException('indicator')
    async def _ind_ema(self): raise NotImplementedException('indicator')
    async def _ind_ht_trendline(self): raise NotImplementedException('indicator')
    async def _ind_kama(self): raise NotImplementedException('indicator')
    async def _ind_ma(self): return list(ta.MA(self.current_time_df['close'], **self.analysis_config['indicators']['ma']))
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
    async def _ind_adx(self): return list(ta.ADX(self.current_time_df['high'], self.current_time_df['low'], self.current_time_df['close'], **self.analysis_config['indicators']['adx']))
    async def _ind_adxr(self): return list(ta.ADXR(self.current_time_df['high'], self.current_time_df['low'], self.current_time_df['close'], **self.analysis_config['indicators']['adxr']))
    async def _ind_apo(self): return list(ta.APO(self.current_time_df['high'], **self.analysis_config['indicators']['apo']))
    async def _ind_aroon(self): 
        aroondown, aroonup = ta.AROON(self.current_time_df['high'], self.current_time_df['low'], **self.analysis_config['indicators']['aroon'])
        return {'aroonup':list(aroonup), 'aroondown': list(aroondown)}
    async def _ind_aroonosc(self): return list(ta.AROONOSC(self.current_time_df['high'], self.current_time_df['low'], **self.analysis_config['indicators']['aroonosc']))
    async def _ind_bop(self): raise NotImplementedException('indicator')
    async def _ind_cci(self): raise NotImplementedException('indicator')
    async def _ind_cmo(self): raise NotImplementedException('indicator')
    async def _ind_dx(self): raise NotImplementedException('indicator')
    async def _ind_macd(self):
        macd, macdsignal, macdhist = ta.MACD(self.current_time_df['close'], **self.analysis_config['indicators']['macd'])
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
    async def _ind_roc(self): return list(ta.ROC(self.current_time_df['close'], **self.analysis_config['indicators']['roc']))
    async def _ind_rocp(self): return list(ta.ROCP(self.current_time_df['close'], **self.analysis_config['indicators']['rocp']))
    async def _ind_rocr(self): return list(ta.ROCR(self.current_time_df['close'], **self.analysis_config['indicators']['rocr']))
    async def _ind_rocr100(self): return list(ta.ROCR100(self.current_time_df['close'], **self.analysis_config['indicators']['rocr100']))
    async def _ind_rsi(self): 
        return list(ta.RSI(self.current_time_df['close'], **self.analysis_config['indicators']['rsi']))
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
    async def _ind_atr(self): return list(ta.ATR( self.current_time_df['high'],  self.current_time_df['low'],  self.current_time_df['close']))
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