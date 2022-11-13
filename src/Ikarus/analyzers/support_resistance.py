from dataclasses import asdict, dataclass, field
import math
from sklearn.cluster import KMeans, DBSCAN, MeanShift, OPTICS, Birch
import numpy as np
from ..utils import minute_to_time_scale
import pandas as pd


@dataclass
class SRCluster():
    centroids: list = field(default_factory=list)
    validation_index: int = 0
    min_cluster_members: int = 0
    horizontal_distribution_score: float = 0.0
    vertical_distribution_score: float = 0.0
    chunk_start_index: int = 0
    chunk_end_index: int = 0


@dataclass
class FibonacciSRCluster(SRCluster):
    level: float = .0 
    price_level: float = .0
    band: float = .0


class FibonacciClustering():
    coeffs = np.array([0, 0.236, 0.382, 0.5, 0.618, 1])
    def __init__(self, max_price, min_price, radius) -> None:
        price_diff = max_price - min_price
        self.price_levels = min_price + (price_diff * FibonacciClustering.coeffs)
        self.radius = radius
        pass

    def reinit(self, max_price, min_price) -> None:
        price_diff = max_price - min_price
        self.levels = min_price + (price_diff * FibonacciClustering.coeffs)

    def fit_predict(self, chunk):

        tokenized_chunks = []
        for idx, price_level in enumerate(self.price_levels):
            cluster_upper_limit = price_level * (1+self.radius)
            cluster_lower_limit = price_level * (1-self.radius)
            filter = np.logical_and(cluster_lower_limit < chunk, chunk < cluster_upper_limit)
            token = filter.astype(int)
            token *= (idx+1)
            tokenized_chunks.append(token)

        return np.array(tokenized_chunks).sum(axis=0) - 1



class SupportResistance():

    async def eval_sup_res_cluster_horizontal_score(indices, num_of_candle):
        # NOTE: By dividing the indice diferences to len(dbscan_bear), we manage to represent the distance without the dependecy of number of candles:
        if len(indices) <= 1:
            return 0

        weights = list(range(1,len(indices)))
        return np.round(np.average(np.diff(indices) / num_of_candle, weights=weights),4)


    async def eval_sup_res_cluster_vertical_score(centroids, chart_price_range):
        if len(centroids) <= 1:
            return 0

        cluster_price_range = max(centroids) - min(centroids)
        cluster_price_range_perc = cluster_price_range / chart_price_range
        return np.round(cluster_price_range_perc/len(centroids), 4)


    async def eval_sup_res_clusters(algorithm, candles, meta_chunks, chart_price_range):
        sr_levels = []
        #chunk_start_index = 0
        #chunk_end_index = 0
        for meta_chunk in meta_chunks:

            #chunk
            chunk = candles[meta_chunk[0] : meta_chunk[1]]
            min_cluster_members = max(round(chunk.size/100),3)

            if hasattr(algorithm, 'min_samples'):
                algorithm.set_params(min_samples=min_cluster_members)

            cluster_predictions = algorithm.fit_predict(chunk)
            cls_tokens = np.unique(cluster_predictions)

            # Increase the chunk_end_index
            #chunk_end_index += (chunk.size - 1)

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
                    meta_chunk[0] + indices[min_cluster_members-1],
                    min_cluster_members,
                    await SupportResistance.eval_sup_res_cluster_horizontal_score(indices, len(cluster_predictions)),
                    await SupportResistance.eval_sup_res_cluster_vertical_score(centroids, chart_price_range),
                    meta_chunk[0],
                    meta_chunk[1]
                )

                # If there is more then 1 chunk, it means that there are different start and end points for sr_clusters
                #if len(candle_chunks) > 1:
                #    srcluster.chunk_start_index = chunk_start_index
                #    srcluster.chunk_end_index = chunk_end_index
                sr_levels.append(srcluster)

            # Since the current chunk is completed, move the start point to next chunk
            #chunk_start_index += chunk.size # TODO TEST
        return sr_levels

    async def create_meta_chunks(data_points, frame_length, step_length):
        meta_chunks = []
        if frame_length and data_points.size > frame_length:

            # Number of chunks that will be in full length: frame_length
            filled_chunk_num = math.ceil((data_points.size - frame_length)/step_length)

            # List of meta_chunks with the length of frame_length
            for i in range(filled_chunk_num):
                chunk_start_idx = i*step_length
                chunk_end_idx = chunk_start_idx+frame_length
                meta_chunks.append((chunk_start_idx,chunk_end_idx))
            
            # Add the last chunk which has a length less than frame_length
            # TODO: NEXT: Check the case where there is no residual chunk
            meta_chunks.append((filled_chunk_num*step_length, data_points.size-1))

        else:
            meta_chunks.append((0,data_points.size-1))
        return meta_chunks


    async def _fibonacci(self, candlesticks, **kwargs):
        
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        fibonacci = FibonacciClustering(candlesticks['high'].max(), candlesticks['low'].min(), kwargs.get('radius',0.005))

        source = '_' + kwargs.get('source','close')
        chunk = np.nan_to_num(await getattr(self, source)(candlesticks)).reshape(-1,1)

        # NOTE: Both bearish and bullish patterns can be combined since the fibonacci is not only support or resistance:
        # chunk = np.concatenate([bearish_frac, bullish_frac])
        # or
        # pd.concat([candlesticks['high'], candlesticks['low']], axis=0).to_numpy()

        cluster_predictions = fibonacci.fit_predict(chunk)
        fibo_clusters = []

        # NOTE: The term validation index is used as a point where the level/cluster is verified and ready to be used.
        # By using this definition, it corresponds to the max index of min or max price level value, since the 
        # levels are designed after this index
        validation_index = max(
            np.where(candlesticks['high'] == candlesticks['high'].max())[0][0],
            np.where(candlesticks['low'] == candlesticks['low'].min())[0][0]
        )
        for token in range(-1, len(fibonacci.coeffs)):
            # NOTE: Ignore outliers
            if token == -1:
                continue

            indices = np.where(cluster_predictions == token)[0]
            centroids = chunk[indices].reshape(1,-1)[0].tolist()

            if not any(centroids):
                continue

            srcluster = FibonacciSRCluster(
                level=FibonacciClustering.coeffs[token],
                price_level=fibonacci.price_levels[token],
                band=fibonacci.radius,
                centroids=centroids,
                validation_index=validation_index,
                horizontal_distribution_score=await SupportResistance.eval_sup_res_cluster_horizontal_score(indices, len(cluster_predictions)),
                vertical_distribution_score=await SupportResistance.eval_sup_res_cluster_vertical_score(centroids, chart_price_range)
            )
            fibo_clusters.append(srcluster)
        return fibo_clusters


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
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)]

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
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)]

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
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)]

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
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)]

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
        frame_length = None
        step_length = None
        if "step_length" in kwargs.keys() or "step_to_frame_ratio" in kwargs.keys():
            diff_in_minute = int((candlesticks.index[1]-candlesticks.index[0])/60000)
            frame_length = self.time_scales_config[minute_to_time_scale(diff_in_minute)]

            if "step_length" in kwargs.keys():
                step_length = kwargs['step_length']
            elif "step_to_frame_ratio" in kwargs.keys():
                step_length = int(frame_length / kwargs['step_to_frame_ratio'])


        meta_chunks = await SupportResistance.create_meta_chunks(bullish_frac, frame_length, step_length)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(dbscan, bullish_frac, meta_chunks, chart_price_range)
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
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)]

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
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)]

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
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)]

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
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)]

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
            chunk_size = self.time_scales_config[minute_to_time_scale(diff_in_minute)]

        candle_chunks = await SupportResistance.create_candle_chunks(data_points, chunk_size)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(kmeans, candle_chunks, chart_price_range)
        return sr_clusters


