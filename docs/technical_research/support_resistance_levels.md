# How to calculate support resistance levels?

Support resistance levels are the key point to place an Limit order. It helps to target a price level to enter or exit. Otherwise enter and exit levels would be determined by some arbitary numbers like "Enter now and Target %1 profit". Then the question is "why not %2 or %0.5"?

## Evaluation

1. Simplification: Choosing a way to evaluate candidate points.
1. Clustering: Choosing a clustering algorithm to cluster accumuluated candidate point.
1. Validation: Measuring the performance or accuracy of the support resistance levels

## Notes:
- 
- 
- 

- You would want number of members to be high and the horizontal cumulation spread to be narrow
density_score = (cluster_price_range/frame_price_range) / number of members

### KMeans
Parameters:
- Number of cluster

KMeans clustering requires to know the number of clusters (or needs to optimize). However the number of cluster(sup/res levels) are also a result of our evaluation. So it makes no sense to use KMeans for this case. Another downside is the outliers. Since outliers affects the center of the cluster, their existence is devient.

### DBScan
Parameters:
- Epsilon
- Min cluster

DBScan fits better for the clustering in that case. It connects the close points(based on the parameter epsilon) which is good to eliminate outliers since they are lonely.
https://therobusttrader.com/support-and-resistance/

### Mean Shift
Parameters:
- bandwidth

It chooses a point, draws a circle(bw is the radius) and get the mean of all points in the centre. Actually it looks like a perfect fit with the description. However in the case of DBScan, epsilon enable the vertical axis of cluster to expand. In here the bandwidth is limited. In other words, MeanShift can be seen as a subset of DBScan which eliminates clusters with large vertical distribution.

One difference is MeanShift has no min element by its nature. However since the SR levels requires it due to its nature, we can limit it as a post process step

## Measuring Reliability of the Calculated Levels
Things to consider:
- Number of Touches
- Time

horizontal_distribution_score = weighted_average(ordered_cluster, range(1,len(ordered_cluster)))
vertical_distribution_score = (vertical_range(cluster) / vertical_range(chart)) / size(cluster)
score = horizontal_distribution_score / vertical_distribution_score

## Example Implementation:

1. As a simplification method, evaluating fractal patterns is a common practice that make sense. The number of candles for the fractal might vary from 3 to 5.
1. As a clustering algorihm DBScan fits the best for this case.
1. In order to call a region as support resistance,it needs to be tested multiple times and it is better to have more remote located test points. Considering this fact, we can write a score function for the clusters as a measure of reliability of the support resistance levels:
    - Check **Analyzer.eval_sup_res_cluster_score()** function


