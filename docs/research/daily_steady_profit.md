
# Table of Contents
0. [Purpose](#purpose)
1. [Method](#method)
2. [Results](#results)

# Purpose
Purpose of this research is to find out: "What is the possibility of making %1 profit during next 24 hours?". As an artifact, the distribution plots of max profit, max loss and the chance of %1 profit is generated.

As a result, it is aimed to reveal the most probable daily steady profit level.

# Method
Using the '1h' time frame, for each candlestick, evaluating the lowest and highest price change in percentage. 10 pairs have been choosen as a benchmark and the correlation levels of these pairs are taken into the account to have a diverse and generalized results.
## Market Regime Based Filtering
At certain market states the probability of making %x percent might be much more higher compare to a random time.
Considering the results of [aroon_classifies_market](./aroon_classifies_market.md), following research can be made:
* "PPC accuracy" "market_class_aroon" "1d": Good at detecting uptrend downtrend. PVPC is significantly lower.
* "PPC accuracy" "market_class_aroon" "1h": Good at detecting rangeing market. PVPC is even better.

Steps:
1. Evaluate the _df_change_ which contains _pos_change_ and _neg_change_ columns.
2. Combine all of the occurences of each class in a df column and sync the indices
   - Run the [config.json](../../configs/research/aroon_classifies_market/config.json) from [aroon_classifies_market](../../configs/research/aroon_classifies_market) and write to DB
   - Create a new config file to query 
      - all of the market regime x of _market_class_aroon_
      - the _df_change_
   - Create a report tool to consume these queries and filter the df_change based on the market regimes and direct it to report_writers

3. Use the columns from the step-2 to filter the step-1 _df_change_
3. Direct the filtered _df_change_ to the report_tools/writers as it is normally done

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



