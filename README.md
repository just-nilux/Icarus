# Ikarus
Ikarus is a cryptocurrency trading bot for Binance. It's main focus is the "risk management". If you can not manage the risk then trading is not much different than gambling.

Ikarus manages the risk by keeping all the sub system artifacts transparent and analyzable.

## Object Types:
* **DataObject:**
* **AnalysisObject**
* **TradeObject:**
TradeObjects are stored in "live-trades" collection of MongoDB. They get updated at the beginning of each iteration. Then it is also consumed from the algorithms for different use cases:
1) If algorithm is configured to support max 1 (or x) open trade at a time (for a specific pair), then it may check if there is an open trade for the current pair. Based on this check it may decide to create a new trade object or not.
* **ObserverObject:**



