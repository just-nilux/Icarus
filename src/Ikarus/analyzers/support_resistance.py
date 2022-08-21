from dataclasses import asdict, dataclass, field
import math
from sklearn.cluster import KMeans, DBSCAN, MeanShift, OPTICS, Birch
import numpy as np
from ..utils import minute_to_time_scale
import itertools


@dataclass
class SRCluster():
    centroids: list = field(default_factory=list)
    validation_index: int = 0
    min_cluster_members: int = 0
    horizontal_distribution_score: float = 0.0
    vertical_distribution_score: float = 0.0
    chunk_start_index: int = 0
    chunk_end_index: int = 0


class SupportResistance():

    async def eval_sup_res_cluster_horizontal_score(indices, num_of_candle):
        # NOTE: By dividing the indice diferences to len(dbscan_bear), we manage to represent the distance without the dependecy of number of candles:
        weights = list(range(1,len(indices)))
        return np.round(np.average(np.diff(indices) / num_of_candle, weights=weights),4)


    async def eval_sup_res_cluster_vertical_score(centroids, chart_price_range):
        cluster_price_range = max(centroids) - min(centroids)
        cluster_price_range_perc = cluster_price_range / chart_price_range
        return np.round(cluster_price_range_perc/len(centroids), 4)


    async def eval_sup_res_clusters(algorithm, candle_chunks, chart_price_range):
        sr_levels = []
        chunk_start_index = 0
        chunk_end_index = 0
        for chunk in candle_chunks:

            min_cluster_members = max(round(chunk.size/100),3)

            if hasattr(algorithm, 'min_samples'):
                algorithm.set_params(min_samples=min_cluster_members)

            cluster_predictions = algorithm.fit_predict(chunk)
            cls_tokens = np.unique(cluster_predictions)

            # Increase the chunk_end_index
            chunk_end_index += (chunk.size - 1)

            for token in cls_tokens:
                # NOTE: Ignore outliers
                if token == -1:
                    continue

                indices = np.where(cluster_predictions == token)[0]
                centroids = chunk[indices].reshape(1,-1)[0].tolist()

                # NOTE: Ignore the cluster if all of the members are 0, or the not enough cluster members
                if not any(centroids) or len(centroids)<min_cluster_members:
                    continue

                srcluster = SRCluster(
                    centroids,
                    chunk_start_index + indices[min_cluster_members-1],
                    min_cluster_members,
                    await SupportResistance.eval_sup_res_cluster_horizontal_score(indices, len(cluster_predictions)),
                    await SupportResistance.eval_sup_res_cluster_vertical_score(centroids, chart_price_range)
                )

                # If there is more then 1 chunk, it means that there are different start and end points for sr_clusters
                if len(candle_chunks) > 1:
                    srcluster.chunk_start_index = chunk_start_index
                    srcluster.chunk_end_index = chunk_end_index
                sr_levels.append(srcluster)

            # Since the current chunk is completed, move the start point to next chunk
            chunk_start_index += chunk.size # TODO TEST
        return sr_levels

    async def create_candle_chunks(data_points, chunk_size):

        if chunk_size and data_points.size > chunk_size:
            filled_chunk_num = math.floor(data_points.size/chunk_size)
            candle_chunks = [data_points[i:i+chunk_size] for i in range(filled_chunk_num)]    # Add filled chunks
            candle_chunks.append(data_points[filled_chunk_num*chunk_size:])                   # Add residual chunks
            return candle_chunks
        else:
            return [data_points]


    async def _support_birch(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bullish_fractal_3')

        bullish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # NOTE: Band of %0.5 unless optimized
        birch = Birch(branching_factor=15, n_clusters = None, threshold=eps)
        
        # Calculate chunk_size if the discrete mode enabled
        chunk_size = None
        if kwargs.get('discrete_mode', False):
            diff_in_minute = int((candlesticks.index[1]-candlesticks.index[0])/60000)
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)][1]

        candle_chunks = await SupportResistance.create_candle_chunks(bullish_frac, chunk_size)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(birch, candle_chunks, chart_price_range)

        return sr_clusters


    async def _resistance_birch(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bearish_fractal_3')

        bearish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # NOTE: Band of %0.5 unless optimized
        birch = Birch(branching_factor=15, n_clusters = None, threshold=eps)

        # Calculate chunk_size if the discrete mode enabled
        chunk_size = None
        if kwargs.get('discrete_mode', False):
            diff_in_minute = int((candlesticks.index[1]-candlesticks.index[0])/60000)
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)][1]

        candle_chunks = await SupportResistance.create_candle_chunks(bearish_frac, chunk_size)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(birch, candle_chunks, chart_price_range)
        return sr_clusters


    async def _support_optics(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bullish_fractal_3')
        cluster_method = kwargs.get('cluster_method','xi')   

        bullish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # NOTE: Band of %0.5 unless optimized
        min_samples = max(round(candlesticks.shape[0]/100),3)
        optics = OPTICS(eps=eps, cluster_method=cluster_method)
        # Calculate chunk_size if the discrete mode enabled
        chunk_size = None
        if kwargs.get('discrete_mode', False):
            diff_in_minute = int((candlesticks.index[1]-candlesticks.index[0])/60000)
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)][1]

        candle_chunks = await SupportResistance.create_candle_chunks(bullish_frac, chunk_size)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(optics, candle_chunks, chart_price_range)

        return sr_clusters


    async def _resistance_optics(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bearish_fractal_3')
        cluster_method = kwargs.get('cluster_method','xi')   

        bearish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # TODO: Optimize this epsilon value based on volatility or sth else
        min_samples = max(round(candlesticks.shape[0]/100),3)
        optics = OPTICS(eps=eps, cluster_method=cluster_method)
        # Calculate chunk_size if the discrete mode enabled
        chunk_size = None
        if kwargs.get('discrete_mode', False):
            diff_in_minute = int((candlesticks.index[1]-candlesticks.index[0])/60000)
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)][1]

        candle_chunks = await SupportResistance.create_candle_chunks(bearish_frac, chunk_size)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(optics, candle_chunks, chart_price_range)
        return sr_clusters

    async def _support_dbscan(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bullish_fractal_3')
        bullish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # NOTE: Band of %0.5 unless optimized
        dbscan = DBSCAN(eps=eps) # NOTE: min_sample is set inside of the eval_sup_res_clusters method

        # Calculate chunk_size if the discrete mode enabled
        chunk_size = None
        if kwargs.get('discrete_mode', False):
            diff_in_minute = int((candlesticks.index[1]-candlesticks.index[0])/60000)
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)][1]

        candle_chunks = await SupportResistance.create_candle_chunks(bullish_frac, chunk_size)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(dbscan, candle_chunks, chart_price_range)
        return sr_clusters


    async def _resistance_dbscan(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bearish_fractal_3')
        # NOTE: In order to yield validation points, nan values are assigned to 0. 
        #       They are visualized but not in the appeared window        

        bearish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * 0.005) # TODO: Optimize this epsilon value based on volatility or sth else
        dbscan = DBSCAN(eps=eps) # NOTE: min_sample is set inside of the eval_sup_res_clusters method

        # Calculate chunk_size if the discrete mode enabled
        chunk_size = None
        if kwargs.get('discrete_mode', False):
            diff_in_minute = int((candlesticks.index[1]-candlesticks.index[0])/60000)
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)][1]

        candle_chunks = await SupportResistance.create_candle_chunks(bearish_frac, chunk_size)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(dbscan, candle_chunks, chart_price_range)
        return sr_clusters


    async def _support_meanshift(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bullish_fractal_3')

        bullish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        bandwidth = float(chart_price_range * 0.01) # TODO: Optimize this epsilon value based on volatility or sth else
        meanshift = MeanShift(bandwidth=bandwidth) 
        
        # TODO: Specifying bandwith halps a bit. I dont know why the estimation did not worked or how it is calculated
        #       Things to improve:
        #       - Min number of members can be added as post filter (seems like does not working well)
        #       - 
        # Calculate chunk_size if the discrete mode enabled
        chunk_size = None
        if kwargs.get('discrete_mode', False):
            diff_in_minute = int((candlesticks.index[1]-candlesticks.index[0])/60000)
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)][1]

        candle_chunks = await SupportResistance.create_candle_chunks(bullish_frac, chunk_size)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(meanshift, candle_chunks, chart_price_range)
        return sr_clusters


    async def _resistance_meanshift(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bearish_fractal_3')

        bearish_frac = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        bandwidth = float(chart_price_range * 0.005) # TODO: Optimize this epsilon value based on volatility or sth else
        meanshift = MeanShift(bandwidth=bandwidth) # TODO use bandwidth

        # Calculate chunk_size if the discrete mode enabled
        chunk_size = None
        if kwargs.get('discrete_mode', False):
            diff_in_minute = int((candlesticks.index[1]-candlesticks.index[0])/60000)
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)][1]

        candle_chunks = await SupportResistance.create_candle_chunks(bearish_frac, chunk_size)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(meanshift, candle_chunks, chart_price_range)
        return sr_clusters

    async def _support_kmeans(self, candlesticks, **kwargs):

        source = '_' + kwargs.get('source','bullish_fractal_3')
        min_cluster_members = kwargs.get('min_cluster_members', 3)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        data_points = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)

        kmeans = KMeans(
            n_clusters=5, init='random',
            n_init=13, max_iter=300, 
            tol=1e-04, random_state=0
        )

        # Calculate chunk_size if the discrete mode enabled
        chunk_size = None
        if kwargs.get('discrete_mode', False):
            diff_in_minute = int((candlesticks.index[1]-candlesticks.index[0])/60000)
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)][1]

        candle_chunks = await SupportResistance.create_candle_chunks(data_points, chunk_size)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(kmeans, candle_chunks, chart_price_range)
        return sr_clusters


    async def _resistance_kmeans(self, candlesticks, **kwargs):
        source = '_' + kwargs.get('source','bearish_fractal_3')
        min_cluster_members = kwargs.get('min_cluster_members', 3)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        data_points = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)

        kmeans = KMeans(
            n_clusters=5, init='random',
            n_init=13, max_iter=300, 
            tol=1e-04, random_state=0
        )

        # Calculate chunk_size if the discrete mode enabled
        chunk_size = None
        if kwargs.get('discrete_mode', False):
            diff_in_minute = int((candlesticks.index[1]-candlesticks.index[0])/60000)
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)][1]

        candle_chunks = await SupportResistance.create_candle_chunks(data_points, chunk_size)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(kmeans, candle_chunks, chart_price_range)
        return sr_clusters


