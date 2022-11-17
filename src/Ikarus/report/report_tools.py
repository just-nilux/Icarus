from statistics import mean
import numpy as np
import pandas as pd
from ..utils import time_scale_to_minute
import copy
import asyncio
from dataclasses import asdict

accuracy_conditions_for_ppc = {
    'downtrend': lambda a,count : (np.array(a) < -1 ).sum() / count * 100,
    'uptrend': lambda a,count : (np.array(a) > 1 ).sum() / count * 100,
    'ranging': lambda a,count : ((np.array(a) > -1) & (np.array(a) < 1)).sum() / count * 100,
}

async def ohlcv(indices, analysis):
    df = analysis[0][['open', 'high', 'low', 'close', 'volume']]
    df.set_index(np.array(df.index).astype('datetime64[ms]'), inplace=True)
    return df


async def perc_pos_change_raw(indices, analysis):
    return analysis[0].set_index(np.array(analysis[0].index).astype('datetime64[ms]'))


async def perc_pos_change_occurence(indices, analysis):
    return pd.DataFrame([analysis[0]['pos_change'].value_counts(), analysis[0]['neg_change'].value_counts()]).T


async def perc_pos_change_stats(indices, analysis):
    df = analysis[0]
    pos_change_thresholds = [0.0025, 0.005, 0.01, 0.02, 0.03, 0.04, 0.05]

    #statistic_dict = {
    #    "count": len(df),
    #    "average_pos_change": round(df['pos_change'].mean(), 4 ),
    #    "average_neg_change": round(df['neg_change'].mean(), 4 )
    #}

    table = []
    for th in pos_change_thresholds:
        #statistic_dict[key] = round((df['pos_change'] > value).sum()/len(df), 2 )
        table.append([
            round((df['pos_change'] > th).sum()/len(df), 2 ),
            round((df['neg_change'] < -th).sum()/len(df), 2 )
        ])
    df_th = pd.DataFrame(table, columns=['pos_change','neg_change'], index=list(map(lambda x: str(x).replace('.','_'), pos_change_thresholds)))
    #statistic_dict['threshold_table'] = df_th.to_dict()
    return df_th.T.to_dict()


async def correlation_matrix(indices, analysis):
    df = pd.DataFrame(analysis, index=[indice[0] for indice in indices]).T
    #logretdf = np.log(df.pct_change() + 1)
    pct_changedf = df.pct_change()
    return pct_changedf.corr()

# *ppc: price percentage change
async def market_class_ppc(index, detected_market_regimes):
    tabular_dict = {}
    for regime_name, regime_instances in detected_market_regimes[0].items():
        perc_price_change_list = [instance.perc_price_change for instance in regime_instances]
        tabular_dict[regime_name] = perc_price_change_list
    return tabular_dict


async def market_class_pvpc(index, detected_market_regimes):
    tabular_dict = {}
    for regime_name, regime_instances in detected_market_regimes[0].items():
        perc_val_price_change_list = [instance.perc_val_price_change for instance in regime_instances if instance.perc_val_price_change != None]
        tabular_dict[regime_name] = perc_val_price_change_list
    return tabular_dict


async def market_class_table_stats(index, detected_market_regimes):

    tabular_dict = {}
    for regime_name, regime_instances in detected_market_regimes[0].items():
        # "Exception has occurred: ValueError: not enough values to unpack..." error fixed
        if not regime_instances:
            continue
        perc_price_change_list, perc_val_price_change_list, duration_in_candle_list = list(map(np.array, zip(
            *[[instance.perc_price_change, instance.perc_val_price_change, instance.duration_in_candle] for instance in regime_instances])))
        regime_stats = {}
        regime_stats['Occurence'] = int(len(regime_instances))
        regime_stats['Average PPC'] = round(mean(perc_price_change_list),2)
        regime_stats['Average PVPC'] = round(perc_val_price_change_list[perc_val_price_change_list != None].mean(),2) # TODO: <string>:1: RuntimeWarning: Mean of empty slice.
        regime_stats['None PVPC'] = round(sum(x is None for x in perc_val_price_change_list)/len(regime_instances)*100,2)
        regime_stats['Average duration'] = int(mean(duration_in_candle_list))
        regime_stats['Coverage'] = round(sum(duration_in_candle_list) / len(index) * 100,2)
        regime_stats['PPC Accuracy'] = round(
            accuracy_conditions_for_ppc[regime_name](perc_price_change_list, len(regime_instances)),2)
        regime_stats['PVPC Accuracy'] = round(
            accuracy_conditions_for_ppc[regime_name](perc_val_price_change_list[perc_val_price_change_list != None], len(regime_instances)),2)

        tabular_dict[regime_name] = regime_stats
    
    return tabular_dict


async def perc_pos_change_stats_in_market_class(index, detected_market_regimes):
    market_regimes = detected_market_regimes[0]
    df_change = copy.deepcopy(detected_market_regimes[1])
    df_change['downtrend'] = False

    perc_price_change_list = [(instance.start_ts, instance.end_ts)  for instance in market_regimes['downtrend']]
    #step_ts = time_scale_to_minute(index[0][1]) * 60 * 1000
    #start_ts = regime_instances[0]
    #end_ts = regime_instances[-1]

    coroutines = []
    results = []
    coroutines.append(perc_pos_change_stats(index, [df_change]))

    for regime_name, regime_instances in market_regimes.items():
        df_change[regime_name] = False
        for instance in regime_instances:
            df_change.loc[instance.start_ts:instance.end_ts, regime_name]=True
        coroutines.append(perc_pos_change_stats(index, [df_change[df_change[regime_name]]]))

    results = await asyncio.gather(*coroutines)
    result_dict = {key:value for key, value in zip(['all'] + list(market_regimes.keys()), results)}

    # NOTE: FOR '1d':
    # I think the results are meaningful. As expected in downtrend,
    # neg_change possibility is higher and pos_change is lower. It is vice-versa in
    # uptrend
    return result_dict


async def sup_res_metrics(index, analysis_data):
    metrics = ['vertical_distribution_score', 'horizontal_distribution_score', 'distribution_score',
        'number_of_members', 'number_of_retest']

    timeframes_x_algo = []
    for  clusters in analysis_data:
        timeframes_x_algo.append(pd.DataFrame([asdict(cluster) for cluster in clusters], columns=metrics))

    tuple_index = pd.MultiIndex.from_tuples(list(map(tuple, index)))
    df_timeframes_x_algo_mean = pd.DataFrame(index=tuple_index, columns=timeframes_x_algo[0].columns)

    for tuple_indice, df_tf_x_algo in zip(tuple_index,timeframes_x_algo):
        df_timeframes_x_algo_mean.loc[tuple_indice] = df_tf_x_algo.mean()
    
    
    # Heatmap 1
    '''
    [Pair]
    [ClusteringAlgo]
    | | HDS | VDS | ... |
    |:-:|:-:|:-:|:-:|
    | 1h | x | x | x |
    | 4h | x | x | x |
    | ... | x | x | x |
    '''

    coroutines = []

    algos = df_timeframes_x_algo_mean.index.get_level_values(2).unique()
    per_algo_tables = {}

    

    return result_dict