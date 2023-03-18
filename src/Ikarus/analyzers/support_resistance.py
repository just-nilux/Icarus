from dataclasses import asdict, dataclass, field
import math
from sklearn.cluster import KMeans, DBSCAN, MeanShift, OPTICS, Birch
import numpy as np
from utils import minute_to_time_scale
import asyncio
import itertools

@dataclass
class SRConfig():
    kwargs: dict                        # Mandatory
    source: str = ''
    min_members: int = 3
    frame_length: int = None
    step_length: int = None

    # DBSCAN, OPTICS, BIRCH
    eps_coeff: float = 0.005            # TODO: Optimize this epsilon value based on volatility or sth else

    # MeanShift
    bandwidth_coeff: float = 0.01

    # OPTICS
    cluster_method: str = 'xi'

    # KMeans
    n_cluster: int = None

    def __post_init__(self):
        self.source = '_' + self.kwargs.get('source','')
        self.eps = self.kwargs.get('eps',0.005)

    def parse_chunks_params(self, diff_in_minute, time_scales_config):
        if "step_length" in self.kwargs.keys() or "step_to_frame_ratio" in self.kwargs.keys():
            self.frame_length = time_scales_config[minute_to_time_scale(diff_in_minute)]

            if "step_length" in self.kwargs.keys():
                self.step_length = self.kwargs.get('step_length')
            elif "step_to_frame_ratio" in self.kwargs.keys():
                self.step_length = int(self.frame_length * self.kwargs.get('step_to_frame_ratio'))


@dataclass
class SRCluster():
    centroids: list = field(default_factory=list)
    validation_index: int = 0
    # NOTE: relative_validation_index parameter can also be added by thinking that it may give a clue about a normal
    # validation time so that anomalies might be foreseen. However it also has other dependencies such as: 
    # - the chunk start index 
    # - chunk length
    # Thus it requires a bit more effort to figure out if it worths to effort to implement and investigate
    min_cluster_members: int = 0
    horizontal_distribution_score: float = 0.0          # Higher the better
    vertical_distribution_score: float = 0.0            # Lower the better
    chunk_start_index: int = None
    chunk_end_index: int = None
    distribution_score: float = None                    # Higher the better
    number_of_retest: int = None                        # Higher the better
    number_of_members: int = None                       # Higher the better
    distribution_efficiency: int = None                 # Higher the better

    def __post_init__(self):
        self.distribution_score = round(self.horizontal_distribution_score/self.vertical_distribution_score,2) 
        self.number_of_members =len(self.centroids)
        self.number_of_retest = self.number_of_members-self.min_cluster_members
        self.distribution_efficiency = round(self.distribution_score * self.number_of_members,2)

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

    def eval_min_cluster_members(chunk_size):
        return max(round(chunk_size/100),3)

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

        # The returned value should not be zero since it will be denominator in distribution_score calculation
        return max(np.round(cluster_price_range_perc/len(centroids), 6), 0.000001)


    async def eval_sup_res_clusters(algorithm, candles, meta_chunks, chart_price_range):
        sr_levels = []

        for meta_chunk in meta_chunks:
            chunk = candles[meta_chunk[0] : meta_chunk[1]]
            min_cluster_members = SupportResistance.eval_min_cluster_members(chunk.size)

            # If the attribute min_samples exist, we have to overwrite it
            if hasattr(algorithm, 'min_samples'):
                algorithm.set_params(min_samples=min_cluster_members) 

            cluster_predictions = algorithm.fit_predict(chunk)
            cls_tokens = np.unique(cluster_predictions)

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
                sr_levels.append(srcluster)

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
            
            # Check if we already hit the last candle. If not add the residual candles
            if meta_chunks[-1][1] != (data_points.size-1):
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
        sr_config = SRConfig(kwargs)
        sr_config.parse_chunks_params(int((candlesticks.index[1]-candlesticks.index[0])/60000), self.time_scales_config)

        bullish_frac = np.nan_to_num(await getattr(self, sr_config.source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * sr_config.eps_coeff)
        birch = Birch(branching_factor=15, n_clusters = None, threshold=eps)

        meta_chunks = await SupportResistance.create_meta_chunks(bullish_frac, sr_config.frame_length, sr_config.step_length)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(birch, bullish_frac, meta_chunks, chart_price_range)
        return sr_clusters


    async def _resistance_birch(self, candlesticks, **kwargs):
        sr_config = SRConfig(kwargs)
        sr_config.parse_chunks_params(int((candlesticks.index[1]-candlesticks.index[0])/60000), self.time_scales_config)

        bearish_frac = np.nan_to_num(await getattr(self, sr_config.source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * sr_config.eps_coeff)
        birch = Birch(branching_factor=15, n_clusters = None, threshold=eps)
        # TODO: Add birch configs to sr_config

        meta_chunks = await SupportResistance.create_meta_chunks(bearish_frac, sr_config.frame_length, sr_config.step_length)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(birch, bearish_frac, meta_chunks, chart_price_range)
        return sr_clusters


    async def _support_optics(self, candlesticks, **kwargs):
        sr_config = SRConfig(kwargs)
        sr_config.parse_chunks_params(int((candlesticks.index[1]-candlesticks.index[0])/60000), self.time_scales_config)  

        bullish_frac = np.nan_to_num(await getattr(self, sr_config.source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * sr_config.eps_coeff)
        optics = OPTICS(eps=eps, cluster_method=sr_config.cluster_method)

        meta_chunks = await SupportResistance.create_meta_chunks(bullish_frac, sr_config.frame_length, sr_config.step_length)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(optics, bullish_frac, meta_chunks, chart_price_range)
        return sr_clusters


    async def _resistance_optics(self, candlesticks, **kwargs):
        sr_config = SRConfig(kwargs)
        sr_config.parse_chunks_params(int((candlesticks.index[1]-candlesticks.index[0])/60000), self.time_scales_config)

        bearish_frac = np.nan_to_num(await getattr(self, sr_config.source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * sr_config.eps_coeff) 
        optics = OPTICS(eps=eps, cluster_method=sr_config.cluster_method)

        meta_chunks = await SupportResistance.create_meta_chunks(bearish_frac, sr_config.frame_length, sr_config.step_length)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(optics, bearish_frac, meta_chunks, chart_price_range)
        return sr_clusters

    async def _support_dbscan(self, candlesticks, **kwargs):
        sr_config = SRConfig(kwargs)
        sr_config.parse_chunks_params(int((candlesticks.index[1]-candlesticks.index[0])/60000), self.time_scales_config)

        bullish_frac = np.nan_to_num(await getattr(self, sr_config.source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * sr_config.eps_coeff)
        dbscan = DBSCAN(eps=eps)

        meta_chunks = await SupportResistance.create_meta_chunks(bullish_frac, sr_config.frame_length, sr_config.step_length)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(dbscan, bullish_frac, meta_chunks, chart_price_range)
        return sr_clusters


    async def _resistance_dbscan(self, candlesticks, **kwargs):
        sr_config = SRConfig(kwargs)
        sr_config.parse_chunks_params(int((candlesticks.index[1]-candlesticks.index[0])/60000), self.time_scales_config)    

        bearish_frac = np.nan_to_num(await getattr(self, sr_config.source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        eps = float(chart_price_range * sr_config.eps_coeff)
        dbscan = DBSCAN(eps=eps) # NOTE: min_sample is set inside of the eval_sup_res_clusters method

        meta_chunks = await SupportResistance.create_meta_chunks(bearish_frac, sr_config.frame_length, sr_config.step_length)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(dbscan, bearish_frac, meta_chunks, chart_price_range)
        return sr_clusters


    async def _support_meanshift(self, candlesticks, **kwargs):
        sr_config = SRConfig(kwargs)
        sr_config.parse_chunks_params(int((candlesticks.index[1]-candlesticks.index[0])/60000), self.time_scales_config)   

        bullish_frac = np.nan_to_num(await getattr(self, sr_config.source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        bandwidth = float(chart_price_range * sr_config.bandwidth_coeff)
        meanshift = MeanShift(bandwidth=bandwidth) 
        
        # TODO: Specifying bandwith halps a bit. I dont know why the estimation did not worked or how it is calculated
        #       Things to improve:
        #       - Min number of members can be added as post filter (seems like does not working well)

        meta_chunks = await SupportResistance.create_meta_chunks(bullish_frac, sr_config.frame_length, sr_config.step_length)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(meanshift, bullish_frac, meta_chunks, chart_price_range)
        return sr_clusters


    async def _resistance_meanshift(self, candlesticks, **kwargs):
        sr_config = SRConfig(kwargs)
        sr_config.parse_chunks_params(int((candlesticks.index[1]-candlesticks.index[0])/60000), self.time_scales_config)   

        bearish_frac = np.nan_to_num(await getattr(self, sr_config.source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        bandwidth = float(chart_price_range * sr_config.bandwidth_coeff)
        meanshift = MeanShift(bandwidth=bandwidth) # TODO use bandwidth

        meta_chunks = await SupportResistance.create_meta_chunks(bearish_frac, sr_config.frame_length, sr_config.step_length)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(meanshift, bearish_frac, meta_chunks, chart_price_range)
        return sr_clusters

    async def _support_kmeans(self, candlesticks, **kwargs):
        sr_config = SRConfig(kwargs)
        sr_config.parse_chunks_params(int((candlesticks.index[1]-candlesticks.index[0])/60000), self.time_scales_config)

        bullish_frac = np.nan_to_num(await getattr(self, sr_config.source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        kmeans = KMeans(
            n_clusters=sr_config.n_cluster, init='random',
            n_init=13, max_iter=300, 
            tol=1e-04, random_state=0
        )

        meta_chunks = await SupportResistance.create_meta_chunks(bullish_frac, sr_config.frame_length, sr_config.step_length)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(kmeans, bullish_frac, meta_chunks, chart_price_range)
        return sr_clusters


    async def _resistance_kmeans(self, candlesticks, **kwargs):
        sr_config = SRConfig(kwargs)
        sr_config.parse_chunks_params(int((candlesticks.index[1]-candlesticks.index[0])/60000), self.time_scales_config)

        bearish_frac = np.nan_to_num(await getattr(self, sr_config.source)(candlesticks)).reshape(-1,1)
        chart_price_range = candlesticks['high'].max() - candlesticks['low'].min()
        kmeans = KMeans(
            n_clusters=sr_config.n_cluster, init='random',
            n_init=13, max_iter=300, 
            tol=1e-04, random_state=0
        )

        meta_chunks = await SupportResistance.create_meta_chunks(bearish_frac, sr_config.frame_length, sr_config.step_length)
        sr_clusters = await SupportResistance.eval_sup_res_clusters(kmeans, bearish_frac, meta_chunks, chart_price_range)
        return sr_clusters


    # _sr_<algorithm>
    async def _sr_dbscan(self, candlesticks, **kwargs):
        cors = [self._support_dbscan(candlesticks, **kwargs),
            self._resistance_dbscan(candlesticks, **kwargs)]
        return list(itertools.chain.from_iterable(await asyncio.gather(*cors)))


    async def _sr_kmeans(self, candlesticks, **kwargs):
        cors = [self._support_kmeans(candlesticks, **kwargs),
            self._resistance_kmeans(candlesticks, **kwargs)]
        return list(itertools.chain.from_iterable(await asyncio.gather(*cors)))


    async def _sr_birch(self, candlesticks, **kwargs):
        cors = [self._support_birch(candlesticks, **kwargs),
            self._resistance_birch(candlesticks, **kwargs)]
        return list(itertools.chain.from_iterable(await asyncio.gather(*cors)))


    async def _sr_optics(self, candlesticks, **kwargs):
        cors = [self._support_optics(candlesticks, **kwargs),
            self._resistance_optics(candlesticks, **kwargs)]
        return list(itertools.chain.from_iterable(await asyncio.gather(*cors)))


    async def _sr_meanshift(self, candlesticks, **kwargs):
        cors = [self._support_meanshift(candlesticks, **kwargs),
            self._resistance_meanshift(candlesticks, **kwargs)]
        return list(itertools.chain.from_iterable(await asyncio.gather(*cors)))
