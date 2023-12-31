import finplot as fplt
from statistics import mean
import pandas as pd
import numpy as np


color_map_support = [
    ('#0000FF', '#CCCCFF'),
    ('#00FF00', '#CCFFCC')
]

color_map_resistance = [
    ('#FF0000', '#FFCCCC'),
    ('#FFFB00', '#FFFBCC')
]

color_map_cluster = [
    ('#FF00FF', '#FFCCFF'),
    ('#00FFFF', '#CCFFFF')
]

#####################################  Fundamental Handler Fuctions ######################################

def fibonacci_handler(x, y, axes):

    hover_label = fplt.add_legend('aaa', ax=axes['ax'])
    hover_label.setText(f"Fibonacci Levels", color='#0000FF', bold=True)
    #hover_label.setText(f'<textarea name="Text1" cols="40" rows="5"></textarea>', color='#0000FF', bold=True)

    # Visualize Support Lines
    for fibo_cluster in y:
        if fibo_cluster.vertical_distribution_score == 0:
            overall_score = 0
        else:
            overall_score = round(fibo_cluster.horizontal_distribution_score/fibo_cluster.vertical_distribution_score,2)

        text_bot = "HorDist:{}, VerDist:{}, Score:{}".format(
            fibo_cluster.horizontal_distribution_score, 
            fibo_cluster.vertical_distribution_score, 
            overall_score)

        text_top = "Fibonacci Level: {}, #Members:{}".format(fibo_cluster.level, len(fibo_cluster.centroids))

        fplt.add_text((x[0], fibo_cluster.price_level), text_bot, color='#000000',anchor=(0,0), ax=axes['ax'])
        fplt.add_text((x[0], fibo_cluster.price_level), text_top, color='#000000',anchor=(0,1), ax=axes['ax'])
        fplt.add_line((x[0], fibo_cluster.price_level), (x[-1], fibo_cluster.price_level), style='.', color='#0000FF', width=2, interactive=False)
        if len(fibo_cluster.centroids):
            fplt.add_rect((x[fibo_cluster.validation_index], max(fibo_cluster.centroids)), (x[-1], min(fibo_cluster.centroids)), ax=axes['ax'], color='#CCCCFF')


def support_resistance_handler(x, y, axes, **kwargs):
    sr_type = kwargs.get('type','')
    sr_cmap = kwargs.get('cmap',[('#0000FF', '#CCCCFF')])

    hover_label = fplt.add_legend('aaa', ax=axes['ax'])
    hover_label.setText(sr_type, color=sr_cmap[0][0], bold=True)
    #hover_label.setText(f'<textarea name="Text1" cols="40" rows="5"></textarea>', color='#0000FF', bold=True)

    # Color Map params
    colormap_idx = 0
    start_idx = None

    for sr_cluster in y:

        if start_idx == None:
            start_idx = sr_cluster.chunk_start_index

        # Change color of cluster based on the start_index of cluster
        if start_idx != sr_cluster.chunk_start_index:
            start_idx = sr_cluster.chunk_start_index
            colormap_idx += 1
            colormap_idx = colormap_idx % len(color_map_support)

        text_bot = "HorDist:{}, VerDist:{}, Dist:{}".format(
            sr_cluster.horizontal_distribution_score, 
            sr_cluster.vertical_distribution_score, 
            sr_cluster.distribution_score)

        text_top_left = "#MinMember: {}, #NumOfRetest:{}".format(sr_cluster.min_cluster_members,sr_cluster.number_of_retest)
        text_top_right = "#Frame:{}".format(sr_cluster.chunk_end_index-sr_cluster.chunk_start_index)
        fplt.add_text((x[sr_cluster.chunk_end_index], mean(sr_cluster.centroids)), text_top_right, color='#000000',anchor=(1,1), ax=axes['ax'])
        fplt.add_text((x[sr_cluster.chunk_start_index], mean(sr_cluster.centroids)), text_bot, color='#000000',anchor=(0,0), ax=axes['ax'])
        fplt.add_text((x[sr_cluster.chunk_start_index], mean(sr_cluster.centroids)), text_top_left, color='#000000',anchor=(0,1), ax=axes['ax'])
        fplt.add_line((x[sr_cluster.chunk_start_index], mean(sr_cluster.centroids)), 
            (x[sr_cluster.chunk_end_index], mean(sr_cluster.centroids)), style='.', color=sr_cmap[colormap_idx][0], width=2, interactive=False)
        fplt.add_rect((x[sr_cluster.validation_index], max(sr_cluster.centroids)), 
            (x[sr_cluster.chunk_end_index], min(sr_cluster.centroids)), ax=axes['ax'], color=sr_cmap[colormap_idx][1])


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


def bar_handler(x, y, axis):
    fplt.bar(x, y, axis)


def scatter_handler(x, y, axis):
    fplt.plot(x=x, y=y, kind='scatter', color='#0000ff', width=1, ax=axis, zoomscale=False, style='d')

def add_time_separator(x, period_in_ms, **kwargs):
    diff_in_ms = int((x[1]-x[0]))
    ms_half_tick = int(diff_in_ms/2)

    if period_in_ms <= diff_in_ms:
        return []
    
    start_ts = 0
    for ts in x:
        if ts % period_in_ms == 0: 
            start_ts = ts
            break

    for ts in range(start_ts,x[-1],period_in_ms):
        fplt.add_line((ts-ms_half_tick, kwargs.get('y_bot',0)), (ts-ms_half_tick, kwargs.get('y_top',300000)), color='#bbb', style='--')

def enable_ax_bot(axes, **kwargs):
    fplt._ax_reset(axes['ax_bot'])

    axes['ax'].set_visible(xaxis=False)
    axes['ax_bot'].show()

    #if kwargs.get('reset', True): fplt._ax_reset(axes['ax_bot'])
    if y_range := kwargs.get('y_range', None): fplt.set_y_range(y_range[0], y_range[1], ax=axes['ax_bot'])
    if band := kwargs.get('band', None): fplt.add_band(band[0], band[1], color='#6335', ax=axes['ax_bot'])


def market_class_handler(x, y, axes): 
    # Visualization on ax_bot as class rows
    color_set = ['#FF8080', '#8080FF', '#80FF80', '#80FFFF', '#FF80FF', '#FFFF80'] # 6 Color is enough to distinguish classes

    enable_ax_bot(axes, y_range=(0,len(y.keys())))
    fplt.plot(x, y=[len(y.keys())]*len(x), ax=axes['ax_bot'])

    # NOTE: No difference in the evaluation of the y even if it is a dictionary or a list. Since it helps in visualizaiton. The dict format is left as it is.
    for class_idx, (class_name, class_item_list) in enumerate(y.items()):
        for market_regime in class_item_list:
            fplt.add_rect((market_regime.start_ts, class_idx+1), (market_regime.end_ts, class_idx), color=color_set[class_idx%6], interactive=False, ax=axes['ax_bot'])
            
            perc_price_change = f'PPC: %{str(market_regime.perc_price_change)}'
            fplt.add_text((market_regime.start_ts, class_idx+1), perc_price_change, color='#000000',anchor=(0,0), ax=axes['ax_bot'])

            perc_val_price_change = f'PVPC: %{str(market_regime.perc_val_price_change)}'
            fplt.add_text((market_regime.start_ts, class_idx+0.8), perc_val_price_change, color='#000000',anchor=(0,0), ax=axes['ax_bot'])

            num_of_candle = f'#Candle: {str(market_regime.duration_in_candle)}'
            fplt.add_text((market_regime.start_ts, class_idx+0.6), num_of_candle, color='#000000',anchor=(0,0), ax=axes['ax_bot'])

            fplt.add_line((market_regime.validation_ts, class_idx+1), (market_regime.validation_ts, class_idx), style='.', color='#000000', width=2, interactive=False, ax=axes['ax_bot'])
            #fplt.add_line((market_regime.validation_ts, class_idx+1), (market_regime.validation_ts, class_idx), style='.', color='#000000', width=2, interactive=False, ax=axes['ax_bot'])

        fplt.add_text((x[0], class_idx+0.5), class_name, color='#000000',anchor=(0,0), ax=axes['ax_bot'])

    # Visualization on ax as class rows
    for class_idx, (class_name, class_item_list) in enumerate(y.items()):
        for market_regime in class_item_list:
            fplt.add_rect((market_regime.start_ts, market_regime.start_price), (market_regime.end_ts, market_regime.end_price), color=color_set[class_idx%6], interactive=False, ax=axes['ax'])

def disable_ax_bot(axes):
    axes['ax'].set_visible(xaxis=True)
    axes['ax_bot'].hide()

#####################################  Custom Analyzer Visualization #####################################
def hmm(x, y, axes): market_class_handler(x, y, axes)
def market_class_aroon(x, y, axes): market_class_handler(x, y, axes)
def market_class_aroonosc(x, y, axes): market_class_handler(x, y, axes)
def market_class_fractal_aroon(x, y, axes): market_class_handler(x, y, axes)

def mkfi_colorfilter(item, datasrc, df):
    tokens = df['tokens'].copy()

    # NOTE: Shitty Code to work around
    new_df = pd.DataFrame(index=df.index)
    new_df['open_time'] = df['open_time']
    new_df['_base_'] = 0
    new_df['mkfi'] = df['mkfi']
    new_df['_open_'] = 0
    new_df['_close_'] = 0

    # TODO: Color update
    yield ['#00DA00', '#00DA00', '#00DA00'] + [new_df.loc[tokens == 1]]
    yield ['#DBE94B', '#DBE94B', '#DBE94B'] + [new_df.loc[tokens == 2]]
    yield ['#0036FF', '#0036FF', '#0036FF'] + [new_df.loc[tokens == 3]]
    yield ['#FF68F1', '#FF68F1', '#FF68F1'] + [new_df.loc[tokens == 4]]

def mkfi(x, y, axes):
    df = pd.DataFrame.from_dict(y)
    df.set_index(x, inplace=True)
    enable_ax_bot(axes, y_range=(min(y['mkfi']),max(y['mkfi'])))
    fplt.bar(df, ax=axes['ax_bot'],colorfunc=mkfi_colorfilter)

def fractal_line_3(x, y, axes): axes['ax'].set_visible(xaxis=True); line_handler(x, y, axes['ax'])
def fractal_aroon(x, y, axes): enable_ax_bot(axes, y_range=(0,100), ); line_handler(x, y, axes['ax_bot'])
def fractal_aroonosc(x, y, axes): enable_ax_bot(axes, y_range=(-100,100)); line_handler(x, y, axes['ax_bot'])

def support_birch(x, y, axes): disable_ax_bot(axes); support_resistance_handler(x, y, axes, **{'type':'Support', 'cmap':color_map_support})
def resistance_birch(x, y, axes): disable_ax_bot(axes); support_resistance_handler(x, y, axes, **{'type':'Resistance', 'cmap':color_map_resistance})
def support_optics(x, y, axes): disable_ax_bot(axes); support_resistance_handler(x, y, axes, **{'type':'Support', 'cmap':color_map_support})
def resistance_optics(x, y, axes): disable_ax_bot(axes); support_resistance_handler(x, y, axes, **{'type':'Resistance', 'cmap':color_map_resistance})
def support_meanshift(x, y, axes): disable_ax_bot(axes); support_resistance_handler(x, y, axes, **{'type':'Support', 'cmap':color_map_support})
def resistance_meanshift(x, y, axes): disable_ax_bot(axes); support_resistance_handler(x, y, axes, **{'type':'Resistance', 'cmap':color_map_resistance})
def support_dbscan(x, y, axes): disable_ax_bot(axes); support_resistance_handler(x, y, axes, **{'type':'Support', 'cmap':color_map_support})
def resistance_dbscan(x, y, axes): disable_ax_bot(axes); support_resistance_handler(x, y, axes, **{'type':'Resistance', 'cmap':color_map_resistance})
def support_kmeans(x, y, axes): disable_ax_bot(axes); support_resistance_handler(x, y, axes, **{'type':'Support', 'cmap':color_map_support})
def resistance_kmeans(x, y, axes): disable_ax_bot(axes); support_resistance_handler(x, y, axes, **{'type':'Resistance', 'cmap':color_map_resistance})
def fibonacci(x, y, axes): disable_ax_bot(axes); fibonacci_handler(x, y, axes)

def sr_birch(x, y, axes): disable_ax_bot(axes); support_resistance_handler(x, y, axes, **{'type':'Horizontal Clusters', 'cmap':color_map_cluster})
def sr_optics(x, y, axes): disable_ax_bot(axes); support_resistance_handler(x, y, axes, **{'type':'Horizontal Clusters', 'cmap':color_map_cluster})
def sr_meanshift(x, y, axes): disable_ax_bot(axes); support_resistance_handler(x, y, axes, **{'type':'Horizontal Clusters', 'cmap':color_map_cluster})
def sr_dbscan(x, y, axes): disable_ax_bot(axes); support_resistance_handler(x, y, axes, **{'type':'Horizontal Clusters', 'cmap':color_map_cluster})
def sr_kmeans(x, y, axes): disable_ax_bot(axes); support_resistance_handler(x, y, axes, **{'type':'Horizontal Clusters', 'cmap':color_map_cluster})

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

def parallel_ma(x, y, axes): disable_ax_bot(axes); line_handler(x, y, axes['ax'])

def rvol_colorfilter(item, datasrc, df):
    is_red = df['rvol']<0.8
    is_green = df['rvol']>1.25
    is_yellow = ~is_green & ~is_red
    yield ['#00DA00', '#00DA00', '#00DA00'] + [df.loc[is_green]]
    yield ['#DADA00', '#DADA00', '#DADA00'] + [df.loc[is_yellow]]
    yield ['#DA0000', '#DA0000', '#DA0000'] + [df.loc[is_red]]

def rvol(x, y, axes):

    # Do not visualize rvol for bigger timeframes starting from 1d
    diff_in_ms = int((x[1]-x[0]))
    ms_in_day = 86400000

    if ms_in_day <= diff_in_ms:
        return 

    enable_ax_bot(axes)
    df_rvol = pd.DataFrame(index=x)
    df_rvol['rvol'] = y

    fplt.bar(df_rvol, ax=axes['ax_bot'],colorfunc=rvol_colorfilter)

    # Make ax visible for the seperators
    axes['ax'].set_visible(xaxis=True)
    add_time_separator(x, 86400000)

def kaufman_efficiency_ratio(x, y, axes): enable_ax_bot(axes, y_range=(np.nanmin(y),np.nanmax(y))); line_handler(x, y, axes['ax_bot'])
def price_density(x, y, axes): enable_ax_bot(axes, y_range=(np.nanmin(y),np.nanmax(y))); line_handler(x, y, axes['ax_bot'])

####################################  TA-LIB Indicators Visualization ####################################

def ma(x, y, axes): disable_ax_bot(axes); line_handler(x, y, axes['ax'])
def rsi(x, y, axes): enable_ax_bot(axes, y_range=(0,100), band=(20,80)); line_handler(x, {'RSI':y}, axes['ax_bot'])
def stoch(x, y, axes): enable_ax_bot(axes, y_range=(0,100), band=(20,80)); line_handler(x, y, axes['ax_bot'])
def stochf(x, y, axes): enable_ax_bot(axes, y_range=(0,100), band=(20,80)); line_handler(x, y, axes['ax_bot'])
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
def aroon(x, y, axes): enable_ax_bot(axes, y_range=(0,100),band=(20,80)); line_handler(x, y, axes['ax_bot'])
def aroonosc(x, y, axes): enable_ax_bot(axes, y_range=(-100,100), band=(-50,50)); line_handler(x, y, axes['ax_bot'])
def mfi(x, y, axes): enable_ax_bot(axes, y_range=(0,100), band=(20,80)); line_handler(x, y, axes['ax_bot'])
def roc(x, y, axes): enable_ax_bot(axes); line_handler(x, y, axes['ax_bot'])
def rocp(x, y, axes): enable_ax_bot(axes); line_handler(x, y, axes['ax_bot'])
def rocr(x, y, axes): enable_ax_bot(axes); line_handler(x, y, axes['ax_bot'])
def rocr100(x, y, axes): enable_ax_bot(axes); line_handler(x, y, axes['ax_bot'])

# Volume indicators
def obv(x, y, axes): enable_ax_bot(axes, y_range=(min(y),max(y))); line_handler(x, y, axes['ax_bot'])
def ad(x, y, axes): enable_ax_bot(axes, y_range=(min(y),max(y))); line_handler(x, y, axes['ax_bot'])

# Volatility Indicators
def atr(x, y, axes): enable_ax_bot(axes); line_handler(x, y, axes['ax_bot'])
def natr(x, y, axes): enable_ax_bot(axes); line_handler(x, y, axes['ax_bot'])
def trange(x, y, axes): enable_ax_bot(axes); line_handler(x, y, axes['ax_bot'])

# TA-LIB Patterns
def cdleveningstar(x, y, axes): disable_ax_bot(axes); scatter_handler(x, y, axes['ax'])
def cdlmorningstar(x, y, axes): disable_ax_bot(axes); scatter_handler(x, y, axes['ax'])



