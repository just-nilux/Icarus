'''
Analyzers are the units that can be configured to provide certain analytics regarding target pairs
Analyzer is the first step of simplification.
'''

import pandas as pd
import logging
import talib as ta
import json

class Analyzer():
    """
    The duty of Analyzer class is to provide analysis objects.
    It is configurable
    """
    def __init__(self, _time_scale=None, _indicators=None):
        self.logger = logging.getLogger('app.{}'.format(__name__))
        
        return


    async def default_analyzer(self, data_dict):
        """This functions returns default analyzer object

        Args:
            pair_list (list): List of currency pair

        Returns:
            dict: analysis.json
        """    
        self.logger.debug("default_analyzer started")
        analysis_obj=dict()

        for pair in data_dict.keys():
            analysis = dict()
            analysis["1M"] = {}
            analysis["1w"] = {}
            analysis["1d"] = {}
            analysis["1h"] = {}
            analysis["15m"] = {}
            analysis["1m"] = {}
            analysis_obj[pair] = analysis

        self.logger.debug("default_analyzer ended")
        return analysis_obj


    async def sample_analyzer(self, data_dict):
        self.logger.debug("sample_analyzer started")

        analysis_obj=dict()
        for pair,time_dict in data_dict.items():
            self.logger.debug("  analysis started: [{}]".format(pair))

            analysis_pair = dict()

            # time_scale: 1m, 15m, ... 1M
            # time_df: pd.DataFrame with columns of Ikarus.kline_column_names
            for time_scale, time_df in time_dict.items():
                self.logger.debug("    analysing [{}]: [{}]".format(pair,time_scale))

                # TODO: asycn wrapper for each indicator
                # TODO: decomposer for each task

                # Evaluate the parameters
                # TODO: Some indicator can be just specific to a time_scale, thus there needs to be an config.json obj
                trange = ta.TRANGE(time_df['high'], time_df['low'], time_df['close'])
                obv = ta.OBV(time_df['close'], time_df['volume'])
                lowest_low, highest_high = time_df['low'].min(), time_df['high'].max()

                # Fill the dict with the statistics
                stats = dict()
                stats['trange'] = list(trange)
                stats['obv'] = list(obv)
                stats['llow'] = lowest_low
                stats['hhigh'] = highest_high

                # Assign "stats" to each "time_scale"
                analysis_pair[time_scale] = stats

            analysis_obj[pair] = analysis_pair
            self.logger.debug("  analysis ended: [{}]".format(pair))

        await self.dump(analysis_obj)
        self.logger.debug("sample_analyzer ended")
        return analysis_obj


    async def dump(self, js_obj):
        """
        This functions dumps json objects to files for debug purposes

        Args:
            js_obj (dict): dict to be dumped

        Returns:
            True:
        """    

        self.logger.debug("analysis.json file created")
        js_file = open("run-time-objs/analysis.json", "w")
        json.dump(js_obj, js_file, indent=4)
        js_file.close()

        return True
