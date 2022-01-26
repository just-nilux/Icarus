<p align="center"><img src="https://user-images.githubusercontent.com/40933377/151241659-1fd03ef8-5723-4a57-8ea8-58a9b6386304.jpg" width="1000" height="288"></p>

# Icarus
Icarus is an all-in-one cryptocurrency trading bot for Binance. It enables you to
- Backtest
- Live-trade
- Monitor
- Create new strategies and analyzers
- Create visualizations

## Table of content

- [Capabilities](#capabilities)
- [Backtest](#backtest)
- [Live Trade](#live-trade)

## Capabilities
- Easy switching between backtest and live trading
- Support for market, limit and oco orders
- Support for running multiple strategies simultaneously
- Support for data feeds that contain multiple pairs with multiple timescales, which enables to run short term and long term analysis simultaneously
- Meaningful visualizations for trades and analysis objects which fastens custom analysis process
- Asyncio module based architecture which enables faster operations
- Monitor module that supports telegram bot to monitor certain configurable events

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
Run the `visualize_test_session` script and investigate the dashboard:

`python -m Ikarus.scripts.visualize_test_session configs/quick-start/config.json`

<p align="center">
  <img src="/docs/readme/backtest.PNG?raw=true" alt="Backtest Visualization"/>
</p>

### 5. Visualize Indicators 📉
Run the `visualize_indicators` script and investigate the dashboard:

`python -m Ikarus.scripts.visualize_indicators configs/quick-start/config.json`

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
