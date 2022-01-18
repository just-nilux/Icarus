from enum import unique
import finplot as fplt
from statistics import mean
from itertools import groupby
import pandas as pd
import numpy as np
from operator import itemgetter

# Custom analyzers
def market_classifier(x, y, axes): 
    color_set = ['#FF8080', '#80FF80', '#8080FF', '#80FFFF', '#FF80FF' '#FFFF80'] # 6 Class is currently enough to model

    enable_ax_bot(axes, y_range=(0,len(y.keys())))
    fplt.plot(x, y=[len(y.keys())]*len(x), ax=axes['ax_bot'])

    for class_idx, (class_name, filter_idx) in enumerate(y.items()):
        for k, g in groupby(enumerate(filter_idx), lambda ix: ix[0] - ix[1]):
            seq_idx = list(map(itemgetter(1), g))
            fplt.add_rect((x[seq_idx[0]], class_idx+1), (x[seq_idx[-1]], class_idx), color=color_set[class_idx], interactive=False, ax=axes['ax_bot'])
        fplt.add_text((x[0], class_idx+0.5), class_name, color='#000000',anchor=(0,0), ax=axes['ax_bot'])


def fractal_line_3(x, y, axes): disable_ax_bot(axes); line_handler(x, y, axes['ax'])
def fractal_aroon(x, y, axes): enable_ax_bot(axes, y_range=(0,100)); line_handler(x, y, axes['ax_bot'])
def fractal_aroonosc(x, y, axes): enable_ax_bot(axes, y_range=(-100,100)); line_handler(x, y, axes['ax_bot'])

def kmeans(x, y, axes): 
    disable_ax_bot(axes)
    # Visualize Support Lines
    #for sr_level in y['low_cls']:
    #    fplt.add_line((x[0], sr_level), (x[-1], sr_level), style='.', color='#0000FF', width=2, interactive=False)

    # Visualize Resistance Lines
    #for sr_level in y['high_cls']:
    #    fplt.add_line((x[0], sr_level), (x[-1], sr_level), style='.', color='#FF0000', width=2, interactive=False)
    for sr_level in y['low_cls']:
        fplt.add_line((x[0], mean(sr_level)), (x[-1], mean(sr_level)), style='.', color='#0000FF', width=2, interactive=False)
        fplt.add_band(min(sr_level), max(sr_level), ax=axes['ax'], color='#CCCCFF')

    # Visualize Resistance Lines
    for sr_level in y['high_cls']:
        fplt.add_line((x[0], mean(sr_level)), (x[-1], mean(sr_level)), style='.', color='#FF0000', width=2, interactive=False)
        fplt.add_band(min(sr_level), max(sr_level), ax=axes['ax'], color='#FFCCCC')

def support_dbscan(x, y, axes): disable_ax_bot(axes); support_handler(x, y, axes)
def support_mshift(x, y, axes): disable_ax_bot(axes); support_handler(x, y, axes)
def resistance_dbscan(x, y, axes): disable_ax_bot(axes); resistance_handler(x, y, axes)
def resistance_mshift(x, y, axes): disable_ax_bot(axes); resistance_handler(x, y, axes)

def bullish_fractal_5(x, y, axes): 
    disable_ax_bot(axes)
    fplt.plot(x=x, y=y, kind='scatter', color='#0000ff', width=2, ax=axes['ax'], zoomscale=False, style='d')

def bearish_fractal_5(x, y, axes): 
    disable_ax_bot(axes)
    fplt.plot(x=x, y=y, kind='scatter', color='#ff00ff', width=2, ax=axes['ax'], zoomscale=False, style='d')

def bullish_fractal_3(x, y, axes): 
    disable_ax_bot(axes)
    fplt.plot(x=x, y=y, kind='scatter', color='#0000ff', width=2, ax=axes['ax'], zoomscale=False, style='d')

def bearish_fractal_3(x, y, axes): 
    disable_ax_bot(axes)
    fplt.plot(x=x, y=y, kind='scatter', color='#ff00ff', width=2, ax=axes['ax'], zoomscale=False, style='d')


# TA-LIB Indicators
def ma(x, y, axes): disable_ax_bot(axes); line_handler(x, y, axes['ax'])
def rsi(x, y, axes): enable_ax_bot(axes, y_range=(0,100), band=(30,70)); scatter_handler(x, y, axes['ax_bot'])
def bband(x, y, axes): disable_ax_bot(axes); line_handler(x, y, axes['ax'])
def macd(x, y, axes): 
    # BUG: Choosing rsi first and choosing macd second causes trouble due to fplt.set_y_range
    axes['ax'].set_visible(xaxis=False)
    fplt._ax_reset(axes['ax_bot'])
    axes['ax_bot'].show()
    line_handler(x, {'macd': y['macd'], 'macdsignal':y['macdsignal']}, axes['ax_bot'])
    fplt.bar(x, y['macdhist'], ax=axes['axo_bot'])
    axes['axo_bot'].show()

# Momentum Indicators
def adx(x, y, axes): enable_ax_bot(axes, y_range=(0,100), band=(25,50)); line_handler(x, y, axes['ax_bot'])
def adxr(x, y, axes): enable_ax_bot(axes, y_range=(0,100), band=(25,50)); line_handler(x, y, axes['ax_bot'])
def aroon(x, y, axes): enable_ax_bot(axes, y_range=(0,100)); line_handler(x, y, axes['ax_bot'])
def aroonosc(x, y, axes): enable_ax_bot(axes, y_range=(-100,100)); line_handler(x, y, axes['ax_bot'])
def roc(x, y, axes): enable_ax_bot(axes); line_handler(x, y, axes['ax_bot'])
def rocp(x, y, axes): enable_ax_bot(axes); line_handler(x, y, axes['ax_bot'])
def rocr(x, y, axes): enable_ax_bot(axes); line_handler(x, y, axes['ax_bot'])
def rocr100(x, y, axes): enable_ax_bot(axes); line_handler(x, y, axes['ax_bot'])

# Volatility Indicators
def atr(x, y, axes): enable_ax_bot(axes); line_handler(x, y, axes['ax_bot'])
def natr(x, y, axes): enable_ax_bot(axes); line_handler(x, y, axes['ax_bot'])
def trange(x, y, axes): enable_ax_bot(axes); line_handler(x, y, axes['ax_bot'])

# TA-LIB Patterns
def cdleveningstar(x, y, axes): disable_ax_bot(axes); scatter_handler(x, y, axes['ax'])
def cdlmorningstar(x, y, axes): disable_ax_bot(axes); scatter_handler(x, y, axes['ax'])

def support_handler(x, y, axes):
    hover_label = fplt.add_legend('aaa', ax=axes['ax'])
    hover_label.setText("Support", color='#0000FF', bold=True)
    # TODO: Find a way to add proper legend
    # Visualize Support Lines
    for sr_level in y:
        fplt.add_line((x[0], mean(sr_level)), (x[-1], mean(sr_level)), style='.', color='#0000FF', width=2, interactive=False)
        fplt.add_band(min(sr_level), max(sr_level), ax=axes['ax'], color='#CCCCFF')

def resistance_handler(x, y, axes):
    hover_label = fplt.add_legend('aaa', ax=axes['ax'])
    hover_label.setText("Resistance", color='#FF0000', bold=True)
    # TODO: Find a way to add proper legend
    # Visualize Resistance Lines
    for sr_level in y:
        fplt.add_line((x[0], mean(sr_level)), (x[-1], mean(sr_level)), style='.', color='#FF0000', width=2, interactive=False)
        fplt.add_band(min(sr_level), max(sr_level), ax=axes['ax'], color='#FFCCCC')

# Helper functions for indicator visualization
def line_handler(x, y, axis):
    # TODO: Improve the plot configuration, such as legend texts and the colors
    if type(y) == dict:
        # Handling dict of list
        for param, data in y.items():
            fplt.plot(x, data, width=3, ax=axis, legend=str(param))

    elif type(y) == list:
        # Handling list of list
        if all(isinstance(el, list) for el in y): 
            for sub_list in y:
                fplt.plot(x, sub_list, width=3, ax=axis, color='#0000ff')

        # Handling list
        else:
            fplt.plot(x, y, width=3, ax=axis)

def scatter_handler(x, y, axis):
    fplt.plot(x=x, y=y, kind='scatter', color='#0000ff', width=1, ax=axis, zoomscale=False, style='d')

def enable_ax_bot(axes, **kwargs):
    axes['ax'].set_visible(xaxis=False)
    axes['ax_bot'].show()

    #if kwargs.get('reset', True): fplt._ax_reset(axes['ax_bot'])
    if y_range := kwargs.get('y_range', None): fplt.set_y_range(y_range[0], y_range[1], ax=axes['ax_bot'])
    if band := kwargs.get('band', None): fplt.add_band(band[0], band[1], color='#6335', ax=axes['ax_bot'])


def disable_ax_bot(axes):
    axes['ax'].set_visible(xaxis=True)
    axes['ax_bot'].hide()

