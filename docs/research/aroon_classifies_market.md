# Table of Contents
0. [Hypothesis Statement](#hypothesis-statement)
1. [Hypothesis Definition](#hypothesis-definition)
    * [UpTrend](#uptrend)
    * [DownTrend](#downtrend)
    * [Range](#range)
    * [Metrics](#metrics)
2. [Hypothesis Testing](#hypothesis-testing)
    * [PPC Accuracy](#ppc-accuracy)
    * [PVPC Accuracy](#pvpc-accuracy)
    * [Market Regime Occurence](#market-regime-occurence)
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
### Occurence:
Number of instances of a market regime.
### Duration:
Duration of a regime instances with the unit candlestick.
### Coverage: 
Total coverage of a regime instances in percentage on a given chart.
### Percentage Price Change (PPC):
The change between the **open price** of the first and **close price** of the last candles in a detected section of the chart.
### PPC Accuracy:
For a a type of market regime: "How much of the detected regimes fits to a threshold rule":
* UpTrend: PPC > 1
* Range: -1 < PPC < 1
* DownTrend: PPC < -1
### PVPC:
The change between the **open price** of the validation candle and **close price** of the last candle in a detected section of the chart. This metric is not used to evaluate the accuracy/reliability of the detected regime. However it is usefull to make a judgement regarding the question _"What is the price change after the regime is validated?"_ or _"What does the useable part of this market regime looks like?"_.

## Parameters to Optimize:
* Validation Threshold: Minimum number of candle that is required for a market regime to exist
* PPC Accuracy Thresholds: What is the best performing set of thresholds


# Hypothesis Testing
Parameters:
* Market class analyzers: aroon, aroonosc, fractal_aroon
* Pairs: BTCUSDT, ETHUSDT
* Timeframes: 1d
* Chart Start Date: 2017-10-10 13:00:00
* Chart End Date: 2022-10-10 13:00:00


## PPC Accuracy
<img src="../../configs/research/aroon_classifies_market/reports/PPC_Accuracy_BTCUSDT_1h.png" /> 
<img src="../../configs/research/aroon_classifies_market/reports/PPC_Accuracy_BTCUSDT_1d.png" /> 
<img src="../../configs/research/aroon_classifies_market/reports/PPC_Accuracy_ETHUSDT_1d.png" />


## PVPC Accuracy
<img src="../../configs/research/aroon_classifies_market/reports/PVPC_Accuracy_BTCUSDT_1h.png" /> 
<img src="../../configs/research/aroon_classifies_market/reports/PVPC_Accuracy_BTCUSDT_1d.png" /> 
<img src="../../configs/research/aroon_classifies_market/reports/PVPC_Accuracy_ETHUSDT_1d.png" />

## Market Regime Occurence
<img src="../../configs/research/aroon_classifies_market/reports/Occurence_BTCUSDT_1h.png" /> 
<img src="../../configs/research/aroon_classifies_market/reports/Occurence_BTCUSDT_1d.png" /> 
<img src="../../configs/research/aroon_classifies_market/reports/Occurence_ETHUSDT_1d.png" /> 

# Personal Notes
TBD

In the fractal_arron calculation, either ffill().bfill() or bfill().ffill() needs to be use. the result of bfill().ffill() (which is the the default one) performs way better on PPC and PPVC metrics. However it cannot be used since the future values are used to fill the missing current values.

Interestingly the ranging market is easyily detected ath the 1h timeframe with the -1 +1 percentage rule. It may open different doors