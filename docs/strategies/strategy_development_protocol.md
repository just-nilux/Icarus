# Strategy Development Protocol

## 0. Suggest an Hypothesis
A hypothesis is a simple claim that can be proven or disputed statistically.

## 1. Define Hypothesis
* Define the hypothesis to be clearly formulized like:
    * When x happens, y happens
    * Event of x is correlated with y

## 2. Collect Data for Hypothesis
1. Analyze market samples to investigate the hypothesis from statistical point of view:
    * Is it ever true?
    * What is the possibility for each occurence to be true? (Accuracy)
    * How frequent it occurs? (Frequency)
2. Review statistical results in terms of profitability.
3. Improve the hypothesis with details

## 3. Backtest
1. Determine the metrics that measures the impact of the hypothesis best.
2. Try to create a purely hypothesis dependent backtest strategy as much as possible.
3. Review the performance and optimize the strategy

## 4. Live Trade
1. Live trading a results should align with backtest results.

Here is an example transformation that a sympol hypothesis pass through:

    0. When OBV and the price action diverges it is followed up with a reversal

    1. When the divergence occurs between the price action and the OBV, it is followed up with a reversal, where the divergence is defined as X and reversal defined as Y

    2. When the divergence occurs between the price action and the OBV, it is followed up by a reversal, with the probability of 75% and with the frequency of 3 times per day on the the market conditions X, Y and Z but not T. It holds a potential of %5 profit per day for given conditions.

    3. Assuming that the hypothesis is actually more about entering then the metrics that measure the entry success holds more importance on the backtest results. Implementing a pure hypothesis based strategy.

# Personal Notes
My observation is, on almost all of the resoures I saw, the steps start with throwing an strategy idea and then iteratively making it better or leaving it. Optimizing might look like a scientific part but the problem is here. Strategies are composed of multiple small pieces like entering, exiting, position sizing etc. If a strategy is not profittable how do you know what to optimze or fix? It might be the entry/exit timing, the target price levels on limit orders might be a bit off or wrongly put stop loss levels may have negative impact. 

Thus I suggest to starting the strategy creation steps from the small pieces and cheking/analyzing the validity, accuracy, reliablity(whatever you call it) of these components first.