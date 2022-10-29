from statistics import mean
import numpy as np
import pandas as pd

accuracy_conditions_for_ppc = {
    'downtrend': lambda a,count : (np.array(a) < -1 ).sum() / count * 100,
    'uptrend': lambda a,count : (np.array(a) > 1 ).sum() / count * 100,
    'ranging': lambda a,count : ((np.array(a) > -1) & (np.array(a) < 1)).sum() / count * 100,
}


async def change_in_24h_raw(indices, analysis):
    df = pd.DataFrame(analysis).T
    df.columns = ['index','open', 'high', 'low']
    df.set_index(df['index'].astype('int64').astype('datetime64[ms]'), inplace=True)
    del df['index']

    rolling_window = 24
    df['high'] = df['high'].rolling(window=rolling_window).apply(max)
    df['low'] = df['low'].rolling(window=rolling_window).apply(min)
    df[['high','low']] = df[['high','low']].shift(-23)
    df.dropna(inplace=True)

    df['pos_change'] = round(df['high']/df['open'] - 1, 3)
    df['neg_change'] = round(df['low']/df['open'] - 1, 3)
    df.drop(['open', 'high', 'low'], axis=1, inplace=True)

    return df


async def change_in_24h_stats(indices, analysis):
    df = pd.DataFrame(analysis).T
    df.columns = ['index','open', 'high', 'low']
    rolling_window = 24
    df['high'] = df['high'].rolling(window=rolling_window).apply(max)
    df['low'] = df['low'].rolling(window=rolling_window).apply(min)
    df[['high','low']] = df[['high','low']].shift(-23)
    df = df.dropna()

    df['pos_change'] = df['high']/df['open'] - 1
    df['neg_change'] = df['low']/df['open'] - 1
    df['three_percent'] = df['pos_change'] > 0.03
    df['two_percent'] = df['pos_change'] > 0.02
    df['one_percent'] = df['pos_change'] > 0.01
    df['zero_five_percent'] = df['pos_change'] > 0.005

    statistic_dict = {
        "count": len(df),
        "average_pos_change": round(df['pos_change'].mean(), 4 ),
        "average_neg_change": round(df['neg_change'].mean(), 4 ),
        "one_percent": round(df['one_percent'].sum()/len(df), 2 ),
        "two_percent": round(df['two_percent'].sum()/len(df), 2 ),
        "three_percent": round(df['three_percent'].sum()/len(df), 2 ),
    }

    return statistic_dict


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