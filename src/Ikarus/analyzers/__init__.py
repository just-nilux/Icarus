import asyncio
from analyzers.talib_indicators import TALibIndicators
from analyzers.indicators import Indicators
from analyzers.market_classification import MarketClassification
from analyzers.patterns import Patterns
from analyzers.support_resistance import SupportResistance


class Analyzer(Indicators, TALibIndicators, Patterns, SupportResistance, MarketClassification):

    def __init__(self, config):
        self.analysis_config = config.get('analysis')
        self.time_scales_config = config.get('time_scales')

        return


    async def analyze(self, data_dict):
        analysis_dict=dict()
        for pair,data_obj in data_dict.items():
            analysis_obj = dict()

            for time_scale, candlesticks in data_obj.items():

                # Generate coroutines
                indicator_coroutines = []
                header = '_'
                indicator_method_names = list(map(lambda orig_string: header + orig_string, self.analysis_config.keys()))
                indicator_names = list(self.analysis_config.keys())

                for ind_method, ind_name in zip(indicator_method_names,indicator_names):
                    if hasattr(self, ind_method): indicator_coroutines.append(getattr(self, ind_method)(candlesticks, **self.analysis_config.get(ind_name,{})))
                    else: raise RuntimeError(f'Unknown Analyzer: "{ind_method}"')

                analysis_output = list(await asyncio.gather(*indicator_coroutines))


                # TODO: REFACTORUNG: Sample analyzer does not do patterns
                #       Just combine everyting. you can get rid of the prefixes if youwish
                # NOTE: Since coroutines are not reuseable, they require to be created in each cycle
                # NOTE: pd.Series needs to be casted to list
                stats = dict()
                for key, value in zip(self.analysis_config.keys(), analysis_output):
                    stats[key] = value
                # Assign "stats" to each "time_scale"
                analysis_obj[time_scale] = stats

            analysis_dict[pair] = analysis_obj

        return analysis_dict
