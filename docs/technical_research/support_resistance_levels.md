# How to calculate support resistance levels?

Support resistance levels are the key point to place an Limit order. It helps to target a price level to enter or exit. Otherwise enter and exit levels would be determined by some arbitary numbers like "Enter now and Target %1 profit". Then the question is "why not %2 or %0.5"?

## Evaluation

1. Simplification: Choosing a way to evaluate candidate points.
1. Clustering: Choosing a clustering algorithm to cluster accumuluated candidate point.
1. Validation: Measuring the performance or accuracy of the support resistance levels

## Notes:
- KMeans clustering requires to know the number of clusters (or needs to optimize). However the number of cluster(sup/res levels) are also a result of our evaluation. So it makes no sense to use KMeans for this case. Another downside is the outliers. Since outliers affects the center of the cluster, their existence is devient.
- DBScan fits better for the clustering in that case. It connects the close points(based on the parameter epsilon) which is good to eliminate outliers since they are lonely.
- https://therobusttrader.com/support-and-resistance/

- You would want number of members to be high and the horizontal cumulation spread to be narrow
density_score = (cluster_price_range/frame_price_range) / number of members

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


