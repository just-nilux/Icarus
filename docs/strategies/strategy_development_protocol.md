# Strategy Development Protocol

## 0. Hypothesis Statement
* Make an hypothesis statement that can be proven or disputed statistically and also describe how it might be useful as a trading strategy component. Which problem it solves?

## 1. Hypothesis Definition
1. Formulize the hypothesis clearly:
    * When x happens, y happens
    * Event of x is correlated with y
    * X is correct
2. Define each element of the hypothesis and its features mathematically
3. Define the metrics to measure success/accuracy

## 2. Hypothesis Testing
This step is different than backtesting since it runs the logic then as an outcome it only checks the actual result, but not the reflection of it on the equity curve or strategy stats which blends the effect of entry/exit rules, position sizing and risk management. The latter is the case for the backtest.
1. Analyze market samples to investigate the hypothesis from statistical point of view:
    * Is it ever true?
    * What is the possibility for each occurence to be true? (Accuracy)
    * How frequent it occurs? (Frequency)
2. Review statistical results in terms of profitability.
3. Improve the hypothesis with details

The output of hypothesis testing is the final step for a hypothesis. Afterwards, if applicable, it can be converted to a trading strategy.

## 3. Backtest
An hypothesis does not have to be directly linked to a strategy. It can just be helping element that does not generate an enter/exit rule. If it can generate secondary information to create a strategy, following items might be applied.
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