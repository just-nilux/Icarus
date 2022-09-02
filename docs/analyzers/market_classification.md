
# Purpose
* Usıng proper strategy at a proper market condition
* Prediction of next market state
* Prediction of the current market regime end time and price ranges.

# Types of Market Regimes
* **Defined Regimes:** Human-defined regimes that is meaningful for humans. There are various subjective definitions to classify market regimes but the ideas they represent are similar and can be reduced to following regime types:
    * UpTrend
    * DownTrend
    * Ranging
    * DropDown(?)
    * JumpUp(?)
* **Undefined Regimes:** ML defined "patterns". That may or may not be meaningful for humans.

# Market Regime Detection
There are 2 approaches on market regime detection:
* **Offline analysis:**  It does not try to predict the class as early as possible. It looks at the big picture and try to dedect, analyze and give meaning to the market regimes as accurate as possible. As a result a dataset is created. It can be perceived as feature extraction.

* **Online analysis:** It aims to predict the current/next market regime as early and as accurate as possible
* Undefined Regimes:
    * Hidden Markov Model
    * Clustering
* Defined Regimes:
    * Technical Indicators
    * Object detection approach (Supervised learning and drawing rectangles)

# Market Regime Statistics
* Start/End date of regimes
* Occurence rate of market regimes
* Dependency relationships and correlations  between Market regimes
* Charachteristics of market states like the volume, length, profitability of each instance

# Implementation/Design Decisions:
The target is to state such hypothesis like:
    
    * The UpTrending market regime generally last x candle in this timeframe
    * The market regime x generally results in a price change: y%
    * The market regimes x and y generally occur sequentially with the probabılıty of z%

To make such statement we treat each occurence of certain type of market regime as an atomic unit with various features. To keep the data organized, use of dataclass quite beneficial. This dataclasses will be the ommon language the bot talk when visualizing the market regimes or creating higher level statistics

# The use of indicators on market classification:

## Aroon
Aroon is composed of 2 lines (aroonup and aroondown) that oscillates between 0 and 100, that measures:
> How long it has been since the last highest high or lowest low

    1. If the aroonup is greater then threshold-1 then it is "uptrend"
    2. If the aroondown is greater then threshold-2 then it is "downtrend"
    3. If thresholds 1 and 2 is not the same then the 3rd class can be "ranging" if aroonup and down is below the thresholds

## Aroonosc
Aroonosc is the difference between aroonup and aroondown values. The sample is:

    1. If the value is above 0, then it is "uptrend"
    2. If the value is below 0, then it is "downtrend"

The values above and below zero simply denotes the crossovers.