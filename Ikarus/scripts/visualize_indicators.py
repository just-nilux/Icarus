
import finplot as fplt
import json
from PyQt5.QtWidgets import QComboBox, QCheckBox, QWidget
from pyqtgraph import QtGui
import pyqtgraph as pg
from time import time as now, sleep
import sys
import asyncio
from binance import AsyncClient
from .. import binance_wrapper
import datetime
from itertools import chain
import itertools
from ..analyzers import Analyzer
from . import indicator_plot
from functools import partial

def change_asset(*args, **kwargs):
    '''Resets and recalculates everything, and plots for the first time.'''
    # save window zoom position before resetting  
    #fplt._savewindata(fplt.windows[0])

    symbol = ctrl_panel.symbol.currentText()
    interval = ctrl_panel.interval.currentText()
    indicator = ctrl_panel.indicators.currentText().lower()

    # remove any previous plots
    if ctrl_panel.autoclear.isChecked() or "symbol" in args:
        ax.reset()
        axo.reset()
        ax_bot.reset()
        axo_bot.reset()

    fplt.candlestick_ochl(data_dict[symbol][interval]['open close high low'.split()], ax=ax, colorfunc=fplt.strength_colorfilter)
    #fplt.volume_ocv(data_dict[symbol][interval]['open close volume'.split()], ax=axo)

    # Visualize indicators
    if indicator != 'clean':
        if hasattr(indicator_plot, indicator):
            handler = getattr(indicator_plot, indicator)
            handler(data_dict[symbol][interval].index, analysis_dict[symbol][interval][indicator], 
                {'ax':ax, 'axo':axo, 'ax_bot':ax_bot, 'axo_bot':axo_bot})

    ax.set_visible(xaxis=True)
    # restores saved zoom position, if in range
    fplt.refresh()


def dark_mode_toggle(dark):

    # first set the colors we'll be using
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
    vbs = set([ax.vb for ax in axs])
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


def create_ctrl_panel(win, pairs, time_scales, indicators):
    panel = QWidget(win)
    panel.move(150, 0)
    win.scene().addWidget(panel)
    layout = QtGui.QGridLayout(panel)

    panel.symbol = QComboBox(panel)
    [panel.symbol.addItem(pair) for pair in pairs]
    panel.symbol.setCurrentIndex(0)
    layout.addWidget(panel.symbol, 0, 0)
    panel.symbol.currentTextChanged.connect(partial(change_asset, "symbol"))

    layout.setColumnMinimumWidth(1, 30)

    panel.interval = QComboBox(panel)
    [panel.interval.addItem(scale) for scale in time_scales]
    panel.interval.setCurrentIndex(0)
    layout.addWidget(panel.interval, 0, 2)
    panel.interval.currentTextChanged.connect(partial(change_asset, "interval"))

    layout.setColumnMinimumWidth(3, 30)

    panel.indicators = QComboBox(panel)
    panel.indicators.addItem('clean')
    [panel.indicators.addItem(ind) for ind in indicators]
    panel.indicators.setCurrentIndex(0)
    layout.addWidget(panel.indicators, 0, 4)
    panel.indicators.currentTextChanged.connect(partial(change_asset, "indicators"))

    layout.setColumnMinimumWidth(5, 30)

    panel.darkmode = QCheckBox(panel)
    panel.darkmode.setText('Haxxor mode')
    panel.darkmode.setCheckState(2)
    panel.darkmode.toggled.connect(dark_mode_toggle)
    layout.addWidget(panel.darkmode, 0, 6)

    layout.setColumnMinimumWidth(5, 30)

    panel.autoclear = QCheckBox(panel)
    panel.autoclear.setText('Autoclear')
    panel.autoclear.setCheckState(2)
    layout.addWidget(panel.autoclear, 0, 8)

    return panel


def analysis_dashboard(pair_pool, time_scale_pool, indicator_pool, title='Buy/Sell Plot'):

    global ctrl_panel, ax, axo, ax_bot, axo_bot, pair_data, pair_analysis, ax_bar
    pair_data = data_dict
    pair_analysis = analysis_dict

    print("buy sell dahsboard")
    
    # Set dashboard specifics
    fplt.display_timezone = datetime.timezone.utc
    fplt.y_pad = 0.07 # pad some extra (for control panel)
    fplt.max_zoom_points = 7
    fplt.autoviewrestore()
    ax,ax_bar,ax_bot = fplt.create_plot(title, rows=3, init_zoom_periods=300, scaleing=[2,0.1,1])
    axo = ax.overlay()
    axo_bot = ax_bot.overlay()
    ax_bar.hide()
    ax_bot.hide()
    ax_bot.vb.setBackgroundColor(None) # don't use odd background color
    ax.set_visible(xaxis=True)

    ctrl_panel = create_ctrl_panel(ax.vb.win, pair_pool, time_scale_pool, indicator_pool)
    dark_mode_toggle(False)
    change_asset()

    fplt.show()


async def visualize_dashboard(bwrapper, config):

    start_time = datetime.datetime.strptime(config['backtest']['start_time'], "%Y-%m-%d %H:%M:%S")
    start_timestamp = int(datetime.datetime.timestamp(start_time))*1000
    end_time = datetime.datetime.strptime(config['backtest']['end_time'], "%Y-%m-%d %H:%M:%S")
    end_timestamp = int(datetime.datetime.timestamp(end_time))*1000

    # Create pools for pair-scales
    time_scale_pool = []
    pair_pool = []
    for strategy in config['strategy'].values():
        time_scale_pool.append(strategy['time_scales'])
        pair_pool.append(strategy['pairs'])

    time_scale_pool = list(set(chain(*time_scale_pool)))
    pair_pool = list(set(chain(*pair_pool)))

    meta_data_pool = list(itertools.product(time_scale_pool, pair_pool))

    global data_dict, analysis_dict
    data_dict = await bwrapper.download_all_data(meta_data_pool, start_timestamp, end_timestamp)
    analyzer = Analyzer(config)
    analysis_dict = await analyzer.visual_analysis(data_dict)

    indicators = list(config['visualization']['indicators'].keys()) + config['visualization']['patterns']
    analysis_dashboard(pair_pool, time_scale_pool, indicators, title=f'Visualizing Time Frame: {config["backtest"]["start_time"]} - {config["backtest"]["end_time"]}')


async def main():

    client = await AsyncClient.create(api_key=cred_info['Binance']['Test']['PUBLIC-KEY'],
                                    api_secret=cred_info['Binance']['Test']['SECRET-KEY'])
    bwrapper = binance_wrapper.TestBinanceWrapper(client, config)
    await visualize_dashboard(bwrapper, config)


if __name__ == '__main__':
    print(sys.argv)
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

