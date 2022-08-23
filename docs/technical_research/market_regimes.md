# Why the market regimes matter?
"Knowing how to trade in different Market Regimes is just as important, if not more so, than what to trade."
# What are the market regimes?
* **Defined Regimes:** Human-defined regimes that is meaningful for humans. There are various subjective definitions to classify market regimes but the ideas they represent are similar and can be reduced to following regime types:
    * UpTrend
    * DownTrend
    * Ranging
    * DropDown(?)
    * JumpUp(?)
* **Undefined Regimes:** ML defined "patterns". That may or may not be meaningful for humans.

# What are the methods to detect market regimes?
There are 2 approaches on market regime detection:
* **Offline analysis:**  It does not try to predict the class as early as possible. It looks at the big picture and try to dedect, analyze and give meaning to the market regimes as accurate as possible. As a result a dataset is created. It can be perceived as feature extraction.

* **Online analysis:** It aims to predict the current/next market regime as early and as accurate as possible

* Object detection approach (Supervised learning and drawing rectangles)
* Combination of conventionla tech indicators
    * SQN and ATR
    * Aroon
* Some sort of clustering

# What kind of statistics can be created out of the detected market regimes?
## Primary Statistics:
* Start/End date of regimes
## Secondary Statistics:
* Occurence rate of market regimes
* Dependency relationships and correlations  between Market regimes
* Charachteristics of market states like the volume, length, profitability of each instance

# What kind of usecases may benefit from the market regime statistics?
* Prediction of next market state
* Prediction of the current market regime end time and price ranges.
# Can the market regimes overlap?

# Implementation/Design Decisions:
The target is to state such hypothesis like:
    
    * The UpTrending market regime generally last x candle in this timeframe
    * The market regime x generally results in a price change: y%
    * The market regimes x and y generally occur sequentially with the probabılıty of z%

To make such statement we treat each occurence of certain type of market regime as an atomic unit with various features. To keep the data organized, use of dataclass quite beneficial. This dataclasses will be the ommon language the bot talk when visualizing the market regimes or creating higher level statistics
