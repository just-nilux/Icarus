# Table of Contents
0. [Hypothesis Statement](#hypothesis-statement)
1. [Hypothesis Definition](#hypothesis-definition)
    * [UpTrend](#uptrend)
    * [DownTrend](#downtrend)
    * [Range](#range)
    * [Metrics](#metrics)
2. [Hypothesis Testing](#hypothesis-testing)
    * [DistributionPlot]()
    * [Tabular statistics]()
    * [Observations]()
3. [Backtest](#backtest)
4. [Live Trade](#live-trade)

# Hypothesis Statement
Aroon indicator classifies market regimes: UpTrend, DownTrend and Range

# Hypothesis Definition
## UpTrend:
Higher highes and higher lows are observed. Significantly** positive price change occurs when the start and the end prices are compared.

* Total Price change
* Upper trendline: The line that the uptrend is located below. 
* Lower trendline: The line that the uptrand is located above. 
* Duration: The time between the start and end of the market state

An uptrend may not have a statistically significant trendline. The slope should be significantly greater than 0 which aligns with the expected change in price.

## DownTrend:
Lower highes and lower lows are observed. Significantly** negative price change occurs when the start and the end prices are compared.

* Total Price change
* Upper trendline: The line that the downtrend is located below.
* Lower trendline: The line that the downtrend is located above.
* Duration: The time between the start and end of the market state

The slope should be significantly less than 0 which aligns with the expected change in price.

## Range:
No significant** price change occurs. Price moves within a certain band until it breaks one permanently, which corresponds to the end of the Range Market

* Total Price change
* Upper boundry: The line that the downtrend stands on. The slope should be either 0 or very close to 0.
* Lower boundry: The line that the downtrend is located below. The slope should be either 0 or very close to 0.
* Duration: The time between the start and end of the market state


** The term "statistical significance" needs to be investigated.

## Metrics
* The slope of trendlines should be greater/less than X for Up/DownTrend and it should be less then Y to be a Range where Y~=0
* The percentage price change should be greater/less than X for Up/DownTrend and it should be less then Y to be a Range where Y~=0
* The duration should be long enough to distinguish indecisive short term moves from the purposeful moves with longer duration. In other words, the market states with small duration should be ignored


# Hypothesis Testing
|                  |   downtrend |   ranging |   uptrend |
|:-----------------|------------:|----------:|----------:|
| Occurence        |        7    |     17    |     11    |
| Average PPC      |       -1.08 |     -0.44 |     13.29 |
| Average duration |        9    |      9    |     11    |
| Coverage         |       18.06 |     44.47 |     34.77 |
| PPC Accuracy     |       42.86 |     41.18 |     18.18 |

# Backtest


# Live Trade


# Personal Notes
