# Table of Contents
0. [Purpose](#purpose)
    * [Questiones](#questiones)
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
    * [Tables](#tables)
        * [Per Timeframe](#per-timeframe)
        * [Per Clustering Algorithm](#per-clustering-algorithm)
    * [Plots](#plots)
        * [Distribution Plots](#distribution-plots)
        * [Heatmap Plots](#heatmap-plots)
7. [Conclusion](#conclusion)
8. [Future Works](#future-works)
        
# Purpose
Support resistance zones are quite useful to make prediction about the possible price levels that will support or resist. Breakout of these level make indicate an end of a market regime and a start of a new one.

When placing limit or oco orders, the support-resistance zones may indicate the target price levels. This reseach only focuses on the straight horizontal sr zones not the ones with a slope or curve.

## Questiones
1. What is the optimal chart length?
1. What are the characteristic of each clustering algorithm?
1. Which clustering algorithm works better?
1. Which timeframes are more suitable/reliable in terms of SR levels?
1. Does it give an edge on the market to be profittable?

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

# Conclusion

1. What is optimal chart length?
    
    Detected clusters and their features strictly rely on the length of the charts. As the charts gets larger, the possibility of having close points in certain price levels is higer. Thus the threshold for a cluster should be higher as the length of the chart is higher. Otherwise the algorithm will generate too much clusters and the result will be noisy.

    Dynamic threshold approach:

        def eval_min_cluster_members(chunk_size):
            return max(round(chunk_size/100),3)

    This approach makes sure that the minimum number of member is 3, and the minimum NoM will be incremented per 100 candles(In example: 3 for 260, 4 for 350, 5 for 450).

    In order to decide which chart length and min NoM combination provides the most meaningful and reliable results, the following table is organized. 
    * [(260,3) (360,3) (360,4) (custom,dynamic)]
    * ["Number of Member", "Number of Cluster", "Distribution Score"]

    As a result it can be stated that:
    * There is no significantly better or worse configuration
    * When the 260_3 and 360_3 is compared, 360_3 looks better since the NoM, NoC and DS is higher
    * When the 360_3 and 360_4 is compared, NoM of 360_4 slightly higher. NoC of 360_4 significantly high. DS values are pretty close to each other except a few outlier.
    * Custom_dynamic configuration shares some portion of the previous configurations for different timeframes.
    * **There is no reason to not to use the custom_dynamic setup.**

    | | Number of Member | Number of Cluster | Distribution Score |
    |:--:|:--:|:--:|:--:|
    |260_3|<img src="../../configs/research/support-resistance/reports_260_3/number_of_members_BTCUSDT_timeframe_analyzer.png" width="640"/>|<img src="../../configs/research/support-resistance/reports_260_3/number_of_cluster_BTCUSDT_timeframe_analyzer.png" width="640"/>|<img src="../../configs/research/support-resistance/reports_260_3/distribution_score_BTCUSDT_timeframe_analyzer.png" width="640"/>|
    |360_3|<img src="../../configs/research/support-resistance/reports_360_3/number_of_members_BTCUSDT_timeframe_analyzer.png" width="640"/>|<img src="../../configs/research/support-resistance/reports_360_3/number_of_cluster_BTCUSDT_timeframe_analyzer.png" width="640"/>|<img src="../../configs/research/support-resistance/reports_360_3/distribution_score_BTCUSDT_timeframe_analyzer.png" width="640"/>|
    |360_4|<img src="../../configs/research/support-resistance/reports_360_4/number_of_members_BTCUSDT_timeframe_analyzer.png" width="640"/>|<img src="../../configs/research/support-resistance/reports_360_4/number_of_cluster_BTCUSDT_timeframe_analyzer.png" width="640"/>|<img src="../../configs/research/support-resistance/reports_360_4/distribution_score_BTCUSDT_timeframe_analyzer.png" width="640"/>|
    |custom_dynamic|<img src="../../configs/research/support-resistance/reports_custom_dynamic/number_of_members_BTCUSDT_timeframe_analyzer.png" width="640"/>|<img src="../../configs/research/support-resistance/reports_custom_dynamic/number_of_cluster_BTCUSDT_timeframe_analyzer.png" width="640"/>|<img src="../../configs/research/support-resistance/reports_custom_dynamic/distribution_score_BTCUSDT_timeframe_analyzer.png" width="640"/>|

1. What are the characteristic of each clustering algo?
    ### sr_optics

       ['1h','4h']: Less member | Less retest | More cluster Dense distribution | High efficiency
       Suitable for small timeframes ['1h','4h']
       Okay to use in big timeframes ['1d','1w']

    * Higher  HDS values in small tfs and lower VDS values in low tfs. As a result the DS is significantly higher in small tfs compare to other algorithms.
    * When the cluster features are investigated, sr_optics has
        * significantly higher NoC in ['1h','4h'] , and relatively higher NoC in ['1d','1w']
        * significantly smaller NoM in ['1h','4h'] and average NoM in ['1d','1w']
        * significantly smaller NoR in ['1h','4h'] and average NoM in ['1d','1w']
    * sr_optics, in ['1h','4h'], generates large number of clusters with a small height and small NoM. Since the cluster is tight in height, NoR is generally lower compare to others. In ['1d','1w'], since it has a large vds but relatively nomal hds, the ds is an average value.
    * Considering the fact that the NoM and NoR is average as well, it can be suggested that the generated clusters are a bit inefficient and inprecise. Because the heigth is quite large but there are just a few members within the boundies of the cluster
    * Distribution efficiency in ['1d','1w'] is quite average but in ['1h','4h'] the DE is huge compare to others

    ### sr_meanshift
    
        More member | More retest ['1h','4h'] | Less cluster | Sparse distribution | Less Efficiency
        Might be average alternat
        ve to use in big timeframes ['1d','1w']

    * High HDS in ['1d'] and average in['1h','4h','1w'].
    * Generally slightly high VDS in all timeframes.
    * NoC increases as the timeframe gets smaller. Average NoC compare to other algotihms
    * When the DS is investigated, meanshift is the lowest at all the timeframes. It leads to lowest DE as well.
    * NoR is average for ['1d','1w'] and above average for ['1h','4h'].  Considering NoR it makes sense to use it for small timeframes. 

    ### sr_dbscan

        More member | More retest | Less cluster | Average distribution
        Suitable for all timeframes, the best is the small timeframes

    * Generally lower HDS compare to other algorithms. HDS increases as the timeframe gets bigger.
    * Generally lower VDS compare to other algorithms.
    * Average DS
    * Significantly higher NoR in '1h' and still high value on '4h'. However in ['1d','1w'], the values are on average.
    * Generally higher DE compare to other algorithms but the difference is not significant, especially in ['1d','1w'].
    * Lowest NoC in all timeframes compare to other algorithms
    * As a result, sr_dbscan can be described as an algorithm that creates smaller number of cluster with a better distribution scores(VDS, DE). Considering the NoR statistics, it can be stated that these small number of clusters are generally dense and tested more compare to other algorithms

    ### sr_birch

        Less member | Less retest | More cluster | Average distribution
        Can be used as a last option to rely on due to low NoR. Not suitable for big timeframes ['1d','1w']

    * Generally average HDS. Increases as the timeframe gets bigger
    * Generally average VDS. Increases as the timeframe gets bigger
    * Generally less NoM and NoR in all timeframes but the difference is not significant. NoR in '1d' is less than 1. Does not look suitable for big timeframes
    * High number of cluster. (If you really need a cluster to have a reference for a price level, then as a last option ıt may work)

1. Which clustering algorithm works better?

    Based on Distribution Score
    |Order| 1h | 4h | 1d | 1w |
    |:--:|:--:|:--:|:--:|:--:|
    |1| **sr_optics** | **sr_optics** | **sr_birch** | **sr_optics** |
    |2| sr_birch | sr_birch | sr_meanshift | sr_dbscan |
    |3| sr_dbscan | sr_dbscan | sr_dbscan | sr_birch |
    |4| sr_meanshift | sr_meanshift | sr_optics | sr_meanshift |

    Based on Number of Retest
    |Order| 1h | 4h | 1d | 1w |
    |:--:|:--:|:--:|:--:|:--:|
    |1| **sr_dbscan** | **sr_dbscan** | **sr_dbscan** | **sr_meanshift** |
    |2| sr_meanshift | sr_meanshift | sr_optics | sr_dbscan |
    |3| sr_birch | sr_birch | sr_meanshift | sr_optics |
    |4| sr_optics | sr_optics | sr_birch | sr_birch |

1. Which timeframes are more suitable/reliable in terms of SR levels?

    |Order| Distribution Score | Number of Retest | Number of Cluster |
    |:--:|:--:|:--:|:--:|
    |1| **1h** | **1h** | **1h** |
    |2| 4h | 4h | 4h |
    |3| 1w | 1d | 1d |
    |4| 1d | 1w | 1w |

1. Does it give an edge on the market to be profitable?

    Considering the following plot, in small timeframes NoR is quite high and in big timeframes it might still be  profitable.
    <img src="../../configs/research/support-resistance/reports/number_of_retest_BTCUSDT_timeframe_analyzer.png" width="640"/>

# Future Works