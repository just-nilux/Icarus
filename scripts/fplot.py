import argparse
import backtrader as bt
from numpy.core.numeric import False_
from tables import file
import talib
import collections
import finplot as fplt
import pandas as pd
import numpy as np
from collections import defaultdict
from matplotlib.markers import MarkerStyle as MS
#kline_column_names = ["open_time", "open", "high", "low", "close", "volume", "close_time","quote_asset_volume", 
#                    "nbum_of_trades", "taker_buy_base_ast_vol", "taker_buy_quote_ast_vol", "ignore"]

def calc_volume_profile(df, period, bins):
    '''
    Calculate a poor man's volume distribution/profile by "pinpointing" each kline volume to a certain
    price and placing them, into N buckets. (IRL volume would be something like "trade-bins" per candle.)
    The output format is a matrix, where each [period] time is a row index, and even columns contain
    start (low) price and odd columns contain volume (for that price and time interval). See
    finplot.horiz_time_volume() for more info.
    '''
    data = []
    df['hlc3'] = (df.high + df.low + df.close) / 3 # assume this is volume center per each 1m candle
    _,all_bins = pd.cut(df.hlc3, bins, right=False, retbins=True)
    for _,g in df.groupby(pd.Grouper(key='open_time', freq=period)):
        t = g['open_time'].iloc[0]
        volbins = pd.cut(g.hlc3, all_bins, right=False)
        price2vol = defaultdict(float)
        for iv,vol in zip(volbins, g.volume):
            price2vol[iv.left] += vol
        data.append([t, sorted(price2vol.items())])
    return data


def fplot_volume_profile(filename=None):

    if filename == None:
        filename=args.filename

    df = pd.read_csv(filename)
    df['open_time'] = df['open_time'].astype('datetime64[ms]')
    #df = df.set_index(['open_time'])
    time_volume_profile = calc_volume_profile(df, period='d', bins=100) # try fewer/more horizontal bars (graphical resolution only)

    fplt.plot(df['open_time'], df['close'], legend='Price')
    fplt.candlestick_ochl(df[['open_time','open','close','high','low']], colorfunc=fplt.strength_colorfilter)

    fplt.horiz_time_volume(time_volume_profile, draw_va=0.7, draw_poc=1.0)
    fplt.show()



def fplot_2row(filename=None):

    if filename == None:
        filename=args.filename

    df = pd.read_csv(filename)
    df = df.set_index(['open_time'])
    print(df)
    ax, ax2 = fplt.create_plot('S&P 500 MACD', rows=2)

    # plot macd with standard colors first
    macd = df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean()
    signal = macd.ewm(span=9).mean()
    df['macd_diff'] = macd - signal
    fplt.volume_ocv(df[['open','close','macd_diff']], ax=ax2, colorfunc=fplt.strength_colorfilter)
    fplt.plot(macd, ax=ax2, legend='MACD')
    fplt.plot(signal, ax=ax2, legend='Signal')

    fplt.candlestick_ochl(df[['open','close','high','low']], ax=ax, colorfunc=fplt.strength_colorfilter)
    hover_label = fplt.add_legend('', ax=ax)
    axo = ax.overlay()
    fplt.volume_ocv(df[['open','close','volume']], ax=axo)
    fplt.plot(df['volume'].ewm(span=24).mean(), ax=axo, color=1)
    fplt.show()


def fplot_2row_scatter(filename=None):

    if filename == None:
        filename=args.filename

    df = pd.read_csv(filename)
    df = df.set_index(['open_time'])
    print(df)
    ax, ax2 = fplt.create_plot('S&P 500 MACD', rows=2)

    # plot macd with standard colors first
    macd = df['close'].ewm(span=12).mean() - df['close'].ewm(span=26).mean()
    signal = macd.ewm(span=9).mean()
    df['macd_diff'] = macd - signal
    fplt.volume_ocv(df[['open','close','macd_diff']], ax=ax2, colorfunc=fplt.strength_colorfilter)
    fplt.plot(macd, ax=ax2, legend='MACD')
    fplt.plot(signal, ax=ax2, legend='Signal')

    fplt.candlestick_ochl(df[['open','close','high','low']], ax=ax, colorfunc=fplt.strength_colorfilter)
    hover_label = fplt.add_legend('', ax=ax)
    axo = ax.overlay()
    fplt.volume_ocv(df[['open','close','volume']], ax=axo)
    fplt.plot(df['volume'].ewm(span=24).mean(), ax=axo, color=1)



    #dft.plot(kind='labels', ax=ax) #TODO: Add labels for buy and sell prices


    fplt.show()


def fplot_volume(filename=None):

    if filename == None:
        filename=args.filename

    df = pd.read_csv(filename)
    df = df.set_index(['open_time'])

    ax = fplt.create_plot('S&P 500 MACD', rows=1)
    fplt.candlestick_ochl(df[['open','close','high','low']], ax=ax, colorfunc=fplt.strength_colorfilter)
    hover_label = fplt.add_legend('', ax=ax)

    # Add ax overlay
    axo = ax.overlay()
    fplt.volume_ocv(df[['open','close','volume']], ax=axo)
    fplt.plot(df['volume'].ewm(span=24).mean(), ax=axo, color=1)
    fplt.show()


def fplot(filename=None):

    if filename == None:
        filename=args.filename

    df = pd.read_csv(filename)
    df = df.set_index(['open_time'])
    fplt.candlestick_ochl(df[['open', 'close', 'high', 'low']], colorfunc=fplt.strength_colorfilter)

    # Add period separator lines
    periods = pd.to_datetime(df.index, unit='ms').strftime('%H')
    last_period = ''
    for x,(period,price) in enumerate(zip(periods, df.close)):
        if period != last_period:
            fplt.add_line((x-0.5, price*0.5), (x-0.5, price*2), color='#bbb', style='--')
        last_period = period
    fplt.show()


def buy_sell(df, df_closed=pd.DataFrame(), df_enter_expire=pd.DataFrame(), df_exit_expire=pd.DataFrame()):

    ax = fplt.create_plot('Buy/Sell')
    fplt.candlestick_ochl(df[['open', 'close', 'high', 'low']], ax=ax, colorfunc=fplt.strength_colorfilter)

    # Add period separator lines
    #_add_time_separator(df)

    # Enter expired trade visualization
    if not df_enter_expire.empty:
        _add_enter_expire_tos(df_enter_expire)

    # Exit expired trade visualization
    if not df_exit_expire.empty:
        _add_exit_expire_tos(df_exit_expire)

    if not df_closed.empty:
        _add_closed_tos(ax, df_closed) # NOTE: Plot the closed ones last to make sure they are in front

    fplt.add_legend('', ax=ax)
    fplt.show()


def _add_time_separator(df):
    periods = pd.to_datetime(df.index, unit='ms').strftime('%H')
    last_period = ''
    for x,(period,price) in enumerate(zip(periods, df.close)):
        if period != last_period:
            fplt.add_line((x-0.5, price*0.5), (x-0.5, price*2), color='#bbb', style='--')
        last_period = period


def _add_enter_expire_tos(df_enter_expire):
    for idx, row in df_enter_expire.iterrows():
        fplt.add_line((row['decision_time'], row['enterPrice']), (row['enterExpire'], row['enterPrice']), color='#9900ff', interactive=False)


def _add_exit_expire_tos(df_exit_expire):
    for idx, row in df_exit_expire.iterrows():
        fplt.add_rect((row['decision_time'], row['exitPrice']), (row['exitExpire'], row['enterPrice']), color='#FFFF00', interactive=True)
        profit_perc = 100*(row['sellPrice']-row['enterPrice'])/row['enterPrice']
        fplt.add_text((row['decision_time'], row['exitPrice']), "%{:.2f}".format(profit_perc), color='#000000')
        fplt.add_line((row['decision_time'], row['enterPrice']), (row['exitExpire'], row['enterPrice']), color='#0000FF', width=3, interactive=False)
        fplt.add_line((row['decision_time'], row['sellPrice']), (row['exitExpire'], row['sellPrice']), color='#0000FF', width=3, interactive=False)


def _add_closed_tos(ax, df_closed):
    # Closed trade visualization (result.exit.type: limit or oco_limit)
    for idx, row in df_closed.iterrows():
        # NOTE: Calculation is based on "sellPrice" but the rect is based on "exitPrice"
        profit_perc = 100*(row['sellPrice']-row['enterPrice'])/row['enterPrice']

        # Stoploss taken
        if profit_perc < 0:
            trade_color = '#FF9090'
            rect_lower_limit = row['sellPrice']

        # Limit taken
        else:
            trade_color = '#60FF60'
            rect_lower_limit = row['enterPrice']

        fplt.add_rect((row['decision_time'], row['exitPrice']), (row['exitTime'], rect_lower_limit), color=trade_color, interactive=True)
        fplt.add_text((row['decision_time'], row['exitPrice']), "%{:.2f}".format(profit_perc), color='#000000')
        fplt.add_line((row['decision_time'], row['enterPrice']), (row['exitTime'], row['enterPrice']), color='#0000FF', width=3, interactive=False)


    # TODO: NEXT: Visualiztion of updated order, exit target price and sel price become the same if it is updated
    #               # sellPrice and exitPrice become the same and the rectangle does not appear
    df_closed.set_index('decision_time',inplace=True)
    duplicate_filter = df_closed.index.duplicated(keep=False)
    plot_spec = {'color':'#0000ff','style':'t2', 'ax':ax}
    _scatter_wrapper(serie=df_closed['enterPrice'], duplicate_filter=duplicate_filter, plot_spec=plot_spec)

    df_closed.set_index('exitTime',inplace=True)
    duplicate_filter = df_closed.index.duplicated(keep=False)
    plot_spec = {'color':'#ff0000','style':'v', 'ax':ax}
    _scatter_wrapper(serie=df_closed['sellPrice'], duplicate_filter=duplicate_filter, plot_spec=plot_spec)

    df_closed.set_index('enterTime',inplace=True)
    duplicate_filter = df_closed.index.duplicated(keep=False)
    plot_spec = {'color':'#00ff00','style':'^', 'ax':ax}
    _scatter_wrapper(serie=df_closed['enterPrice'], duplicate_filter=duplicate_filter, plot_spec=plot_spec)


def _scatter_wrapper(serie, duplicate_filter, plot_spec):
    # Visualize Non-duplicates
    serie[~duplicate_filter].plot(kind='scatter', color=plot_spec['color'], width=2, ax=plot_spec['ax'], zoomscale=False, style=plot_spec['style'])

    # Visualize Duplicates
    for row in serie[duplicate_filter].to_frame().iterrows():
        fplt.plot(x=row[0], y=float(row[1]), kind='scatter', color=plot_spec['color'], width=2, ax=plot_spec['ax'], zoomscale=False, style=plot_spec['style'])


if __name__ == '__main__':

    # Instantiate the parser
    # python .\scripts\fplot.py --filename .\test\data\btcusdt_15m_202005121212_202005131213.csv
    parser = argparse.ArgumentParser(description='Optional app description')
    parser.add_argument('--filename', type=str,)
    args = parser.parse_args()

    #fplot()
    buy_sell()
    #fplot_volume()
    #fplot_2row()
    #fplot_2row_scatter()
    #fplot_volume_profile()



