# Purpose
Knowing where the current price action is, in the context of current market regime may help to the decision making process on strategies.
For example, 
- if we are in a ranging market and close to the bootm of the range then we may make a guess for reversal and look for long entry or short and hope for the down breakdown.
- if we are in a trending market, we may know if we are at the top of the current trend or in a pullback.


# The use of indicators

## Stoch
It tells us where we are compare to the range of the last k candlesticks. A moving average generally applied to the raw data so there might be some lagging caused by the moving average.


FASTK(Kperiod) =(Today's Close - LowestLow)/(HighestHigh - LowestLow) * 100
FASTD(FastDperiod) = MA Smoothed FASTK over FastDperiod
SLOWK(SlowKperiod) = MA Smoothed FASTK over SlowKperiod
SLOWD(SlowDperiod) = MA Smoothed SLOWK over SlowDperiod