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
from mpl_toolkits.axes_grid1 import AxesGrid


def plot_custom(sub_matrices, x_labels, y_labels, sub_x_labels, sub_y_labels):
    
    fig = plt.figure()

    grid = AxesGrid(fig, 111,
                    nrows_ncols=(len(y_labels), len(x_labels)),
                    axes_pad=0.05,
                    share_all=True,
                    label_mode="L",
                    cbar_location="right",
                    cbar_mode="single",
                    )

    for idx, (matrice, ax) in enumerate(zip(sub_matrices,grid)):
        if idx < len(x_labels):
            ax2 = ax.secondary_xaxis('top')
            ax2.tick_params(axis='x')
            ax2.set_xticks(np.arange(len(sub_x_labels)), sub_x_labels, minor=False)
            ax2.set_xlabel(x_labels[idx])

        else:
            ax.set_xticks([])

        if idx % len(y_labels) == 0:
            ax.set_ylabel(y_labels[idx % len(y_labels)])

        ax.set_yticks(np.arange(len(sub_y_labels)), sub_y_labels)
        im = ax.imshow(matrice, vmin=0, vmax=100)

    grid.cbar_axes[0].colorbar(im)

    #for cax in grid.cbar_axes:
    #    cax.toggle_label(False)

    plt.show()


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

    sub_matrices = []
    for analyzer in analyzers:
        for market_regime in market_regimes:
            collection = [
                {"$match":{"analyzer":{"$eq":analyzer}}},
                {"$project": {"ppc": f"$data.{market_regime}.PPC Accuracy (%)", "folder_name": "$folder_name" }}
            ]
            print(analyzer, market_regime)
            #report_tool_coroutines.append(mongo_client.do_aggregate("market_class_table_stats", collection))
            x = await mongo_client.do_aggregate("market_class_table_stats", collection)
            print(len(x))
            tabular_df = query_to_table(x)
            #big_df[market_regime][analyzer] = tabular_df.values
            sub_matrices.append(tabular_df.values)

    plot_custom(sub_matrices, market_regimes, analyzers, tabular_df.columns.to_list(), tabular_df.index.to_list())
    x=1

if __name__ == '__main__':
    print(sys.argv)
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

