from statistics import mean, stdev
import numpy as np
import pandas as pd
from ..utils import time_scale_to_minute
from ..objects import ECause, EState, Report, ReportMeta
from ..safe_operators import safe_divide, safe_sum, safe_substract
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

    stat_absolute_profit = {
        'best': df['profit'].max(),
        'worst': df['profit'].min(),
        'total': df['profit'].sum(),
        'total_updated': df[df['is_updated']==True]['profit'].sum(),
        'total_not_updated': df[df['is_updated']==False]['profit'].sum(),
        'average': df['profit'].mean(),
        'average_updated': df[df['is_updated']==True]['profit'].mean(),
        'average_not_updated': df[df['is_updated']==False]['profit'].mean()
    }

    stat_percentage_profit = {
        'best': df['percentage_profit'].max(),
        'worst': df['percentage_profit'].min(),
        'total': df['percentage_profit'].sum(),
        'total_updated': df[df['is_updated']==True]['percentage_profit'].sum(),
        'total_not_updated': df[df['is_updated']==False]['percentage_profit'].sum(),
        'average': df['percentage_profit'].mean(),
        'average_updated': df[df['is_updated']==True]['percentage_profit'].mean(),
        'average_not_updated': df[df['is_updated']==False]['percentage_profit'].mean()
    }

    stat_price_change = {
        'best': df['price_change'].max(),
        'worst': df['price_change'].min(),
        'total': df['price_change'].sum(),
        'total_updated': df[df['is_updated']==True]['price_change'].sum(),
        'total_not_updated': df[df['is_updated']==False]['price_change'].sum(),
        'average': df['price_change'].mean(),
        'average_updated': df[df['is_updated']==True]['price_change'].mean(),
        'average_not_updated': df[df['is_updated']==False]['price_change'].mean()
    }

    day_in_ms = 1000*60*60*24
    hour_in_ms = 1000*60*60
    durations = df['duration']/hour_in_ms
    stat_duration = {
        'max': durations.max(),
        'min': durations.min(),
        'total': durations.sum(),
        'average': durations.mean()
    }

    stat_rates = {
        'win': (df['profit'] > 0).sum() / len(df['profit']),
        'lose': (df['profit'] <= 0).sum() / len(df['profit']),
        'enter': (df['cause'] != ECause.ENTER_EXP).sum() / len(df)
    }

    stat_risk = dict()
    if 'exit_type' in df.columns and any('oco' == df['exit_type']):
        df_oco = df[df['exit_type'] == 'oco']
        df_risk = pd.DataFrame(df_oco['risk_data'].to_list())
        df_r = pd.concat([df_oco,df_risk], axis=1)
        df_r.loc[df_r['cause'] == 'limit','r_value'] = (df_risk['target_price'] - df_risk['enter_price']) / (df_risk['enter_price'] - df_risk['stop_limit_price'])
        df_r.loc[df_r['cause'] == 'stop_limit','r_value'] = -1

        stat_risk['expectancy'] = df_r['r_value'].mean()

        if len(df_oco) < 100:
            sqn_coeff = len(df_oco)
        else:
            sqn_coeff = 100
        stat_risk['SQN'] = stat_risk['expectancy']/df_r['r_value'].std() * np.sqrt(sqn_coeff)


    stat_others = {
        'total_fee': df['fee'].sum()
    }

    # Combine Stats
    stats = {
        'strategy': df['strategy'][0],
        'count': stat_count,
        'absolute_profit': stat_absolute_profit,
        'percentage_profit': stat_percentage_profit,
        'price_change': stat_price_change,
        'duration':stat_duration,
        'rates': stat_rates,
        'risk': stat_risk,
        'others': stat_others
    }

    # Round all floats to 2
    for stat_key, stat in stats.items():
        if type(stat) != dict:
            continue
        
        for k,v in stat.items():
            if type(v) in [np.float64, float]:
                stat[k] = round(v,3)
            elif type(v) == np.int64:
                stat[k] = int(v)

    return Report(ReportMeta(title='strategy_{}'.format(df['strategy'][0])), data=stats)


async def balance_statistics(index, reporter_input):

    df = pd.DataFrame(reporter_input[0])
    mdd_percentage = (df['total'].max() - df['total'].min() ) / df['total'].max() * 100


    quote_asset_start = df['total'].iloc[0]
    quote_asset_end = df['total'].iloc[-1]
    
    stats = {
        'start':quote_asset_start,
        'end':quote_asset_end,
        'absolute_profit': safe_substract(quote_asset_end, quote_asset_start, quant='0.01')
    }
    stats['percentage_profit'] = safe_divide(stats['absolute_profit']*100, stats['start'], quant='0.01')
    stats['max_drawdown'] = round(mdd_percentage,2)

    return  Report(ReportMeta(title='balance_statistics'),data=stats)


async def trade_cause(index, reporter_input):

    df = pd.DataFrame(reporter_input[0])

    count_cause = df['cause'].value_counts()

    report_meta = ReportMeta(
        title='trade.cause: {}'.format(df['strategy'][0]),
        filename='trade_cause_{}'.format(df['strategy'][0])
        )
    return  Report(report_meta, data=count_cause.to_dict())


async def trade_profit_duration_distribution(index, reporter_input):

    df = pd.DataFrame(reporter_input[0])
    df['duration'] = df['duration']/(60*60*1000)
    report_meta = ReportMeta(
        title='trade.result.profit: {}'.format(df['strategy'][0]),
        filename='trade_result_profit_{}'.format(df['strategy'][0])
        )
    return Report(report_meta, data=df[['duration', 'profit']])


async def strategy_capitals(index, reporter_input):

    df_base = pd.DataFrame(reporter_input[0])
    df = pd.DataFrame(df_base['data'].to_list(), index=df_base['ts'].astype('datetime64[ms]'))
    df['Total'] = df.sum(axis=1)

    report_meta = ReportMeta(
        title='Strategy Capitals',
        filename='strategy_capitals'
        )
    return Report(report_meta, data=df)


async def r_multiples(index, reporter_input):
    if not reporter_input[0]:
        return None
    
    df = pd.DataFrame(reporter_input[0])
    df.loc[df['cause'] == 'limit','r_value'] = (df['target_price'] - df['enter_price']) / (df['enter_price'] - df['stop_limit_price'])
    df.loc[df['cause'] == 'stop_limit','r_value'] = -1

    hour_in_ms = 1000*60*60
    df['duration']  = df['duration'] / hour_in_ms

    report_meta = ReportMeta(
        title='R Multiple Distribution {}'.format(df['strategy'][0]),
        filename='r_multiple_distribution_{}'.format(df['strategy'][0]),
        )
    return Report(report_meta, data=df[['duration','r_value']])