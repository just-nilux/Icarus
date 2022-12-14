from statistics import mean
import numpy as np
import pandas as pd
from ..utils import time_scale_to_minute
from ..objects import ECause, EState
import copy
import asyncio
from dataclasses import asdict
import itertools

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


async def supres_tables_per_metric(index, analysis_data):
    metrics = ['vertical_distribution_score', 'horizontal_distribution_score', 'distribution_score',
        'number_of_members', 'distribution_efficiency', 'number_of_retest', 'number_of_cluster']

    timeframes_x_algo = []
    for  clusters in analysis_data:
        timeframes_x_algo.append(pd.DataFrame([asdict(cluster) for cluster in clusters], columns=metrics))

    tuple_index = pd.MultiIndex.from_tuples(list(map(tuple, index)))
    df_timeframes_x_algo_mean = pd.DataFrame(index=tuple_index, columns=timeframes_x_algo[0].columns)

    for tuple_indice, df_tf_x_algo in zip(tuple_index,timeframes_x_algo):
        df_timeframes_x_algo_mean.loc[tuple_indice] = df_tf_x_algo.mean()
        df_timeframes_x_algo_mean.loc[tuple_indice, 'number_of_cluster'] = len(df_tf_x_algo)

    tables_per_metric = {}
    for metric in metrics:
        df_unstacked = df_timeframes_x_algo_mean[metric].unstack(level=2).astype(float)

        # Hack for retaining the index order after unstack operation
        level0 = df_timeframes_x_algo_mean[metric].index.get_level_values(0).unique()
        level1 = df_timeframes_x_algo_mean[metric].index.get_level_values(1).unique()
        tables_per_metric[metric] = df_unstacked.reindex(list(itertools.product(*[level0, level1])))

    return tables_per_metric


async def supres_tables_per_algo(index, analysis_data):
    metrics = ['vertical_distribution_score', 'horizontal_distribution_score', 'distribution_score',
        'number_of_members', 'distribution_efficiency', 'number_of_retest', 'number_of_cluster']

    timeframes_x_algo = []
    for  clusters in analysis_data:
        timeframes_x_algo.append(pd.DataFrame([asdict(cluster) for cluster in clusters], columns=metrics))

    tuple_index = pd.MultiIndex.from_tuples(list(map(tuple, index)))
    df_timeframes_x_algo_mean = pd.DataFrame(index=tuple_index, columns=timeframes_x_algo[0].columns)

    for tuple_indice, df_tf_x_algo in zip(tuple_index,timeframes_x_algo):
        df_timeframes_x_algo_mean.loc[tuple_indice] = df_tf_x_algo.mean()
        df_timeframes_x_algo_mean.loc[tuple_indice, 'number_of_cluster'] = len(df_tf_x_algo)

    algos = df_timeframes_x_algo_mean.index.get_level_values(2).unique()
    tables_per_algo = {algo:df_timeframes_x_algo_mean.xs(algo, level=2, drop_level=True) for algo in algos}

    return tables_per_algo


async def supres_tables_per_timeframe(index, analysis_data):
    metrics = ['vertical_distribution_score', 'horizontal_distribution_score', 'distribution_score',
        'number_of_members', 'distribution_efficiency', 'number_of_retest', 'number_of_cluster']

    timeframes_x_algo = []
    for  clusters in analysis_data:
        timeframes_x_algo.append(pd.DataFrame([asdict(cluster) for cluster in clusters], columns=metrics))

    tuple_index = pd.MultiIndex.from_tuples(list(map(tuple, index)))
    df_timeframes_x_algo_mean = pd.DataFrame(index=tuple_index, columns=timeframes_x_algo[0].columns)

    for tuple_indice, df_tf_x_algo in zip(tuple_index,timeframes_x_algo):
        df_timeframes_x_algo_mean.loc[tuple_indice] = df_tf_x_algo.mean()
        df_timeframes_x_algo_mean.loc[tuple_indice, 'number_of_cluster'] = len(df_tf_x_algo)

    timeframes = df_timeframes_x_algo_mean.index.get_level_values(1).unique()
    tables_per_algo = {tf:df_timeframes_x_algo_mean.xs(tf, level=1, drop_level=True) for tf in timeframes}

    return tables_per_algo


async def supres_distribution_per_metric(index, analysis_data):
    metrics = ['vertical_distribution_score', 'horizontal_distribution_score', 'distribution_score',
        'number_of_members', 'distribution_efficiency', 'number_of_retest']

    timeframes_x_algo = []
    for  clusters in analysis_data:
        timeframes_x_algo.append(pd.DataFrame([asdict(cluster) for cluster in clusters], columns=metrics))

    result_dict = {}
    for metric in metrics:
        metric_dict = {}
        for idx, tf_x_algo in zip(index, timeframes_x_algo):
            metric_dict[idx[-1]] = tf_x_algo[metric]
        result_dict[metric] = metric_dict 

    # result_dict: 
    # 1h timeframe
    # {
    #   number_of_retest: {sr_dbscan:number_of_retest, sr_birch:number_of_retest,...}, # Plot
    #   number_of_members: {sr_dbscan:number_of_members, sr_birch:number_of_members,...},
    #   ...
    # }
    # The results will go to box plots so for each metric
    return result_dict

async def dummy_reporter(index, analysis_data):
    return analysis_data

async def strategy_statistics(index, reporter_input):

    df = pd.DataFrame(reporter_input[0])

    stats = {}

    # Count
    stat_count = {}
    stat_count['live'] = (df['status'] != EState.CLOSED).sum()
    stat_count['closed'] = (df['status'] == EState.CLOSED).sum()

    count_cause = df['cause'].value_counts()
    for cause in ECause:
        stat_count[cause.value] = count_cause.get(cause,0)

    count_updated = df['is_updated'].value_counts()
    stat_count['not_updated'] = count_updated.get(False, 0)
    stat_count['updated'] = count_updated.get(True, 0)
    stat_count['win'] = (df['profit'] > 0).sum()
    stat_count['lose'] = (df['profit'] <= 0).sum()

    stat_profit = {
        'best': df['profit'].max(),
        'worst': df['profit'].min(),
        'total': df['profit'].sum(),
        'total_updated': df[df['is_updated']==True]['profit'].sum(),
        'total_not_updated': df[df['is_updated']==False]['profit'].sum(),
        'average': df['profit'].mean(),
        'average_updated': df[df['is_updated']==True]['profit'].mean(),
        'average_not_updated': df[df['is_updated']==False]['profit'].mean()  
    }

    day_in_ms = 1000*60*60*24
    stat_duration = {
        'max': df['duration'].max()/day_in_ms,
        'min': df['duration'].min()/day_in_ms,
        'total': df['duration'].sum()/day_in_ms,
        'average': df['duration'].mean()/day_in_ms
    }

    stat_rates = {
        'win': (df['profit'] > 0).sum() / len(df['profit']),
        'lose': (df['profit'] <= 0).sum() / len(df['profit']),
        'enter': (df['cause'] != ECause.ENTER_EXP).sum() / len(df)
    }

    stat_others = {
        'total_fee': df['fee'].sum()

    }

    # Combine Stats
    stats = {
        'strategy': df['strategy'][0],
        'count': stat_count,
        'profit': stat_profit,
        'duration':stat_duration,
        'rates': stat_rates,
        'others': stat_others
    }

    # Round all floats to 2
    for stat_key, stat in stats.items():
        if type(stat) != dict:
            continue
        
        for k,v in stat.items():
            if type(v) in [np.float64, float]:
                stat[k] = round(v,2)
            elif type(v) == np.int64:
                stat[k] = int(v)

    return stats
