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
    * [Number of Clusters](#number-of-clusters)
    * [Retest Ratio](#retest-ratio)
6. [Results](#results)

# Purpose
Support resistance zones are quite useful to make prediction about the possible price levels that will support or resist. Breakout of these level make indicate an end of a market regime and a start of a new one.

When placing limit or oco orders, the support-resistance zones may indicate the target price levels. This reseach only focuses on the straight horizontal sr zones not the ones with a slope or curve.

## Questiones and Expected Answers
1. What are the characteristic of each clustering algo?

    Example Output: HDS, VDS, Number of members, Number of Cluster and Retest-Ratio: 
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
(DS): [Horizontal Score] / [Vertical Score]
## Number of Members
(NoM): Total number of members of a cluster
## Number of Clusters
(NoC): Total Number of cluster that an algorithm crated
## Retest Ratio
(RR): It is ratio of the number of validation candles and the retest candles. If the ratio is low, then the possibility of creating a trading edge out of the sr line is low and vice-versa.

# Results
HDS, VDS, DS, NoM and RR parameters are evaluated per cluster. For each **[timeframe] x [pair] x [algorithm]** there will be multiple of these statistics

NoC is evaluated per  **[timeframe] x [pair] x [algorithm]**

The comparisons between the pairs has the lowest importance.

## Approach
1. What are the characteristic of each clustering algo?
1. Which clustering algorithm works better(have higher accuracy)?
1. Which timeframes are more suitable/reliable in terms of SR levels?
1. Does it give an edge on the market to be profittable?


For each pair use the grid as follows: Timeframes x SR Analyzers. Using this grid structure, create a table for each metric

Heatmap:
Layout: [Timeframes x SR Analyzers]
Cluster Algos: ["DBSCAN", "MeanShift", "OPTICS", "BIRCH"]
Value: [HS x VS x RS x NoM]

Alternatively maybe all of these 4 tables can be combined in one big table by using the approach on market regime. That function even might be generalized for this kind of multiplots
