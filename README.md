# Ikarus
What is Ikarus?
Ikarus is a cryptocurrency trading bot for Binance. It takes its name from the Greek myth Ikarus. The purpose of the name is to not to forget that rising to high to the sun or gliding too low to the see would both cause failure. In order to succeed, it is needed to have a balance between the edges.

It's main focus is the "risk management". If you can not manage the risk then trading is not much different than gambling.

Ikarus manages the risk by keeping all the sub system artifacts transparent and analyzable.

## Objects:
Ikarus uses objects to simplify, categorize and manage operations. Objects are located in the data layers that contains the raw input. In order to manage the data, a simplification process is needed. This simplification is performed by the objects. Each object have a life cycle. They are created, updated and deleted/stored in related collection of the database. In order to store and reuse the variables, they are designed as JSON compatible.
* **DataObject:**
* **AnalysisObject**
* **TradeObject:**
TradeObjects are stored in "live-trades" collection of MongoDB. They get updated at the beginning of each iteration. Then it is also consumed from the algorithms for different use cases:
1) If algorithm is configured to support max 1 (or x) open trade at a time (for a specific pair), then it may check if there is an open trade for the current pair. Based on this check it may decide to create a new trade object or not.
* **ObserverObject:**

## Usage of Database:
Since the Ikarus works based on the life cycle of objects, it needs to be stored. This will be required during algorithms, since they will need recall prev decisions and calculations. 

