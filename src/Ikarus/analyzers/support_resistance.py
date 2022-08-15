from sklearn.cluster import KMeans, DBSCAN, MeanShift, OPTICS, Birch
import numpy as np

class SupportResistance():

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
            sr_level['horizontal_distribution_score'] = await SupportResistance.eval_sup_res_cluster_horizontal_score(indices, len(cluster_predictions))
            sr_level['vertical_distribution_score'] = await SupportResistance.eval_sup_res_cluster_vertical_score(sr_level['centroids'], chart_price_range)

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


    async def _support_birch(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bullish_fractal_3')

        bullish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # NOTE: Band of %0.5 unless optimized
        min_samples = max(round(candlesticks.shape[0]/100),3)
        birch = Birch(branching_factor=15, n_clusters = None, threshold=eps)
        return await SupportResistance.eval_sup_res_clusters(birch, bullish_frac, min_samples, chart_price_range)


    async def _resistance_birch(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bearish_fractal_3')

        bullish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # NOTE: Band of %0.5 unless optimized
        min_samples = max(round(candlesticks.shape[0]/100),3)
        birch = Birch(branching_factor=15, n_clusters = None, threshold=eps)
        return await SupportResistance.eval_sup_res_clusters(birch, bullish_frac, min_samples, chart_price_range)


    async def _support_optics(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bullish_fractal_3')
        cluster_method = kwargs.get('cluster_method','xi')   

        bullish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # NOTE: Band of %0.5 unless optimized
        min_samples = max(round(candlesticks.shape[0]/100),3)
        optics = OPTICS(eps=eps, min_samples=min_samples, cluster_method=cluster_method)
        return await SupportResistance.eval_sup_res_clusters(optics, bullish_frac, optics.min_samples, chart_price_range)


    async def _resistance_optics(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bearish_fractal_3')
        cluster_method = kwargs.get('cluster_method','xi')   

        bearish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # TODO: Optimize this epsilon value based on volatility or sth else
        min_samples = max(round(candlesticks.shape[0]/100),3)
        optics = OPTICS(eps=eps, min_samples=min_samples, cluster_method=cluster_method)
        return await SupportResistance.eval_sup_res_clusters(optics, bearish_frac, optics.min_samples, chart_price_range)


    async def _support_dbscan(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bullish_fractal_3')
        bullish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # NOTE: Band of %0.5 unless optimized
        min_samples = max(round(candlesticks.shape[0]/100),3)
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        return await SupportResistance.eval_sup_res_clusters(dbscan, bullish_frac, dbscan.min_samples, chart_price_range)


    async def _resistance_dbscan(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bearish_fractal_3')
        # NOTE: In order to yield validation points, nan values are assigned to 0. 
        #       They are visualized but not in the appeared window        

        bearish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # TODO: Optimize this epsilon value based on volatility or sth else
        min_samples = max(round(candlesticks.shape[0]/100),3)
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        return await SupportResistance.eval_sup_res_clusters(dbscan, bearish_frac, dbscan.min_samples, chart_price_range)


    async def _support_meanshift(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bullish_fractal_3')
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
        return await SupportResistance.eval_sup_res_clusters(meanshift, bearish_frac, min_samples, chart_price_range)


    async def _resistance_meanshift(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bearish_fractal_3')
        min_cluster_members = kwargs.get('min_cluster_members', 3)

        bearish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        bandwidth = float(chart_price_range * 0.005) # TODO: Optimize this epsilon value based on volatility or sth else
        min_samples = max(round(candlesticks.shape[0]/100),3)
        meanshift = MeanShift(bandwidth=bandwidth) # TODO use bandwidth
        return await SupportResistance.eval_sup_res_clusters(meanshift, bearish_frac, min_samples, chart_price_range)


    async def _support_kmeans(self, candlesticks, **kwargs):

        source = '_' + kwargs.get('source','bullish_fractal_3')
        min_cluster_members = kwargs.get('min_cluster_members', 3)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        data_points = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)

        km = KMeans(
            n_clusters=5, init='random',
            n_init=13, max_iter=300, 
            tol=1e-04, random_state=0
        )

        return await SupportResistance.eval_sup_res_clusters(km, data_points, min_cluster_members, chart_price_range)

    async def _resistance_kmeans(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bearish_fractal_3')
        min_cluster_members = kwargs.get('min_cluster_members', 3)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        data_points = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)

        km = KMeans(
            n_clusters=5, init='random',
            n_init=13, max_iter=300, 
            tol=1e-04, random_state=0
        )

        return await SupportResistance.eval_sup_res_clusters(km, data_points, min_cluster_members, chart_price_range)



