# Ikarus
What is Ikarus?
Ikarus is a cryptocurrency trading bot for Binance. It takes its name from the Greek myth Ikarus. The purpose of the name is to not to forget that rising to high to the sun or gliding too low to the see would both cause failure. In order to succeed, it is needed to have a balance between the edges.

It's main focus is the "risk management". If you can not manage the risk then trading is not much different than gambling.

Ikarus manages the risk by keeping all the sub system artifacts transparent and analyzable.

# Capabilities
1. Available order types:
    - enter
        - market
        - limit
    - exit
        - market
        - limit
        - oco


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


# Notes
## Note #1: Decision, Enter and Exit Points
Decision and the enter points can be in the same candle. However, exit cannot be in the same candle with entry. Because the logic goes as follows:
### t=0:
- Decision has been made to enter.
### t=n:
- Check the candle [n-1], if the entry is succesful.
- If succesfull, then change the status to 'waiting exit'
- algorithm will see the status 'waiting exit' and create the 'action' with the value 'execute_exit'
- exit order will be placed at the beginning of the candle n

In this scenario the earliest execution of exit is possible at [n] where the entry point is at [n-1]

## Note #3: Overlapping Entries

The visualization might be deceiving about the execution logic
If an rectangle border touches a candle, then the time-interval that the candle contain is inside the candle

## Note #2: Market Order Logic

Since the market orders are executed in the execute_orders function of binance wrapper, 
it is not expected to have a market section here at this position. If exit_expire happens (the bought
asset neither reach the sell limit or break the stoploss, then it can wait forever or market sell can be made)
the decision about what to do can be made by the algorithm, since it is the only place to make a decision.
In that case if it makes a decision to market sell, it is executed. If it makes a decision to wait until the 
time x, then the expire time can be posponed for a while. In all cases it is decided by the algorihtm and no
market order is executed here.

