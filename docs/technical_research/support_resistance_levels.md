# Why the Support-Resistance Levels matter?

Support resistance levels are the key point to place an Limit order. It helps to target a price level to enter or exit. Otherwise enter and exit levels would be determined by some arbitary numbers like "Enter now and Target %1 profit". Then the question is "why not %2 or %0.5"?

# Horizontal Support-Resistance Levels
## Evaluation Steps

1. Simplification: Choosing a way to evaluate candidate points.
1. Clustering: Choosing a clustering algorithm to cluster accumuluated candidate point.
1. Validation: Measuring the performance or accuracy of the support resistance levels

## Clustering Algorithms
### KMeans
Parameters:
- Number of cluster

KMeans clustering requires to know the number of clusters (or needs to optimize). However the number of cluster(sup/res levels) are also a result of our evaluation. So it makes no sense to use KMeans for this case. Another downside is the outliers. Since outliers affects the center of the cluster, their existence is devient.

### DBSCAN
Parameters:
- Epsilon
- Min cluster

DBScan fits better for the clustering in that case. It connects the close points(based on the parameter epsilon) which is good to eliminate outliers since they are lonely.
https://therobusttrader.com/support-and-resistance/

### Mean Shift
Parameters:
- bandwidth

It chooses a point, draws a circle(bandwidth is the radius) and get the mean of all points in the centre. Actually it looks like a perfect fit with the description. However in the case of DBScan, epsilon enable the vertical axis of cluster to expand. In here the bandwidth is limited. In other words, MeanShift can be seen as a subset of DBScan which eliminates clusters with large vertical distribution.

One difference is MeanShift has no min element by its nature. However since the SR levels requires it due to its nature, we can limit it as a post process step

### OPTICS
Parameters:
- Branching coeff: Max number of subcluster that a cluster can have
- Threshold value: The definition of epsilon fits
- Number of cluster (Optional)

See: https://scikit-learn.org/stable/auto_examples/cluster/plot_optics.html#sphx-glr-auto-examples-cluster-plot-optics-py

It has concepts lıke core-distance, reachability-distance
As a concept OPTICS algorithm is actullay creates a reachibility graph. where the euclydian distance betwween the core and the other points.On top of the the clustring itself is an sepearte interpretations

### BIRCH
See the followıng video for the logıc:
https://www.youtube.com/watch?v=l1pwUwMgKD0&t=112s

## Validation
How to know which support resıstance level or cluster is more reliable? In order to answer this question following score functıons can be caluclated.
### Horizontal Score
Psuedo Code:
1. Get the adjacent distance between each data point.
1. Divide the distance to the whole length of the chart to have normalized values between 0 and 1.
1. Get the weighted average of this distance array where the weights are simply an array of integers starting from 1, until the lenght of the distance array. The logic behing this function is: "As the distance increases between datapoints, the cluster becomes more reliable since it is tested multiple different times. So we need to reward the clusters for having large distance values."
### Vertical Score
Psuedo Code:
1. Get the vertical length of the cluster.
1. Divide the vertical length to the length of the chart to have a normalized value between 0 and 1

### Final Score
[Horizontal Score] / [Vertical Score]
### Alternative Ideas:
* Score can be multiplied with the number of members.Then the final score can be checked if it is greater than 100. 100 is just an observation
* The calculation of vertical score can be made with RMS
* Total score can be evaluated as score*number_of_members. Then we expect it to be greater then 100. This number would be a function of horizontal dist, vertical dist and the num of members which makes sense.

## Example Implementation:

1. As a simplification method, evaluating fractal patterns is a common practice that make sense. The number of candles for the fractal might vary from 3 to 5.
1. As a clustering algorihm DBScan fits the best for this case.
1. In order to call a region as support resistance,it needs to be tested multiple times and it is better to have more remote located test points. Considering this fact, we can write a score function for the clusters as a measure of reliability of the support resistance levels:
    - Check **Analyzer.eval_sup_res_cluster_score()** function

## Problems:
If a long timespan is chosen as start and end date of simulation, and the timeframe is small like '1h' then the x axis will be too long and there will be alot of data points. As a result:
* Min Member threshold for clusters will be high
* The relevance of members decrease after a distance which is a vague parameter.
The problems with number of candlesticks:

If we consider 1 year timeframe:
* '1d' timeframe: 365*2 = 730 candlesticks
* '1h' timeframe: 336 + 24*265=6.696  candlesticks.

Even if the price just go up and down, arbitarily, a lot of cluster will be created. As the time span increases relevence between the members should decrease. You cannot claim that "In 2019 there was a support level in 1h frame at the price x, and now that is why there is a freactal point at the price x". This should be irrelevant.
	
This approach brings another problem:
	initially we said that as the timespan between the fractals increases the reliability of the sr level increases. This suggests a linear relationship (relevance) between the distance and the reliability
now we said that if the distance is too much: than it there cannot be a relevance. As it is articulated in the example above.

To solve the issue: we can divide the total timespan to number of candlesticks that a timeframe normally have.

## Notes:
Support-Resistance Level Parameters:
* **source:** The data source for clustering
* **discrete_mode:** 


# Cross Support-Resistance Lines
## Calculation Approaches:
* If the slope of the cluster is known than the Horizontal SR Calculations might be applied.
* Relying on conventional indicators triggers to detect beginning and end of the regimes. For example using aroon to detect trends
* A pre-calculation regarding the Market Regimes might be done. Using the detected trend regimes. The slope of clusters can be evaluated and 

