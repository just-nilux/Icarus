<p align="center"><img src="https://user-images.githubusercontent.com/40933377/151241659-1fd03ef8-5723-4a57-8ea8-58a9b6386304.jpg" width="1000" height="288"></p>

# Icarus
Icarus is an all-in-one cryptocurrency trading bot for Binance. It enables you to
- backtest
- live-trade
- monitor
  - boot diagnostics
  - trade related events
  - balance
- create 
  - custom strategies
  - custom indicators
- visualize
  - trades on charts
  - custom indicators
  - technical research results
- report
  - backtest results
  - strategy performances
  - technical research results


# Table of content

- [Installation](#installation)
- [Philosophy](#philosophy)
- [Applications](#applications)
- [Live Trade](#live-trade)

# Installation
```
git clone https://github.com/bilkosem/Icarus.git
cd Icarus
sudo ./install.sh
```
Install mongodb from official website: https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/, then
```
sudo chown -R mongodb:mongodb /var/lib/mongodb
sudo chown mongodb:mongodb /tmp/mongodb-27017.sock
sudo service mongod restart
```
# Philosophy
Icarus tries to overcome downsides of traditional trading strategy creation process:
<p align="center">
  <img src="/docs/readme/strategy_dev_old.png?raw=true" alt="strategy_dev_old"/>
</p>

## Problems
### Strategy Creation

A hypothesis is not equal to a strategy. Strategies are compose of multiple hypothesis considering entry/exit rules, pozition sizing and risk management. When a hypothesis is converted to a strategy and tested, the results also contains the affect of other components. Thus the evaluation of the results might be misleading and does not reflect the real validity of hypothesis.

### Evaluate Results

As a result of the backtest, statistics are created. These statistics contains general metrics like, total profit, win rate, average return, average duration etc. These metrics may only measure the validity of the hypothesis indirectly.

### Optimize

Since the hypothesis itself is not the direct subject of the statistic evaluation, how to decide what to optimize.

## Scientific Approach for Strategy Development
Proposed solution:

<p align="center">
  <img src="/docs/readme/strategy_dev_new.png?raw=true" alt="strategy_dev_new"/>
</p>

# Applications
## Backtest
### 1. Configure 🛠
Choose an existing configuration file (such as [configs/quick-start/config.json](configs/quick-start/config.json)) or just create a new one to experiment.

By doing backtest with 'quick-start' config file, you run 3 strategies that works on pairs together and independent from their decisions. These strategies uses Market, Limit, and OCO orders to enter and exit trades.

### 2. Run 🚀
Run the backtest script by providing the config file as argument:

`python backtest.py configs/quick-start/config.json`
### 3. Observe Backtest Results 📊
The statistics of the backtest session will be dumped to the file which is specified in the `statistics.report_path` field of the config file.
Checkout the output statistic file of the backtest session [stat.txt](docs/readme/stat.txt)

### 4. Visualize Trades 📈
Run the `visualize_backtest` script and investigate the dashboard:

`python visualize_backtest.py configs/quick-start/config.json`

<p align="center">
  <img src="/docs/readme/backtest.PNG?raw=true" alt="Backtest Visualization"/>
</p>

### 5. Visualize Indicators 📉
Run the `visualize_indicators` script and investigate the dashboard:

`python visualize_analyzers.py configs/quick-start/config.json`

<p align="center">
  <img src="/docs/readme/indicators.PNG?raw=true" alt="Indicator Visualization"/>
</p>

## Live-Trade
### 1. Configure 🛠
Live-Trade configs may contain some additional configurations regarding the monitoring settings to enable/disable such as "live trade objects(LTO)", "statistics", "errors" etc.

### 2. Run 🚀
`python live-trade.py configs/quick-start/config.json`

### 3. Visualize 📈
Visualization works the same as the backtest mechanism (Combining the historical trade objects from MongoDB and combining it with the data).

### 4. Monitor 🔍
Based on the configured options, the messages are published to the target telegram channel. Below, you can see the messages regarding the state of a trade object (LTO: Live Trade Object, HTO: Historical Trade Object)

<p align="center"><img src="/docs/readme/telegram-bot-messages.jpeg" width="225" height="400"></p>

## Report
