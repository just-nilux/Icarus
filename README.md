# Icarus
Icarus is an all-in-one cryptocurrency trading bot for Binance. It enables you to
- Backtest
- Live-trade
- Monitor
- Create new strategies and analyzers
- Create visualizations

## Table of content

1. [Capabilities](#capabilities)
1. [Concepts](#concepts)

## Capabilities
- Easy switching between backtest and live trading
- Support for market, limit and oco orders
- Support for running multiple strategies simultaneously
- Support for data feeds that contain multiple pairs with multiple timescales, which enables to run short term and long term analysis simultaneously
- Meaningful visualizations for trades and analysis objects which fastens custom analysis process
- Asyncio module based architecture which enables faster operations
- Monitor module that supports telegram bot to monitor certain configurable events


## Concepts
### Objects:
Icarus processes the raw data to create orders based on the decisions. The connections between consecutive stages of evaluation, are handled by intermediate objects.
<p align="center">
  <img src="https://user-images.githubusercontent.com/40933377/150873776-ea893a06-e5ac-4348-afeb-074b43563fa6.png?raw=true" alt="Sublime's custom image"/>
</p>

| Object | Description | Lifetime |
| --- | --- | --- |
| **Data Object** | Organized version of the raw data regarding to the configured 'currency pair' and time_frames' pairs. It is consumed by the 'Analyzer' | 1 Cycle |
| **Analysis Object** | Contains the result of (configured) indicators types for each 'currency pair' and time_frames' pairs. It is evaluated by the Analyzer object and consumed by the Strategies | 1 Cycle |
| **Trade Object** | A Trade Object contains the initial plan to enter/exit, current status and statistics of a trade. It contains characteristics such as order types, enter/exit levels, the due date of the current decision etc. | Until the enter and the exit phases completed (afterwards the closed trades are stored to create stats and visualizations) |
| **Observer Object** | Observer Objects are used to store some statistics, diagnostic data or analysis results to be visualized alongside the trades. | Until the end of session (backtest) or until the database retention (live-trading)|


### Submodules:
| Submodules | Description |
| --- | --- |
| **Analyzer** | Contains the all available indicators and patterns |
| **Observer** | Contains observer object creater |
| **Strategy** | Contains the all strategies and the main strategy execution logic |
| **Visualization** | Contains the visualization functions logic for ohlc data, analyzers, observers, trades etc. |
| **Monitor** | Contains the monitoring tools such as telegram bot |

