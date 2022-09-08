# Strategy Development Protocol

## 0. Suggest an Hypothesis

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


Here is an example transformation that a sympol hypothesis pass through:

    0. When OBV and the price action diverges it is followed up with a reversal

    1. When the divergence occurs between the price action and the OBV, it is followed up with a reversal, where the divergence is defined as X and reversal defined as Y

    2. When the divergence occurs between the price action and the OBV, it is followed up by a reversal, with the probability of 75% and with the frequency of 3 times per day on the the market conditions X, Y and Z but not T. It holds a potential of %5 profit per day for given conditions.

    3. Assuming that the hypothesis is actually more about entering then the metrics that measure the entry success holds more importance on the backtest results. Implementing a pure hypothesis based strategy.

