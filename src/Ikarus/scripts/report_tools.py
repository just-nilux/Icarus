from statistics import mean
import numpy as np


accuracy_conditions_for_ppc = {
    'downtrend': lambda a,count : (np.array(a) < -1 ).sum() / count * 100,
    'uptrend': lambda a,count : (np.array(a) > 1 ).sum() / count * 100,
    'ranging': lambda a,count : ((np.array(a) > -1) & (np.array(a) < 1)).sum() / count * 100,
}

async def market_class_distribution(index, detected_market_regimes):

    tabular_dict = {}
    for regime_name, regime_instances in detected_market_regimes.items():

        price_change_perc_list = [instance.price_change_perc for instance in regime_instances]
        duration_in_candle_list = [instance.duration_in_candle for instance in regime_instances]
        regime_stats = {}
        regime_stats['Occurence'] = int(len(regime_instances))
        regime_stats['Average PPC'] = round(mean(price_change_perc_list),2)
        regime_stats['Average duration'] = int(mean(duration_in_candle_list))
        regime_stats['Coverage'] = round(sum(duration_in_candle_list) / len(index) * 100,2)
        regime_stats['PPC Accuracy'] = round(
            accuracy_conditions_for_ppc[regime_name](price_change_perc_list, len(regime_instances)),2)

        tabular_dict[regime_name] = regime_stats
    
    return tabular_dict