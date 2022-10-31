
# Table of Contents
0. [Purpose](#purpose)
1. [Method](#method)
2. [Results](#results)

# Purpose
Purpose of this research is to find out: "What is the possibility of making %1 profit during next 24 hours?". As an artifact, the distribution plots of max profit, max loss and the chance of %1 profit is generated.

As a result, it is aimed to reveal the most probable daily steady profit level.

# Method
Using the '1h' time frame, for each candlestick, evaluating the lowest and highest price change in percentage. 10 pairs have been choosen as a benchmark and the correlation levels of these pairs are taken into the account to have a diverse and generalized results.

# Results

The choosen pairs and the correlation:

        ["BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "CHZUSDT", "SHIBUSDT", "EURUSDT"]

## Correlation
<img src="../../configs/research/daily_steady_profit/reports_correlation/correlation_matrix_symbol_1d.png" /> 

## Possible Max-Min Price Change
<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_raw_BTCUSDT_1h.png" />
<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_raw_CHZUSDT_1h.png" />
<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_raw_EURUSDT_1h.png" />


## Max-Min Price Change Distribution
<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_occurence_BTCUSDT_1h.png" />
<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_occurence_CHZUSDT_1h.png" />
<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_occurence_EURUSDT_1h.png" />


## Threshold Exceed Possibility
<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_stats_BTCUSDT_1h.png" /> 
<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_stats_CHZUSDT_1h.png" /> 
<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_stats_ETHUSDT_1h.png" /> 
<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_stats_EURUSDT_1h.png" /> 
<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_stats_SHIBUSDT_1h.png" /> 
<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_stats_SOLUSDT_1h.png" /> 
<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_stats_XRPUSDT_1h.png" /> 