from statistics import mean
import numpy as np
import pandas as pd

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
    return analysis[0]


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