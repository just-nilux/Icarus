# Table of Contents
0. [Purpose](#purpose)
1. [Definitions](#definitions)
    * [Support](#support)
    * [Resistance](#resistance)
3. [Method](#method)
4. [Metrics](#metrics)
6. [Results](#results)

# Purpose
Support resistance zones are quite useful to make prediction about the possible price levels that will support or resist. Breakout of these level make indicate an end of a market regime and a start of a new one.

When placing limit or oco orders, the support-resistance zones may indicate the target price levels. This reseach only focuses on the straight horizontal sr zones not the ones with a slope or curve.

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

Clustering is performed over the whole chart. However if the clusters evaluated in whole chart then there will be a lot of false clusters. Thus, for each evaluation, the charts should be discrete. Normally if there is x previous candleç the frequency can be x/2.

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
## Horizontal Score
As the distance increases between datapoints, the cluster becomes more reliable since it is tested multiple different times. So we need to reward the clusters for having large distance values.

Pseudo Code:
1. Get the adjacent distance between each data point.
1. Divide the distance to the whole length of the chart to have normalized values between 0 and 1.
1. Get the weighted average of this distance array where the weights are simply an array of integers starting from 1, until the lenght of the distance array.
## Vertical Score
Pseudo Code:
1. Get the vertical length of the cluster.
1. Divide the vertical length to the length of the chart to have a normalized value between 0 and 1
## Reliability Score
[Horizontal Score] / [Vertical Score]
## Number of Member
Number of members of the cluster

# Results
* Which clustring algorithm works better(have higher accuracy)?
* Whcih timeframes are more suitable/reliable in terms of SR levels
For each pair use the grid as follows: Timeframes x SR Analyzers. Using this grid structure, create a table for each metric

Heatmap:
Layout: [Timeframes x SR Analyzers]
Cluster Algos: ["DBSCAN", "MeanShift", "OPTICS", "BIRCH"]
Value: [HS x VS x RS x NoM]

Alternatively maybe all of these 4 tables can be combined in one big table by using the approach on market regime. That function even might be generalized for this kind of multiplots
