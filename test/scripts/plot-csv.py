import argparse
import backtrader as bt
import talib

class MyStrategy(bt.Strategy):
    params = (('smaperiod', 15),)

    def __init__(self):
        # SimpleMovingAverage on main data
        # Equivalent to -> sma = btind.SMA(self.data, period=self.p.smaperiod)
        sma = bt.talib.SMA(period=self.p.smaperiod)

        # CrossOver (1: up, -1: down) close / sma
        #self.buysell = bt.talib.CrossOver(self.data.close, sma, plot=True)

        stoc = bt.ind.Stochastic()
        bt.ind.CrossOver(stoc.lines.percK, stoc.lines.percD)

kline_column_names = ["open_time", "open", "high", "low", "close", "volume", "close_time","quote_asset_volume", 
                    "nbum_of_trades", "taker_buy_base_ast_vol", "taker_buy_quote_ast_vol", "ignore"]


def plot(filename):

    file_substr = filename.split('_')
    kline=file_substr[1]

    timeframe = kline[-1]
    compression = int(kline[:-1])

    if timeframe == 'h':
        timeframe = 'm'
        compression = compression*60

    time_table = {'m':4, 'h':4, 'd':5, 'w':6, 'M':7}
    print(time_table[timeframe],compression)
    cerebro = bt.Cerebro(stdstats=True)
    data = bt.feeds.GenericCSVData(dataname=filename, dtformat=2, compression=compression,
                                   timeframe=time_table[timeframe])
    cerebro.adddata(data)
    cerebro.addstrategy(MyStrategy)
    cerebro.run()

    cerebro.plot(style='candlestick',barup='green', bardown='red')

if __name__ == '__main__':

    # Instantiate the parser
    # python .\test\scripts\plot-csv.py --filename .\test\data\btcusdt_15m_202005121212_202005131213.csv
    parser = argparse.ArgumentParser(description='Optional app description')
    parser.add_argument('--filename', type=str,)
    args = parser.parse_args()

    plot(args.filename)



