import finplot as fplt
from statistics import mean
#####################################  Fundamental Handler Fuctions ######################################

def support_handler(x, y, axes):

    if y:
        min_cluster_members = str(y[0].min_cluster_members)
    else:
        return
    hover_label = fplt.add_legend('aaa', ax=axes['ax'])
    hover_label.setText(f"Support<br/>Min Member:{min_cluster_members}", color='#0000FF', bold=True)

    #hover_label.setText(f'<textarea name="Text1" cols="40" rows="5"></textarea>', color='#0000FF', bold=True)

    # TODO: Find a way to add proper legend
    # Visualize Support Lines
    for sr_cluster in y:

        text_bot = "HorDist:{}, VerDist:{}, Score:{}".format(
            sr_cluster.horizontal_distribution_score, 
            sr_cluster.vertical_distribution_score, 
            round(sr_cluster.horizontal_distribution_score/sr_cluster.vertical_distribution_score,2))

        text_top = "#Members:{}".format(len(sr_cluster.centroids))

        fplt.add_text((x[0], mean(sr_cluster.centroids)), text_bot, color='#000000',anchor=(0,0), ax=axes['ax'])
        fplt.add_text((x[0], mean(sr_cluster.centroids)), text_top, color='#000000',anchor=(0,1), ax=axes['ax'])

        fplt.add_line((x[0], mean(sr_cluster.centroids)), (x[-1], mean(sr_cluster.centroids)), style='.', color='#0000FF', width=2, interactive=False)
        #fplt.add_band(min(sr_level), max(sr_level), ax=axes['ax'], color='#CCCCFF')
        fplt.add_rect((x[sr_cluster.validation_index], max(sr_cluster.centroids)), (x[-1], min(sr_cluster.centroids)), ax=axes['ax'], color='#CCCCFF')


def resistance_handler(x, y, axes):

    if y:
        min_cluster_members = str(y[0].min_cluster_members)
    else:
        return
    hover_label = fplt.add_legend('aaa', ax=axes['ax'])
    hover_label.setText(f"Resistance<br/>Min Member:{min_cluster_members}", color='#0000FF', bold=True)


    # Visualize Resistance Lines
    for sr_cluster in y:
        text_bot = "HorDist:{}, VerDist:{}, Score:{}".format(
            sr_cluster.horizontal_distribution_score, 
            sr_cluster.vertical_distribution_score, 
            round(sr_cluster.horizontal_distribution_score/sr_cluster.vertical_distribution_score,2))

        text_top = "#Members:{}".format(len(sr_cluster.centroids))

        fplt.add_text((x[0], mean(sr_cluster.centroids)), text_bot, color='#000000',anchor=(0,0), ax=axes['ax'])
        fplt.add_text((x[0], mean(sr_cluster.centroids)), text_top, color='#000000',anchor=(0,1), ax=axes['ax'])

        fplt.add_line((x[0], mean(sr_cluster.centroids)), (x[-1], mean(sr_cluster.centroids)), style='.', color='#FF0000', width=2, interactive=False)
        #fplt.add_band(min(sr_level), max(sr_level), ax=axes['ax'], color='#FFCCCC')
        fplt.add_rect((x[sr_cluster.validation_index], max(sr_cluster.centroids)), (x[-1], min(sr_cluster.centroids)), ax=axes['ax'], color='#FFCCCC')


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


def market_class_handler(x, y, axes): 
    # Visualization on ax_bot as class rows
    color_set = ['#FF8080', '#80FF80', '#8080FF', '#80FFFF', '#FF80FF', '#FFFF80'] # 6 Color is enough to distinguish classes

    enable_ax_bot(axes, y_range=(0,len(y.keys())))
    fplt.plot(x, y=[len(y.keys())]*len(x), ax=axes['ax_bot'])

    for class_idx, (class_name, class_item_list) in enumerate(y.items()):
        for class_item in class_item_list:
            fplt.add_rect((class_item['start'], class_idx+1), (class_item['end'], class_idx), color=color_set[class_idx%6], interactive=False, ax=axes['ax_bot'])
            if 'validation_point' in class_item:
                fplt.add_line((class_item['validation_point'], class_idx+1), (class_item['validation_point'], class_idx), style='.', color='#000000', width=2, interactive=False, ax=axes['ax_bot'])
        fplt.add_text((x[0], class_idx+0.5), class_name, color='#000000',anchor=(0,0), ax=axes['ax_bot'])

    # Visualization on ax as class rows
    for class_idx, (class_name, class_item_list) in enumerate(y.items()):
        for class_item in class_item_list:
            fplt.add_rect((class_item['start'], class_item['vertical_level1']), (class_item['end'], class_item['vertical_level2']), color=color_set[class_idx%6], interactive=False, ax=axes['ax'])


def disable_ax_bot(axes):
    axes['ax'].set_visible(xaxis=True)
    axes['ax_bot'].hide()

#####################################  Custom Analyzer Visualization #####################################

def market_class_aroonosc(x, y, axes): market_class_handler(x, y, axes)
def market_class_fractal_aroon(x, y, axes): market_class_handler(x, y, axes)

def fractal_line_3(x, y, axes): disable_ax_bot(axes); line_handler(x, y, axes['ax'])
def fractal_aroon(x, y, axes): enable_ax_bot(axes, y_range=(0,100)); line_handler(x, y, axes['ax_bot'])
def fractal_aroonosc(x, y, axes): enable_ax_bot(axes, y_range=(-100,100)); line_handler(x, y, axes['ax_bot'])

def support_birch(x, y, axes): disable_ax_bot(axes); support_handler(x, y, axes)
def resistance_birch(x, y, axes): disable_ax_bot(axes); resistance_handler(x, y, axes)
def support_optics(x, y, axes): disable_ax_bot(axes); support_handler(x, y, axes)
def resistance_optics(x, y, axes): disable_ax_bot(axes); resistance_handler(x, y, axes)
def support_meanshift(x, y, axes): disable_ax_bot(axes); support_handler(x, y, axes)
def resistance_meanshift(x, y, axes): disable_ax_bot(axes); resistance_handler(x, y, axes)
def support_dbscan(x, y, axes): disable_ax_bot(axes); support_handler(x, y, axes)
def resistance_dbscan(x, y, axes): disable_ax_bot(axes); resistance_handler(x, y, axes)
def support_kmeans(x, y, axes): disable_ax_bot(axes); support_handler(x, y, axes)
def resistance_kmeans(x, y, axes): disable_ax_bot(axes); resistance_handler(x, y, axes)


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


####################################  TA-LIB Indicators Visualization ####################################

def ma(x, y, axes): disable_ax_bot(axes); line_handler(x, y, axes['ax'])
def rsi(x, y, axes): enable_ax_bot(axes, y_range=(0,100), band=(30,70)); line_handler(x, {'RSI':y}, axes['ax_bot'])
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



