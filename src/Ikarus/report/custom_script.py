import json
import sys
import os
import asyncio
from binance import AsyncClient
from .. import broker
import datetime
from itertools import chain
import itertools
from ..analyzers import Analyzer
from .. import mongo_utils
from . import report_tools
from .report_writer import ReportWriter
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def get_coordites(mongo_dict):
    _,x,y = mongo_dict['folder_name'].split('_')
    mongo_dict['validation_threshold'] = x
    mongo_dict['timeperiod'] = y
    return mongo_dict

def query_to_table(query_result):
    for mongo_dict in query_result:
        get_coordites(mongo_dict)
        x = 1
    
    df = pd.DataFrame(query_result)
    tabular_df = pd.DataFrame(np.nan,index=df['timeperiod'].unique(), columns=df['validation_threshold'].unique())

    for result in query_result:
        if 'ppc' in result.keys():
            tabular_df[result['validation_threshold']][result['timeperiod']] = result['ppc']
    #print(tabular_df.to_html())
    return tabular_df



def sample():
    # https://pandas.pydata.org/pandas-docs/stable/user_guide/advanced.html
    #df2 = pd.DataFrame(np.random.randn(6, 6), index=index[:6], columns=index[:6])
    pass

async def main():
    config['mongodb']['clean'] = False
    mongo_client = mongo_utils.MongoClient(db='reports', **config['mongodb'])

    # Indice format: ()
    report_tool_coroutines = []
    indices = []

    analyzers = ["market_class_aroon", "market_class_fractal_aroon", "market_class_aroonosc"]
    market_regimes = ["downtrend", "ranging", "uptrend"]    
    indices = list(itertools.product(analyzers, market_regimes))
    collection = [
        {"$match":{"analyzer":{"$eq":"market_class_fractal_aroon"}}},
        {"$project": {"ppc": "$data.downtrend.PPC Accuracy (%)", "folder_name": "$folder_name" }}
    ]

    big_df = pd.DataFrame(index=analyzers, columns=market_regimes)

    for analyzer in analyzers:
        for market_regime in market_regimes:
            collection = [
                {"$match":{"analyzer":{"$eq":analyzer}}},
                {"$project": {"ppc": f"$data.{market_regime}.PPC Accuracy (%)", "folder_name": "$folder_name" }}
            ]
            print(analyzer, market_regime)
            #report_tool_coroutines.append(mongo_client.do_aggregate("market_class_table_stats", collection))
            x = await mongo_client.do_aggregate("market_class_table_stats", collection)
            tabular_df = query_to_table(x)
            big_df[market_regime][analyzer] = tabular_df.values

    vertical_array_stack = [np.concatenate(big_df.values[i], axis=1) for i in range(len(big_df.index))]
    big_matrix = np.concatenate(vertical_array_stack, axis=0)
    fig, ax = plt.subplots()
    heatmap = ax.pcolor(big_matrix, cmap=plt.cm.seismic, 
                        vmin=np.nanmin(big_matrix), vmax=np.nanmax(big_matrix))
    ax.patch.set(hatch='x', edgecolor='black')
    fig.colorbar(heatmap)
    plt.show() 

if __name__ == '__main__':
    print(sys.argv)
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

