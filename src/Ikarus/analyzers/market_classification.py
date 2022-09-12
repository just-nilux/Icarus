from dataclasses import dataclass
import numpy as np
from itertools import groupby
from operator import itemgetter
from hmmlearn.hmm import GaussianHMM


@dataclass
class MarketRegime():
    label: str
    start_ts: int
    end_ts: int
    start_price: float
    end_price: float
    lifetime_in_candle: int
    validation_point: int = None
    time_scale: str = ''
    symbol: str = ''
    def __post_init__(self):
        self.price_change_perc = round(100 * (self.end_price - self.start_price) / self.start_price, 2)

    def set_attribute(self, name, value):
        self.__setattr__(name, value)

@dataclass
class PredefinedMarketRegime(MarketRegime):
    pass

@dataclass
class UndefinedMarketRegime(MarketRegime):
    pass


class MarketClassification():

    async def _hmm(self, candlesticks, **kwargs):
        # TODO: It works fıne but what does it tell???
        close = np.array(candlesticks['close']).reshape(-1,1)
        daily_return = (1 - candlesticks['close'].div(candlesticks['close'].shift())).fillna(0)
        volatility_indicator = await self._atr(candlesticks)


        data_source = np.array(daily_return).reshape(-1,1)

        hmm_model = GaussianHMM(
            n_components=3, covariance_type="full", n_iter=1000
        ).fit(data_source)
        print("Model Score:", hmm_model.score(data_source))
        hidden_states = hmm_model.predict(data_source)
        #print(hmm_model.n_components)

        unique_states = np.unique(hidden_states)
        class_indexes = {}

        for state in unique_states:
            state_name = f'state_{state}'
            class_indexes[state_name] = np.where(hidden_states == state)[0]
        detected_market_regimes = await MarketClassification.detect_regime_instances(candlesticks, class_indexes, kwargs.get('validation_point', 0))

        return detected_market_regimes

    async def _market_class_aroonosc(self, candlesticks, **kwargs):
        analyzer = '_aroonosc'

        if hasattr(self, analyzer):
            analysis_output = await getattr(self, analyzer)(candlesticks)

        class_indexes = {}
        class_indexes['downtrend'] = np.where(np.array(analysis_output) < 0)[0]
        class_indexes['uptrend'] = np.where(np.array(analysis_output) > 0)[0]

        class_stats = await MarketClassification.detect_regime_instances(candlesticks, class_indexes, kwargs.get('validation_point', 0))
        return class_stats


    async def _market_class_fractal_aroon(self, candlesticks, **kwargs):
        # TODO: Fix the shit code
        analyzer = '_fractal_aroon'

        if hasattr(self, analyzer):
            analysis_output = await getattr(self, analyzer)(candlesticks)

        # The class detection logic depends on the data source strictly.
        class_indexes = {}
        class_indexes['downtrend'] = np.where(np.nan_to_num(analysis_output['aroondown']) > 80)[0]
        class_indexes['ranging'] = np.where(np.logical_and(
            np.nan_to_num(analysis_output['aroonup']) < 80, 
            np.nan_to_num(analysis_output['aroondown']) < 80))[0]
        class_indexes['uptrend'] = np.where(np.nan_to_num(analysis_output['aroonup']) > 80)[0]

        # Class occurence indexes
        detected_market_regimes = await MarketClassification.detect_regime_instances(candlesticks, class_indexes, kwargs.get('validation_point', 0))

        # if last closed candle is in uptrend, then then 'end' parameter wikk be equal to its timestamp
        # so the day_diff will be 1
        #result['is_daydiff']=int((candlesticks.index[-1] - result['uptrend'][-1]['end'])/time_scale_to_milisecond('1d'))
        #result['is_lastidx']=int(analysis_output['aroonup'][-1] > 80)
        #await MarketClassification.calculate_class_stats(detected_market_regimes)
        return detected_market_regimes


    async def detect_regime_instances(candlesticks, class_indexes, validation_counter):
        '''
        The essential features of classes is start and end timestamps. The rest is evaluated using these initial points
        '''
        ts_index = candlesticks.index
        result = {}

        for class_name, filter_idx in class_indexes.items():
            class_item_list = []
            for k, g in groupby(enumerate(filter_idx), lambda ix: ix[0] - ix[1]):
                seq_idx = list(map(itemgetter(1), g))
                # NOTE: If the sq. length is 1 than it will not be displayed. Apply "seq_idx[-1]+1" if you need to

                pmr = PredefinedMarketRegime(
                    label=class_name,
                    start_ts=ts_index[seq_idx[0]],
                    end_ts=ts_index[seq_idx[-1]],
                    lifetime_in_candle=len(seq_idx),
                    start_price=candlesticks['close'][ts_index[seq_idx[0]]],
                    end_price=candlesticks['close'][ts_index[seq_idx[-1]]],
                )

                # Check if the validation will be performed
                if validation_counter > 0:
                    if len(seq_idx) >= validation_counter:
                        pmr.set_attribute('validation_point', ts_index[seq_idx[0]+validation_counter -1])
                    else:
                        continue # Continue if the validation is performed and the class instance is not valid


                class_item_list.append(pmr)
            result[class_name] = class_item_list
            # TODO: No need to have a seperation between the calss instances since they are all labeled and self sufficient to be alice in visu.
        return result


    async def calculate_class_stats(detected_market_regimes):
    
        for regime_name, regime_instances in detected_market_regimes.items():
            regime_stats = {}
            regime_stats['num_of_occurence'] = len(regime_instances)
            regime_stats['lifetime_cluster'] = [instance['lifetime'] for instance in regime_instances]                  # Useful for distribution statistics
            regime_stats['price_change_cluster'] = [instance['price_change'] for instance in regime_instances]

        return