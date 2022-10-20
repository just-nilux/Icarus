# Table of Contents
0. [Purpose](#purpose)
1. [Method](#method)
    * [Symbols](#symbols)
    * [Calculation](#calculation)
2. [Results](#results)

# Purpose
Uncorrelated pairs are beneficial for 
* distributing risk through pairs
* testing strategies on different market dynamics

# Method

## Symbols
Since it is not feasible to evaluate correlation for all available pairs. All of the pairs are ordered based on the number of trade occured in last month (Check the config_get_most_traded_pairs.json for the configuration) by _src.Ikarus.scripts.get_most_traded_pairs_ module. The first 50 pairs are taken into the account for the correlation matrix.

## Calculation

Candlesticks with '1d' timeframe is taken into account for the last 1 year. Following snippet is used for evaluation:

    df = pd.DataFrame(analysis, index=[indice[1] for indice in indices]).T
    logretdf = np.log(df.pct_change() + 1)
    return logretdf.corr()

As default _'pearson'_ correlation is used which gives result between -1 and 1.

# Results

Pairs in order:

    ["BTCUSDT", "ETHUSDT", "LUNAUSDT", "BUSDUSDT", "XRPUSDT", "LUNCUSDT", "ATOMUSDT", "BNBUSDT", "SOLUSDT", "ETCUSDT", "RVNUSDT", "ADAUSDT", "CHZUSDT", "MATICUSDT", "APEUSDT", "LINKUSDT", "SHIBUSDT", "LTCUSDT", "DOGEUSDT", "NEARUSDT", "GMTUSDT", "SANTOSUSDT", "ANCUSDT", "AVAXUSDT", "VGXUSDT", "REEFUSDT", "EOSUSDT", "SANDUSDT", "TRXUSDT", "ALGOUSDT", "OPUSDT", "STGUSDT", "LDOUSDT", "DOTUSDT", "EURUSDT", "GALAUSDT", "FTMUSDT", "ROSEUSDT", "GALUSDT", "FILUSDT", "LAZIOUSDT", "ENSUSDT", "UNFIUSDT", "HNTUSDT", "MIRUSDT", "WAVESUSDT", "MANAUSDT", "RUNEUSDT", "JASMYUSDT", "AXSUSDT", "PORTOUSDT"]

<img src="../../configs/research/correlated_symbols/reports/correlation_matrix.png" /> 