# Icarus
Icarus is an all-in-one cryptocurrency trading bot for Binance. It enables you to
- Backtest
- Live-trade
- Monitor
- Create new strategies and analyzers
- Create visualizations

## Table of content

1. [Capabilities](#capabilities)
1. [Backtest](#backtest)
1. [Live Trade](#live-trade)

## Capabilities
- Easy switching between backtest and live trading
- Support for market, limit and oco orders
- Support for running multiple strategies simultaneously
- Support for data feeds that contain multiple pairs with multiple timescales, which enables to run short term and long term analysis simultaneously
- Meaningful visualizations for trades and analysis objects which fastens custom analysis process
- Asyncio module based architecture which enables faster operations
- Monitor module that supports telegram bot to monitor certain configurable events

## Backtest
### 1. Configure
Choose an existing configuration file (such as `configs/quick-start/config.json`) or just create a new one to experiment
### 2. Run
Run the backtest script by providing the config file as argument: `python backtest.py configs/quick-start/config.json`
### 3. Observe Backtest Results
The statistics of the backtest session will be dumped to the file which is specified in the `statistics.report_path` field of the config file.
### 4. Visualize Trades
Run the `visualize_test_session` script and investigate the dashboard: `python -m Ikarus.scripts.visualize_test_session configs/quick-start/config.json`
### 5. Visualize Indicators
Run the `visualize_indicators` script and investigate the dashboard: `python -m Ikarus.scripts.visualize_indicators configs/quick-start/config.json`

## Live Trade
