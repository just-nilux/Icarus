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
import datetime
from functools import lru_cache
import pandas as pd
from PyQt5.QtWidgets import QComboBox, QCheckBox, QWidget
from pyqtgraph import QtGui
import pyqtgraph as pg
from copy import deepcopy

dashboard_data = {}
ax, axo, ctrl_panel = '', '', ''
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
    fplt.volume_ocv(df[['open','close','volume']], ax=axo, colorfunc=fplt.strength_colorfilter)
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


def buy_sell(df, df_closed=pd.DataFrame(), df_enter_expire=pd.DataFrame(), df_exit_expire=pd.DataFrame(), title='Buy/Sell Plot'):

    if df.empty:
        print('OCHL is empty')
        return
    fplt.display_timezone = datetime.timezone.utc

    ax = fplt.create_plot(title)
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
        fplt.add_text((row['decision_time'], row['enterPrice']), "{}".format(row['strategy']), color='#000000')



def _add_exit_expire_tos(df_exit_expire):
    for idx, row in df_exit_expire.iterrows():
        fplt.add_rect((row['decision_time'], row['exitPrice']), (row['exitExpire'], row['enterPrice']), color='#FFFF00', interactive=True)
        profit_perc = 100*(row['sellPrice']-row['enterPrice'])/row['enterPrice']
        fplt.add_text((row['decision_time'], row['exitPrice']), "%{:.2f}".format(profit_perc), color='#000000')
        fplt.add_text((row['decision_time'], row['enterPrice']), "{}".format(row['strategy']), color='#000000')
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
        fplt.add_text((row['decision_time'], row['enterPrice']), "{}".format(row['strategy']), color='#000000')
        fplt.add_line((row['decision_time'], row['enterPrice']), (row['exitTime'], row['enterPrice']), color='#0000FF', width=3, interactive=False)
    x=0
    pass


    # TODO: NEXT: Visualiztion of updated order, exit target price and sel price become the same if it is updated
    #               # sellPrice and exitPrice become the same and the rectangle does not appear
    df_closed.set_index('decision_time',inplace=True)
    duplicate_filter = df_closed.index.duplicated(keep=False)
    plot_spec = {'color':'#0000ff','style':'t2', 'ax':ax, 'legend':'Decision Point'}
    _scatter_wrapper(serie=df_closed['enterPrice'], duplicate_filter=duplicate_filter, plot_spec=plot_spec)

    df_closed.set_index('exitTime',inplace=True)
    duplicate_filter = df_closed.index.duplicated(keep=False)
    plot_spec = {'color':'#ff0000','style':'v', 'ax':ax, 'legend':'Sell Point'}
    _scatter_wrapper(serie=df_closed['sellPrice'], duplicate_filter=duplicate_filter, plot_spec=plot_spec)

    df_closed.set_index('enterTime',inplace=True)
    duplicate_filter = df_closed.index.duplicated(keep=False)
    plot_spec = {'color':'#00ff00','style':'^', 'ax':ax, 'legend':'Buy Point'}
    _scatter_wrapper(serie=df_closed['enterPrice'], duplicate_filter=duplicate_filter, plot_spec=plot_spec)
    # TODO: Fix the multiple buy point legend text


def _scatter_wrapper(serie, duplicate_filter, plot_spec):
    # Visualize Non-duplicates
    serie[~duplicate_filter].plot(kind='scatter', color=plot_spec['color'], width=2, ax=plot_spec['ax'], zoomscale=False, style=plot_spec['style'], legend=plot_spec['legend'])

    # Visualize Duplicates
    for row in serie[duplicate_filter].to_frame().iterrows():
        fplt.plot(x=row[0], y=float(row[1]), kind='scatter', color=plot_spec['color'], width=2, ax=plot_spec['ax'], zoomscale=False, style=plot_spec['style'], legend=plot_spec['legend'])


def change_asset():
    '''Resets and recalculates everything, and plots for the first time.'''
    '''
    dashboard_data = {
        'BTCUSDT':{
            'df':pd.DataFrame,
            'df_enter_expire':pd.DataFrame,
            ...
        }
        ...
    }
    '''
    # save window zoom position before resetting
    #fplt._savewindata(fplt.windows[0])

    symbol = ctrl_panel.symbol.currentText()
    print(symbol)

    # remove any previous plots
    ax.reset()
    axo.reset()
    # TODO: Fix the QGraphicsScene::removeItem: error
    #       It is caused by the rectangles in green and red

    fplt.candlestick_ochl(dashboard_data[symbol]['df']['open close high low'.split()], ax=ax, colorfunc=fplt.strength_colorfilter)
    fplt.volume_ocv(dashboard_data[symbol]['df']['open close volume'.split()], ax=axo)
    ax.set_visible(xaxis=True)

    if not dashboard_data[symbol]['df_enter_expire'].empty:
        _add_enter_expire_tos(deepcopy(dashboard_data[symbol]['df_enter_expire']))

    # Exit expired trade visualization
    if not dashboard_data[symbol]['df_exit_expire'].empty:
        _add_exit_expire_tos(deepcopy(dashboard_data[symbol]['df_exit_expire']))

    if not dashboard_data[symbol]['df_closed'].empty:
        _add_closed_tos(ax, deepcopy(dashboard_data[symbol]['df_closed'])) # NOTE: Plot the closed ones last to make sure they are in front

    # restores saved zoom position, if in range
    fplt.refresh()


def dark_mode_toggle(dark):
    '''Digs into the internals of finplot and pyqtgraph to change the colors of existing
       plots, axes, backgronds, etc.'''
    # first set the colors we'll be using
    
    # TODO: Get rid of the dark mode redundency
    if dark:
        fplt.foreground = '#777'
        fplt.background = '#090c0e'
        fplt.candle_bull_color = fplt.candle_bull_body_color = '#0b0'
        fplt.candle_bear_color = '#a23'
        volume_transparency = '6'
    else:
        fplt.foreground = '#444'
        fplt.background = fplt.candle_bull_body_color = '#fff'
        fplt.candle_bull_color = '#380'
        fplt.candle_bear_color = '#c50'
        volume_transparency = 'c'
    fplt.volume_bull_color = fplt.volume_bull_body_color = fplt.candle_bull_color + volume_transparency
    fplt.volume_bear_color = fplt.candle_bear_color + volume_transparency
    fplt.cross_hair_color = fplt.foreground+'8'
    fplt.draw_line_color = '#888'
    fplt.draw_done_color = '#555'

    pg.setConfigOptions(foreground=fplt.foreground, background=fplt.background)
    # control panel color
    if ctrl_panel is not None:
        p = ctrl_panel.palette()
        p.setColor(ctrl_panel.darkmode.foregroundRole(), pg.mkColor(fplt.foreground))
        ctrl_panel.darkmode.setPalette(p)

    # window background
    for win in fplt.windows:
        win.setBackground(fplt.background)

    # axis, crosshair, candlesticks, volumes
    axs = [ax for win in fplt.windows for ax in win.axs]
    axs += fplt.overlay_axs
    axis_pen = fplt._makepen(color=fplt.foreground)
    for ax in axs:
        ax.axes['left']['item'].setPen(axis_pen)
        ax.axes['left']['item'].setTextPen(axis_pen)
        ax.axes['bottom']['item'].setPen(axis_pen)
        ax.axes['bottom']['item'].setTextPen(axis_pen)
        if ax.crosshair is not None:
            ax.crosshair.vline.pen.setColor(pg.mkColor(fplt.foreground))
            ax.crosshair.hline.pen.setColor(pg.mkColor(fplt.foreground))
            ax.crosshair.xtext.setColor(fplt.foreground)
            ax.crosshair.ytext.setColor(fplt.foreground)
        for item in ax.items:
            if isinstance(item, fplt.FinPlotItem):
                isvolume = ax in fplt.overlay_axs
                if not isvolume:
                    item.colors.update(
                        dict(bull_shadow      = fplt.candle_bull_color,
                             bull_frame       = fplt.candle_bull_color,
                             bull_body        = fplt.candle_bull_body_color,
                             bear_shadow      = fplt.candle_bear_color,
                             bear_frame       = fplt.candle_bear_color,
                             bear_body        = fplt.candle_bear_color))
                else:
                    item.colors.update(
                        dict(bull_frame       = fplt.volume_bull_color,
                             bull_body        = fplt.volume_bull_body_color,
                             bear_frame       = fplt.volume_bear_color,
                             bear_body        = fplt.volume_bear_color))
                item.repaint()


def create_ctrl_panel(win, pairs):
    panel = QWidget(win)
    panel.move(200, 0)
    win.scene().addWidget(panel)
    layout = QtGui.QGridLayout(panel)

    panel.symbol = QComboBox(panel)
    [panel.symbol.addItem(pair) for pair in pairs]
    panel.symbol.setCurrentIndex(1)
    layout.addWidget(panel.symbol, 0, 0)
    panel.symbol.currentTextChanged.connect(change_asset)

    layout.setColumnMinimumWidth(1, 30)

    panel.darkmode = QCheckBox(panel)
    panel.darkmode.setText('Haxxor mode')
    panel.darkmode.setCheckState(2)
    panel.darkmode.toggled.connect(dark_mode_toggle)
    layout.addWidget(panel.darkmode, 0, 6)

    return panel


def buy_sell_dashboard(dashboard_data_pack, title='Buy/Sell Plot'):

    '''
    data logic of the buy_sell function needs to change since dahs board requires all in once
    '''
    # TODO: Find an alternative to this global implementation. This looks ugly
    global ctrl_panel, ax, axo, dashboard_data
    dashboard_data = dashboard_data_pack

    print("buy sell dahsboard")
    
    # Set dashboard specifics
    fplt.display_timezone = datetime.timezone.utc
    fplt.y_pad = 0.07 # pad some extra (for control panel)
    fplt.max_zoom_points = 7
    fplt.autoviewrestore()

    ax = fplt.create_plot(title)
    axo = ax.overlay()
    ax.set_visible(xaxis=True)

    ctrl_panel = create_ctrl_panel(ax.vb.win,list(dashboard_data.keys()))
    dark_mode_toggle(False)
    change_asset()

    fplt.show()


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



