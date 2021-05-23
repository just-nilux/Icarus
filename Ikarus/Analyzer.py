'''
Analyzers are the units that can be configured to provide certain analytics regarding target pairs
Analyzer is the first step of simplification.
'''

import talib as tl
import pandas as pd
import logging


class Analyzer():

    def __init__(self):
        self.logger = logging.getLogger('app.{}'.format(__name__))

        return


    async def default_analyzer(self, pair_list):
        """This functions returns default analyzer object

        Args:
            pair_list (list): List of currency pair

        Returns:
            dict: analysis.json
        """    
        self.logger.debug("default_analyzer started")
        analysis_objs = []

        for pair in pair_list:
            analysis_obj = dict()
            analysis_obj["pair"] = pair
            analysis_obj["monthly"] = {}
            analysis_obj["weekly"] = {}
            analysis_obj["daily"] = {}
            analysis_obj["hourly"] = {}
            analysis_obj["15min"] = {}
            analysis_objs.append(analysis_obj)

        self.logger.debug("default_analyzer ended")
        return analysis_objs