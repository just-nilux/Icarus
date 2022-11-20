# Table of Contents
0. [Purpose](#purpose)
    * [Questiones and Expected Answers](#questiones-and-expected-answers)
1. [Definitions](#definitions)
    * [Support](#support)
    * [Resistance](#resistance)
3. [Method](#method)
    * [Assumptions](#assumptions)
    * [Evaluation](#evaluation)
    * [Variables](#variables)
4. [Metrics](#metrics)
    * [Horizontal Distribution Score](#horizontal-distribution-score)
    * [Vertical Distribution Score](#vertical-distribution-score)
    * [Distribution Score](#distribution-score)
    * [Number of Members](#number-of-members)
    * [Number of Retest](#number-of-retest)
    * [Number of Clusters](#number-of-clusters)
6. [Results](#results)
    * [Answers to Questions](#answers-to-questions)
    * [Tables](#tables)
        * [Per Timeframe](#per-timeframe)
        * [Per Clustering Algorithm](#per-clustering-algorithm)
    * [Plots](#plots)
        * [Distribution Plots](#distribution-plots)
        * [Heatmap Plots](#heatmap-plots)
        
# Purpose
Support resistance zones are quite useful to make prediction about the possible price levels that will support or resist. Breakout of these level make indicate an end of a market regime and a start of a new one.

When placing limit or oco orders, the support-resistance zones may indicate the target price levels. This reseach only focuses on the straight horizontal sr zones not the ones with a slope or curve.

## Questiones and Expected Answers
1. What are the characteristic of each clustering algo?

    Example Output: HDS, VDS, Number of members, Number of Cluster and Number of Retest: 
    * The algorithm x generally have higher VDS score it might be used to make less precise but more reliable predictions about price action.
    * The algorithm y generally have lower HDS, it may indicate to not to use a cluster that is too far away in the past
    * The algorithm z has generally high number of clusters, it may indicate that this algo has false positives but it also makes sense to consult to it when we need a basis for the future price action prediction. Because it emits a lot of cluster and one of them may become true


1. Which clustering algorithm works better(have higher accuracy)?

    Example Output: Based on the DS scores, the algorithm x generally have higer scores then the others. The algorithm y is always has the lowest scores.

1. Which timeframes are more suitable/reliable in terms of SR levels?
    
    Example Output: "In _1d_, average DS score for all clusters are generally higher. It means that using _1d_ timeframe may create much more **meaningful/reliable** info than the timeframes _1h_ and _4h_."

1. Does it give an edge on the market to be profittable?

    Example Output: "In the timeframes x and y, the algorithm z and t creates sr zones that are generally tested multiple times after the validation. So they may create a profitable trading edge."

# Definitions
## Support
A certain price level/zone that is tested multiple times by the price action and acts as a support.
## Resistance
A certain price level/zone that is tested multiple times by the price action and acts as a resistance.

# Method

## Assumptions
Since the clustering is performed over a dataset and the features of clusters highly dependant to the data itself; it is critical to choose an optimal width(number of historical candle) for the window.

    "time_scales": {
        "1h": 336,  // 2 weeks
        "4h": 360,  // 2 months
        "1d": 365,  // 1 year
        "1w": 260,  // 5 year
    },

It can also be defended to have equal length for each timeframe but since the results are mostly relative to

## Evaluation:

Cluster based support-resistance level calculation is made in 3 steps:
1. **Simplification:** Choosing a way to evaluate candidate points. In this research, the fractal method with pattern lenth 3 and 5 is used. Check [patterns.py](../../src/Ikarus/analyzers/patterns.py)
1. **Clustering:** Choosing a clustering algorithm to cluster accumuluated candidate point. Examples: KMeans, DBSCAN, MeanShift, OPTICS, BIRCH.
1. **Validation:** Measuring the performance or accuracy of the support resistance levels

Clustering is performed over the whole chart. However if the clusters evaluated in whole chart then there will be a lot of false clusters. Thus, for each evaluation, the charts should be discrete. This logic is handled by 2 optional parameters:
* step_length
* step_to_frame_ratio

In this research the timescales are adjusted around ~300 which will lead to the parameter min_cluster_sample to be evaluated as 3 to 4.

## Variables:
- Simlification Method:

        ["fractal_line_3"]

- Pairs:

        ["","","","",""]
        
- Timeframes:

        ["1h", "4h", "1d", "1h"]

- SR Analyzers(Clustering algorithms):

        ["DBSCAN", "MeanShift", "OPTICS", "BIRCH"]


# Metrics
## Horizontal Distribution Score
(HDS): As the distance increases between datapoints, the cluster becomes more reliable since it is tested multiple different times. So we need to reward the clusters for having large distance values.

Pseudo Code:
1. Get the adjacent distance between each data point.
1. Divide the distance to the whole length of the chart to have normalized values between 0 and 1.
1. Get the weighted average of this distance array where the weights are simply an array of integers starting from 1, until the lenght of the distance array.
## Vertical Distribution Score
(VDS): Pseudo Code:
1. Get the vertical length of the cluster.
1. Divide the vertical length to the length of the chart to have a normalized value between 0 and 1
## Distribution Score 
(DS): [HDS] / [VDS]

It aims to reward a cluster due to the high HDS and also punish the cluster as the VDS values get bigger. 
## Number of Members
(NoM): Total number of members of a cluster
## Distribution Efficiency
(DE): [DS] * [NoM] = ([HDS] / [VDS]) * [NoM]

It aims to give a clue about "How well a cluster is distributed?". The well distributed cluster is a cluster where the height is small but the distance between the members are large and the number of members are also as large as possible. The ideal is a thin zone with bunch of points from the start to the end of the chunk.
## Number of Retest
(NoR): Number of Members after the valdiation point
## Number of Clusters
(NoC): Total Number of cluster that an algorithm crated

# Results
HDS, VDS, DS, NoM and NoR parameters are evaluated per cluster. For each **[timeframe] x [pair] x [algorithm]** there will be multiple of these statistics

NoC is evaluated per  **[timeframe] x [pair] x [algorithm]**

The comparisons between the pairs has the lowest importance.

## Answers to Questions
1. What are the characteristic of each clustering algo?
    * 
    * supres_tables_per_metric

        [Pair]x[Metric]
        | | DBSCAN | MeanShift | ... |
        |:-:|:-:|:-:|:-:|
        | 1h | x | x | x |
        | 4h | x | x | x |
        | ... | x | x | x |
        
    * supres_tables_per_timeframe

        [Pair]x[Timeframe]
        | | HDS | VDS | ... |
        |:-:|:-:|:-:|:-:|
        | sr_dbscan | x | x | x |
        | sr_birch | x | x | x |
        | ... | x | x | x |


1. Which clustering algorithm works better(have higher accuracy)?

    * supres_tables_per_metric

        [Pair]x[Metric]
        | | DBSCAN | MeanShift | ... |
        |:-:|:-:|:-:|:-:|
        | 1h | DS | DS | DS |
        | 4h | DS | DS | DS |
        | ... | DS | DS | DS |

1. Which timeframes are more suitable/reliable in terms of SR levels?

    [Pair]
    | | DBSCAN | MeanShift | ... |
    |:-:|:-:|:-:|:-:|
    | 1h | DS | DS | DS |
    | 4h | DS | DS | DS |
    | ... | DS | DS | DS |

    [Pair]
    | | DBSCAN | MeanShift | ... |
    |:-:|:-:|:-:|:-:|
    | 1h | NoC | NoC | NoC |
    | 4h | NoC | NoC | NoC |
    | ... | NoC | NoC | NoC |

1. Does it give an edge on the market to be profitable?

    [Pair]
    | | DBSCAN | MeanShift | ... |
    |:-:|:-:|:-:|:-:|
    | 1h | RR | RR | RR |
    | 4h | RR | RR | RR |
    | ... | RR | RR | RR |


    Retest distributions

1. What is optimal chart length?
    
    TBD

    | | Number of Member | Number of Retest | Distribution Score |
    |:--:|:--:|:--:|:--:|
    |260 |<img src="../../configs/research/support-resistance/reports_260/number_of_members_BTCUSDT_timeframe_analyzer.png" width="640"/>|<img src="../../configs/research/support-resistance/reports_260/number_of_retest_BTCUSDT_timeframe_analyzer.png" width="640"/>|<img src="../../configs/research/support-resistance/reports_260/distribution_score_BTCUSDT_timeframe_analyzer.png" width="640"/>|
    |360|<img src="../../configs/research/support-resistance/reports_360/number_of_members_BTCUSDT_timeframe_analyzer.png" width="640"/>|<img src="../../configs/research/support-resistance/reports_360/number_of_retest_BTCUSDT_timeframe_analyzer.png" width="640"/>|<img src="../../configs/research/support-resistance/reports_360/distribution_score_BTCUSDT_timeframe_analyzer.png" width="640"/>|
    |Custom|<img src="../../configs/research/support-resistance/reports_custom/number_of_members_BTCUSDT_timeframe_analyzer.png" width="640"/>|<img src="../../configs/research/support-resistance/reports_custom/number_of_retest_BTCUSDT_timeframe_analyzer.png" width="640"/>|<img src="../../configs/research/support-resistance/reports_custom/distribution_score_BTCUSDT_timeframe_analyzer.png" width="640"/>|

## Tables

### Per Timeframe

**<font color="yellow">1h_BTCUSDT_timeframe_analyzer</font>**
|                             |   vertical_distribution_score |   horizontal_distribution_score |   distribution_score |   number_of_members |   number_of_retest |   number_of_cluster |
|:----------------------------|------------------------------:|--------------------------------:|---------------------:|--------------------:|-------------------:|--------------------:|
| ('BTCUSDT', 'sr_dbscan')    |                   0.00106029  |                       0.0247727 |              31.3346 |            26.8052  |           23.8052  |                 308 |
| ('BTCUSDT', 'sr_birch')     |                   0.00112593  |                       0.0461584 |              53.406  |            12.2757  |            9.27566 |                 682 |
| ('BTCUSDT', 'sr_optics')    |                   0.000449194 |                       0.109696  |             923.849  |             4.59309 |            1.59309 |                1504 |
| ('BTCUSDT', 'sr_meanshift') |                   0.00154643  |                       0.0328082 |              30.6518 |            19.35    |           16.35    |                 440 |

**<font color="yellow">4h_BTCUSDT_timeframe_analyzer</font>**
|                             |   vertical_distribution_score |   horizontal_distribution_score |   distribution_score |   number_of_members |   number_of_retest |   number_of_cluster |
|:----------------------------|------------------------------:|--------------------------------:|---------------------:|--------------------:|-------------------:|--------------------:|
| ('BTCUSDT', 'sr_dbscan')    |                    0.00132954 |                       0.0361944 |              31.3024 |            13.493   |            9.53521 |                 142 |
| ('BTCUSDT', 'sr_birch')     |                    0.00141191 |                       0.0528393 |              42.6913 |             8.30328 |            4.33607 |                 244 |
| ('BTCUSDT', 'sr_optics')    |                    0.00134163 |                       0.0697788 |             218.056  |             6.19178 |            2.23973 |                 292 |
| ('BTCUSDT', 'sr_meanshift') |                    0.00189393 |                       0.0462692 |              26.866  |            11.967   |            8       |                 182 |

**<font color="yellow">1d_BTCUSDT_timeframe_analyzer</font>**
|                             |   vertical_distribution_score |   horizontal_distribution_score |   distribution_score |   number_of_members |   number_of_retest |   number_of_cluster |
|:----------------------------|------------------------------:|--------------------------------:|---------------------:|--------------------:|-------------------:|--------------------:|
| ('BTCUSDT', 'sr_dbscan')    |                    0.0016265  |                       0.0658214 |              47.1471 |                6.5  |               2.5  |                  28 |
| ('BTCUSDT', 'sr_birch')     |                    0.00200128 |                       0.092776  |              48.4632 |                4.96 |               0.96 |                  50 |
| ('BTCUSDT', 'sr_optics')    |                    0.00435697 |                       0.0764156 |              34.2781 |                6.25 |               2.25 |                  64 |
| ('BTCUSDT', 'sr_meanshift') |                    0.0023733  |                       0.105213  |              47.3603 |                5.4  |               1.4  |                  60 |

**<font color="yellow">1w_BTCUSDT_timeframe_analyzer</font>**
|                             |   vertical_distribution_score |   horizontal_distribution_score |   distribution_score |   number_of_members |   number_of_retest |   number_of_cluster |
|:----------------------------|------------------------------:|--------------------------------:|---------------------:|--------------------:|-------------------:|--------------------:|
| ('BTCUSDT', 'sr_dbscan')    |                    0.00164657 |                       0.0554429 |              37.8314 |             5.85714 |            2.85714 |                  14 |
| ('BTCUSDT', 'sr_birch')     |                    0.00199455 |                       0.0626636 |              37.7091 |             4.36364 |            1.36364 |                  22 |
| ('BTCUSDT', 'sr_optics')    |                    0.00667907 |                       0.0598    |              65.5814 |             5.78571 |            2.78571 |                  28 |
| ('BTCUSDT', 'sr_meanshift') |                    0.00232722 |                       0.0565778 |              26.3378 |             5.88889 |            2.88889 |                  18 |



### Per Clustering Algorithm

**<font color="yellow">sr_dbscan_BTCUSDT_timeframe_analyzer</font>**
|                   |   vertical_distribution_score |   horizontal_distribution_score |   distribution_score |   number_of_members |   number_of_retest |   number_of_cluster |
|:------------------|------------------------------:|--------------------------------:|---------------------:|--------------------:|-------------------:|--------------------:|
| ('BTCUSDT', '1h') |                    0.00106029 |                       0.0247727 |              31.3346 |            26.8052  |           23.8052  |                 308 |
| ('BTCUSDT', '4h') |                    0.00132954 |                       0.0361944 |              31.3024 |            13.493   |            9.53521 |                 142 |
| ('BTCUSDT', '1d') |                    0.0016265  |                       0.0658214 |              47.1471 |             6.5     |            2.5     |                  28 |
| ('BTCUSDT', '1w') |                    0.00164657 |                       0.0554429 |              37.8314 |             5.85714 |            2.85714 |                  14 |

**<font color="yellow">sr_birch_BTCUSDT_timeframe_analyzer</font>**
|                   |   vertical_distribution_score |   horizontal_distribution_score |   distribution_score |   number_of_members |   number_of_retest |   number_of_cluster |
|:------------------|------------------------------:|--------------------------------:|---------------------:|--------------------:|-------------------:|--------------------:|
| ('BTCUSDT', '1h') |                    0.00112593 |                       0.0461584 |              53.406  |            12.2757  |            9.27566 |                 682 |
| ('BTCUSDT', '4h') |                    0.00141191 |                       0.0528393 |              42.6913 |             8.30328 |            4.33607 |                 244 |
| ('BTCUSDT', '1d') |                    0.00200128 |                       0.092776  |              48.4632 |             4.96    |            0.96    |                  50 |
| ('BTCUSDT', '1w') |                    0.00199455 |                       0.0626636 |              37.7091 |             4.36364 |            1.36364 |                  22 |

**<font color="yellow">sr_optics_BTCUSDT_timeframe_analyzer</font>**
|                   |   vertical_distribution_score |   horizontal_distribution_score |   distribution_score |   number_of_members |   number_of_retest |   number_of_cluster |
|:------------------|------------------------------:|--------------------------------:|---------------------:|--------------------:|-------------------:|--------------------:|
| ('BTCUSDT', '1h') |                   0.000449194 |                       0.109696  |             923.849  |             4.59309 |            1.59309 |                1504 |
| ('BTCUSDT', '4h') |                   0.00134163  |                       0.0697788 |             218.056  |             6.19178 |            2.23973 |                 292 |
| ('BTCUSDT', '1d') |                   0.00435697  |                       0.0764156 |              34.2781 |             6.25    |            2.25    |                  64 |
| ('BTCUSDT', '1w') |                   0.00667907  |                       0.0598    |              65.5814 |             5.78571 |            2.78571 |                  28 |

**<font color="yellow">sr_meanshift_BTCUSDT_timeframe_analyzer</font>**
|                   |   vertical_distribution_score |   horizontal_distribution_score |   distribution_score |   number_of_members |   number_of_retest |   number_of_cluster |
|:------------------|------------------------------:|--------------------------------:|---------------------:|--------------------:|-------------------:|--------------------:|
| ('BTCUSDT', '1h') |                    0.00154643 |                       0.0328082 |              30.6518 |            19.35    |           16.35    |                 440 |
| ('BTCUSDT', '4h') |                    0.00189393 |                       0.0462692 |              26.866  |            11.967   |            8       |                 182 |
| ('BTCUSDT', '1d') |                    0.0023733  |                       0.105213  |              47.3603 |             5.4     |            1.4     |                  60 |
| ('BTCUSDT', '1w') |                    0.00232722 |                       0.0565778 |              26.3378 |             5.88889 |            2.88889 |                  18 |

## Plots
### Distribution Plots
| | 1h | 4h | 1d | 1w |
|:-:|:-:|:-:|:-:|:-:|
| Horizontal Distribution Score | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1h_horizontal_distribution_score.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_4h_horizontal_distribution_score.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1d_horizontal_distribution_score.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1w_horizontal_distribution_score.png" width="640"/> |
| Vertical Distribution Score | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1h_vertical_distribution_score.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_4h_vertical_distribution_score.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1d_vertical_distribution_score.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1w_vertical_distribution_score.png" width="640"/> |
| Distribution Score | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1h_distribution_score.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_4h_distribution_score.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1d_distribution_score.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1w_distribution_score.png" width="640"/> |
| Number of Members | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1h_number_of_members.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_4h_number_of_members.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1d_number_of_members.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1w_number_of_members.png" width="640"/> |
| Distribution Efficiency | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1h_distribution_efficiency.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_4h_distribution_efficiency.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1d_distribution_efficiency.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1w_distribution_efficiency.png" width="640"/> |
| Number of Retest | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1h_number_of_retest.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_4h_number_of_retest.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1d_number_of_retest.png" width="640"/> | <img src="../../configs/research/support-resistance/reports/supres_distribution_per_metric_BTCUSDT_1w_number_of_retest.png" width="640"/> |


### Heatmap Plots
|Heatmap Plots|
|:---:|
|<img src="../../configs/research/support-resistance/reports/horizontal_distribution_score_BTCUSDT_timeframe_analyzer.png" width="1280"/>|
|<img src="../../configs/research/support-resistance/reports/vertical_distribution_score_BTCUSDT_timeframe_analyzer.png" width="1280"/>|
|<img src="../../configs/research/support-resistance/reports/distribution_score_BTCUSDT_timeframe_analyzer.png" width="1280"/>|
|<img src="../../configs/research/support-resistance/reports/number_of_members_BTCUSDT_timeframe_analyzer.png" width="1280"/>|
|<img src="../../configs/research/support-resistance/reports/distribution_efficiency_BTCUSDT_timeframe_analyzer.png" width="1280"/>|
|<img src="../../configs/research/support-resistance/reports/number_of_cluster_BTCUSDT_timeframe_analyzer.png" width="1280"/>|
|<img src="../../configs/research/support-resistance/reports/number_of_retest_BTCUSDT_timeframe_analyzer.png" width="1280"/>|