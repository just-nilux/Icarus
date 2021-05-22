import talib as tl
import pandas as pd
import logging

logger = logging.getLogger('app.{}'.format(__name__))

async def get_atr(kline):
    print(kline)
    df = pd.DataFrame(kline)
    print(df)
    result = tl.ATR(df[2],df[3],df[4])
    return {}

async def default_analyzer(pair_list):
    logger.debug("default_analyzer started")
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

    logger.debug("default_analyzer ended")
    return analysis_objs
