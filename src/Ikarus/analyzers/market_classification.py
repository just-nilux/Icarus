import numpy as np
from itertools import groupby
from operator import itemgetter
from ..utils import time_scale_to_milisecond


class MarketClassification():

    async def _market_class_aroonosc(self, candlesticks, **kwargs):
        analyzer = '_aroonosc'

        if hasattr(self, analyzer):
            analysis_output = await getattr(self, analyzer)(candlesticks)

        class_indexes = {}
        class_indexes['downtrend'] = np.where(np.array(analysis_output) < 0)[0]
        class_indexes['uptrend'] = np.where(np.array(analysis_output) > 0)[0]

        class_stats = await MarketClassification.calculate_class_stats(candlesticks, class_indexes)
        return class_stats


    async def _market_class_fractal_aroon(self, candlesticks, **kwargs):
        # TODO: Fix the shit code
        analyzer = '_fractal_aroon'

        if hasattr(self, analyzer):
            analysis_output = await getattr(self, analyzer)(candlesticks)

        # The class detection logic depends on the data source strictly.
        class_indexes = {}
        class_indexes['downtrend'] = np.where(np.nan_to_num(analysis_output['aroondown']) > 80)[0]
        class_indexes['uptrend'] = np.where(np.nan_to_num(analysis_output['aroonup']) > 80)[0]

        # Class occurence indexes
        class_stats = await MarketClassification.calculate_class_stats(candlesticks, class_indexes,3)

        # if last closed candle is in uptrend, then then 'end' parameter wikk be equal to its timestamp
        # so the day_diff will be 1
        #result['is_daydiff']=int((candlesticks.index[-1] - result['uptrend'][-1]['end'])/time_scale_to_milisecond('1d'))
        #result['is_lastidx']=int(analysis_output['aroonup'][-1] > 80)
        return class_stats


    async def calculate_class_stats(candlesticks, class_indexes, validation_counter=0):
        
        ts_index = candlesticks.index
        result = {}

        for class_name, filter_idx in class_indexes.items():
            class_item_list = []
            for k, g in groupby(enumerate(filter_idx), lambda ix: ix[0] - ix[1]):
                seq_idx = list(map(itemgetter(1), g))
                # NOTE: If the sq. length is 1 than it will not be displayed. Apply "seq_idx[-1]+1" if you need to
                class_item = {'start':ts_index[seq_idx[0]], 'end':ts_index[seq_idx[-1]]}

                # Check if the validation will be performed
                if validation_counter > 0:
                    if len(seq_idx) >= validation_counter:
                        class_item['validation_point'] = ts_index[seq_idx[0]+validation_counter -1]
                    else:
                        continue # Continue if the validation is performed and the class instance is not valid
                
                class_item_list.append(class_item)
            result[class_name] = class_item_list
        return result
