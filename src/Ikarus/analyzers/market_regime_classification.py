import numpy as np
from itertools import groupby
from operator import itemgetter
from ..utils import time_scale_to_milisecond


class MarketRegimeClassification():

    async def _ind_market_classifier(self, candlesticks, **kwargs):
        # TODO: Market status receives the name of some other indicators and runs
        #       a secondary analysis.
        #       Maybe the secondary analysis such as  S/R levels should be put under
        #       another category

        analyzer = "_ind_" + kwargs.get('source','fractal_aroon')

        if hasattr(self, analyzer):
            analysis_output = await getattr(self, analyzer)(candlesticks)
        
        classification = {}
        if analyzer == '_ind_aroonosc':
            uptrend_filter = np.where(np.array(analysis_output) > 0)[0]
            downtrend_filter = np.where(np.array(analysis_output) < 0)[0]
            classification = {'downtrend':downtrend_filter, 'uptrend':uptrend_filter}

        elif analyzer == '_ind_fractal_aroon':
            uptrend_filter = np.where(np.nan_to_num(analysis_output['aroonup']) > 80)[0]
            downtrend_filter = np.where(np.nan_to_num(analysis_output['aroondown']) > 80)[0]
            classification = {'downtrend':downtrend_filter, 'uptrend':uptrend_filter}

        ts_index = candlesticks.index
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
        result['is_daydiff']=int((candlesticks.index[-1] - result['uptrend'][-1]['end'])/time_scale_to_milisecond('1d'))
        result['is_lastidx']=int(analysis_output['aroonup'][-1] > 80)
        return result
