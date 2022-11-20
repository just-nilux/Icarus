
# Table of Contents
0. [Purpose](#purpose)
1. [Method](#method)
2. [Results](#results)
    * [Correlation](#correlation)
    * [Possible Max-Min Price Change](#possible-max-min-price-change)
    * [Max-Min Price Change Distribution](#max-min-price-change-distribution)
    * [Threshold Exceed Possibility](#threshold-exceed-possibility-with-market-states)
3. [Future Works](#future-works)
# Purpose
Purpose of this research is to find out: "What is the possibility of making %1 profit during next 24 hours?". As an artifact, the distribution plots of max profit, max loss and the chance of %1 profit is generated.

As a result, it is aimed to reveal the most probable daily steady profit level.

# Method
Using the '1h' time frame, for each candlestick, evaluating the lowest and highest price change in percentage. 10 pairs have been choosen as a benchmark and the correlation levels of these pairs are taken into the account to have a diverse and generalized results.
## Market Regime Based Filtering
At certain market states the probability of making %x percent might be much more higher compare to a random time.
Considering the results of [aroon_classifies_market](./aroon_classifies_market.md), following research can be made:
* "PPC accuracy" "market_class_aroon" "1d": Good at detecting uptrend downtrend. PVPC is significantly lower. 

        [{"timeperiod":14, "th":0}]
* "PPC accuracy" "market_class_aroon" "1h": Good at detecting rangeing market. PVPC is even better. 

        [{"timeperiod":14, "th":0}]

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

* Since more stabil pairs are less volatile, the percentage change possibility for these pairs are lower. When perc_pos_change_stats_in_market_class_BTCUSDT_1h and perc_pos_change_stats_in_market_class_EURUSDT_1h compared the difference in 0.001 is significant. It is also visible in occurence plots.
* When the 1d timeframe investigated over different pairs the %1 possibility is always above %90 (except EURUSDT) just like -%1. Which comes the first is not investigated for the sake of simplicity.
* When the 1h timeframes are compared with the 1d of the same pairs. the possibilities in high percentage changes drops significantly. But still the +%1 percentage is around %80.
* In both timeframe and all pairs the negative and positive change percentages are close for each threshold value. It indicates a sideway move, since the timeframe is 24 candle in both 1h and 1d, even the sudden changes are swallowed in this moving windows.
* From the market regime point of view, the downtrends has higher possibility on neg_change and less in pos_change. It is vice versa in uptrend. Ranging market possibility values are generally greater than the ones in downtrend and less then the ones in uptrend. However the difference is not significant.

As a result, it makes sense to have a dummy limit order placing strategy. But it should not have stop limit orders because the order of positive or negative %1 change is not known. As a backup, a market order can be placed to terminate the trade after 24 candle.

As a additional filter to the strategy description above the market states can also be applied to increase the possibilities.


## Correlation
The choosen pairs and the correlation:

        ["BTCUSDT", "ETHUSDT", "XRPUSDT", "SOLUSDT", "CHZUSDT", "SHIBUSDT", "EURUSDT"]

<img src="../../configs/research/daily_steady_profit/reports_correlation/correlation_matrix_symbol_1d.png" /> 

## Possible Max-Min Price Change
|Possible Max-Min Price Change||
|:---:|:---:|
|BTCUSDT|<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_raw_BTCUSDT_1h.png" width="1280"/>|
|CHZUSDT|<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_raw_CHZUSDT_1h.png" width="1280"/>|
|EURUSDT|<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_raw_EURUSDT_1h.png" width="1280"/>|

## Max-Min Price Change Distribution

|Max-Min Price Change Distribution|1h|
|:---|:-----------------|
|BTCUSDT|<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_occurence_BTCUSDT_1h.png" width="1280"/>|
|CHZUSDT|<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_occurence_CHZUSDT_1h.png" width="1280"/>|
|EURUSDT|<img src="../../configs/research/daily_steady_profit/reports/perc_pos_change_occurence_EURUSDT_1h.png" width="1280"/>|


## Threshold Exceed Possibility with Market States

### 1h

**<font color="yellow">market_class_table_stats_1h_BTCUSDT_market_class_aroon</font>**
|                  |   downtrend |   ranging |   uptrend |
|:-----------------|------------:|----------:|----------:|
| Occurence        |      269    |    462    |    251    |
| Average PPC      |       -0.85 |      0.05 |      0.51 |
| Average PVPC     |       -0.85 |      0.05 |      0.51 |
| None PVPC        |        0    |      0    |      0    |
| Average duration |        4    |      6    |      4    |
| Coverage         |   122000    | 285200    | 113300    |
| PPC Accuracy     |       30.11 |     77.49 |     25.5  |
| PVPC Accuracy    |       30.11 |     77.49 |     25.5  |

<img src="../../configs/research/daily_steady_profit/reports_market_class/perc_pos_change_stats_in_market_class_BTCUSDT_1h.png" />

**<font color="yellow">market_class_table_stats_1h_CHZUSDT_market_class_aroon</font>**
|                  |   downtrend |   ranging |   uptrend |
|:-----------------|------------:|----------:|----------:|
| Occurence        |      255    |    472    |    270    |
| Average PPC      |       -1.11 |      0    |      1.2  |
| Average PVPC     |       -1.11 |      0    |      1.2  |
| None PVPC        |        0    |      0    |      0    |
| Average duration |        4    |      5    |      4    |
| Coverage         |   119600    | 276700    | 122600    |
| PPC Accuracy     |       43.14 |     47.67 |     41.11 |
| PVPC Accuracy    |       43.14 |     47.67 |     41.11 |

<img src="../../configs/research/daily_steady_profit/reports_market_class/perc_pos_change_stats_in_market_class_CHZUSDT_1h.png" />

**<font color="yellow">market_class_table_stats_1h_ETHUSDT_market_class_aroon</font>**
|                  |   downtrend |   ranging |   uptrend |
|:-----------------|------------:|----------:|----------:|
| Occurence        |      262    |    473    |    255    |
| Average PPC      |       -1.08 |     -0.05 |      0.87 |
| Average PVPC     |       -1.08 |     -0.05 |      0.87 |
| None PVPC        |        0    |      0    |      0    |
| Average duration |        4    |      5    |      4    |
| Coverage         |   122400    | 276700    | 120000    |
| PPC Accuracy     |       39.31 |     63.21 |     32.94 |
| PVPC Accuracy    |       39.31 |     63.21 |     32.94 |

<img src="../../configs/research/daily_steady_profit/reports_market_class/perc_pos_change_stats_in_market_class_ETHUSDT_1h.png" />

**<font color="yellow">market_class_table_stats_1h_EURUSDT_market_class_aroon</font>**
|                  |   downtrend |   ranging |   uptrend |
|:-----------------|------------:|----------:|----------:|
| Occurence        |      260    |       329 |    244    |
| Average PPC      |       -0.13 |        -0 |      0.08 |
| Average PVPC     |       -0.13 |        -0 |      0.08 |
| None PVPC        |        0    |         0 |      0    |
| Average duration |        7    |         5 |      6    |
| Coverage         |   196600    |    187800 | 169900    |
| PPC Accuracy     |        2.69 |       100 |      2.87 |
| PVPC Accuracy    |        2.69 |       100 |      2.87 |

<img src="../../configs/research/daily_steady_profit/reports_market_class/perc_pos_change_stats_in_market_class_EURUSDT_1h.png" />

**<font color="yellow">market_class_table_stats_1h_SHIBUSDT_market_class_aroon</font>**
|                  |   downtrend |   ranging |   uptrend |
|:-----------------|------------:|----------:|----------:|
| Occurence        |      252    |    470    |    243    |
| Average PPC      |       -1.26 |      0.03 |      1.03 |
| Average PVPC     |       -1.26 |      0.03 |      1.03 |
| None PVPC        |        0    |      0    |      0    |
| Average duration |        4    |      6    |      4    |
| Coverage         |   115500    | 293900    | 107800    |
| PPC Accuracy     |       42.46 |     60    |     34.57 |
| PVPC Accuracy    |       42.46 |     60    |     34.57 |

<img src="../../configs/research/daily_steady_profit/reports_market_class/perc_pos_change_stats_in_market_class_SHIBUSDT_1h.png" />

**<font color="yellow">market_class_table_stats_1h_SOLUSDT_market_class_aroon</font>**
|                  |   downtrend |   ranging |   uptrend |
|:-----------------|------------:|----------:|----------:|
| Occurence        |      271    |    481    |    253    |
| Average PPC      |       -1.17 |     -0.02 |      1.04 |
| Average PVPC     |       -1.17 |     -0.02 |      1.04 |
| None PVPC        |        0    |      0    |      0    |
| Average duration |        4    |      5    |      4    |
| Coverage         |   131400    | 261900    | 125300    |
| PPC Accuracy     |       42.07 |     49.48 |     41.11 |
| PVPC Accuracy    |       42.07 |     49.48 |     41.11 |

<img src="../../configs/research/daily_steady_profit/reports_market_class/perc_pos_change_stats_in_market_class_SOLUSDT_1h.png" />

**<font color="yellow">market_class_table_stats_1h_XRPUSDT_market_class_aroon</font>**
|                  |   downtrend |   ranging |   uptrend |
|:-----------------|------------:|----------:|----------:|
| Occurence        |      250    |    446    |    246    |
| Average PPC      |       -0.96 |     -0.02 |      0.96 |
| Average PVPC     |       -0.96 |     -0.02 |      0.96 |
| None PVPC        |        0    |      0    |      0    |
| Average duration |        4    |      6    |      4    |
| Coverage         |   116500    | 283100    | 118700    |
| PPC Accuracy     |       36.8  |     65.02 |     32.52 |
| PVPC Accuracy    |       36.8  |     65.02 |     32.52 |

<img src="../../configs/research/daily_steady_profit/reports_market_class/perc_pos_change_stats_in_market_class_XRPUSDT_1h.png" />

### 1d

**<font color="yellow">market_class_table_stats_1d_BTCUSDT_market_class_aroon</font>**
|                  |   downtrend |   ranging |   uptrend |
|:-----------------|------------:|----------:|----------:|
| Occurence        |       11    |     19    |      9    |
| Average PPC      |       -5.93 |     -0.52 |      0.94 |
| Average PVPC     |       -5.93 |     -0.52 |      0.94 |
| None PVPC        |        0    |      0    |      0    |
| Average duration |        5    |      5    |      4    |
| Coverage         |     5700    |  10300    |   4000    |
| PPC Accuracy     |       54.55 |     31.58 |     44.44 |
| PVPC Accuracy    |       54.55 |     31.58 |     44.44 |

<img src="../../configs/research/daily_steady_profit/reports_market_class/perc_pos_change_stats_in_market_class_BTCUSDT_1d.png" />

**<font color="yellow">market_class_table_stats_1d_CHZUSDT_market_class_aroon</font>**
|                  |   downtrend |   ranging |   uptrend |
|:-----------------|------------:|----------:|----------:|
| Occurence        |       11    |     20    |     10    |
| Average PPC      |       -4.61 |      0.16 |      8.51 |
| Average PVPC     |       -4.61 |      0.16 |      8.51 |
| None PVPC        |        0    |      0    |      0    |
| Average duration |        4    |      5    |      5    |
| Coverage         |     4400    |  10200    |   5500    |
| PPC Accuracy     |       54.55 |     10    |     60    |
| PVPC Accuracy    |       54.55 |     10    |     60    |

<img src="../../configs/research/daily_steady_profit/reports_market_class/perc_pos_change_stats_in_market_class_CHZUSDT_1d.png" />

**<font color="yellow">market_class_table_stats_1d_ETHUSDT_market_class_aroon</font>**
|                  |   downtrend |   ranging |   uptrend |
|:-----------------|------------:|----------:|----------:|
| Occurence        |       11    |     17    |      7    |
| Average PPC      |      -10.05 |      1.17 |      4.92 |
| Average PVPC     |      -10.05 |      1.17 |      4.92 |
| None PVPC        |        0    |      0    |      0    |
| Average duration |        5    |      5    |      6    |
| Coverage         |     5900    |  10000    |   4200    |
| PPC Accuracy     |       63.64 |     11.76 |     57.14 |
| PVPC Accuracy    |       63.64 |     11.76 |     57.14 |

<img src="../../configs/research/daily_steady_profit/reports_market_class/perc_pos_change_stats_in_market_class_ETHUSDT_1d.png" />

**<font color="yellow">market_class_table_stats_1d_EURUSDT_market_class_aroon</font>**
|                  |   downtrend |   ranging |   uptrend |
|:-----------------|------------:|----------:|----------:|
| Occurence        |       13    |     20    |     11    |
| Average PPC      |       -1.04 |      0.29 |     -0.59 |
| Average PVPC     |       -1.04 |      0.29 |     -0.59 |
| None PVPC        |        0    |      0    |      0    |
| Average duration |        6    |      4    |      3    |
| Coverage         |     7900    |   8900    |   3900    |
| PPC Accuracy     |       46.15 |     85    |      0    |
| PVPC Accuracy    |       46.15 |     85    |      0    |


<img src="../../configs/research/daily_steady_profit/reports_market_class/perc_pos_change_stats_in_market_class_EURUSDT_1d.png" />

**<font color="yellow">market_class_table_stats_1d_SHIBUSDT_market_class_aroon</font>**
|                  |   downtrend |   ranging |   uptrend |
|:-----------------|------------:|----------:|----------:|
| Occurence        |        9    |     16    |      8    |
| Average PPC      |       -6.61 |     -2.52 |      8.81 |
| Average PVPC     |       -6.61 |     -2.52 |      8.81 |
| None PVPC        |        0    |      0    |      0    |
| Average duration |        4    |      8    |      3    |
| Coverage         |     4100    |  13200    |   2900    |
| PPC Accuracy     |       55.56 |      6.25 |     62.5  |
| PVPC Accuracy    |       55.56 |      6.25 |     62.5  |


<img src="../../configs/research/daily_steady_profit/reports_market_class/perc_pos_change_stats_in_market_class_SHIBUSDT_1d.png" />

**<font color="yellow">market_class_table_stats_1d_SOLUSDT_market_class_aroon</font>**
|                  |   downtrend |   ranging |   uptrend |
|:-----------------|------------:|----------:|----------:|
| Occurence        |       12    |     17    |      6    |
| Average PPC      |       -7.73 |     -2.03 |      9.37 |
| Average PVPC     |       -7.73 |     -2.03 |      9.37 |
| None PVPC        |        0    |      0    |      0    |
| Average duration |        4    |      6    |      5    |
| Coverage         |     5400    |  11300    |   3300    |
| PPC Accuracy     |       58.33 |      5.88 |     66.67 |
| PVPC Accuracy    |       58.33 |      5.88 |     66.67 |

<img src="../../configs/research/daily_steady_profit/reports_market_class/perc_pos_change_stats_in_market_class_SOLUSDT_1d.png" />

**<font color="yellow">market_class_table_stats_1d_XRPUSDT_market_class_aroon</font>**
|                  |   downtrend |   ranging |   uptrend |
|:-----------------|------------:|----------:|----------:|
| Occurence        |       12    |     18    |      9    |
| Average PPC      |       -5.76 |     -0.1  |      3.85 |
| Average PVPC     |       -5.76 |     -0.1  |      3.85 |
| None PVPC        |        0    |      0    |      0    |
| Average duration |        4    |      6    |      3    |
| Coverage         |     5200    |  11800    |   3100    |
| PPC Accuracy     |       58.33 |     16.67 |     44.44 |
| PVPC Accuracy    |       58.33 |     16.67 |     44.44 |

<img src="../../configs/research/daily_steady_profit/reports_market_class/perc_pos_change_stats_in_market_class_XRPUSDT_1d.png" />

# Future Works
* The consecutive duration of each threshold value exceed time can be investigated.