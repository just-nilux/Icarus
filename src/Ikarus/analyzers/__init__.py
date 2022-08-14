import asyncio
import copy
import logging
import sys
from .indicators import Indicators
logger = logging.getLogger('app')
import inspect


def is_mod_function(mod, func):
    return inspect.isfunction(func) and inspect.getmodule(func) == mod

def list_functions(mod):
    return [func.__name__ for func in mod.__dict__.values() 
            if is_mod_function(mod, func)]

print ('functions in current module:\n', list_functions(sys.modules[__name__]))
print ('functions in inspect module:\n', list_functions(inspect))
class Analyzer(Indicators):
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
                indicator_names = list(self.analysis_config['indicators'].keys())
                #import sys
                current_module = sys.modules[__name__]
                #getattr(current_module, 'AFunction')
                for ind_method, ind_name in zip(indicator_method_names,indicator_names):
                    if hasattr(self, ind_method): indicator_coroutines.append(getattr(current_module, ind_method)(time_df, **self.analysis_config['indicators'].get(ind_name,{})))
                    else: raise RuntimeError(f'Unknown indicator: "{ind_method}"')

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