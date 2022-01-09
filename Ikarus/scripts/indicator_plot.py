import finplot as fplt
from statistics import mean

# Custom analyzers
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

def bullish_fractal_3(x, y, axes): 
    disable_ax_bot(axes)
    fplt.plot(x=x, y=y, kind='scatter', color='#0000ff', width=2, ax=axes['ax'], zoomscale=False, style='d')

def bearish_fractal_3(x, y, axes): 
    disable_ax_bot(axes)
    fplt.plot(x=x, y=y, kind='scatter', color='#ff00ff', width=2, ax=axes['ax'], zoomscale=False, style='d')


# TA-LIB Indicators
def ma(x, y, axes): disable_ax_bot(axes); line_handler(x, y, axes['ax'])
def rsi(x, y, axes): enable_ax_bot(axes); line_handler(x, y, axes['ax_bot'])
def bband(x, y, axes): disable_ax_bot(axes); line_handler(x, y, axes['ax'])
def macd(x, y, axes): 
    # BUG: Choosing rsi first and choosing macd second causes trouble due to fplt.set_y_range
    axes['ax'].set_visible(xaxis=False)
    fplt._ax_reset(axes['ax_bot'])
    axes['ax_bot'].show()
    line_handler(x, {'macd': y['macd'], 'macdsignal':y['macdsignal']}, axes['ax_bot'])
    fplt.bar(x, y['macdhist'], ax=axes['axo_bot'])
    axes['axo_bot'].show()

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
    fplt.plot(x=x, y=y, kind='scatter', color='#0000ff', width=2, ax=axis, zoomscale=False, style='d')

def enable_ax_bot(axes):
    axes['ax'].set_visible(xaxis=False)
    axes['ax_bot'].show()
    fplt.set_y_range(0, 100, ax=axes['ax_bot'])
    fplt.add_band(30, 70, color='#6335', ax=axes['ax_bot'])


def disable_ax_bot(axes):
    axes['ax'].set_visible(xaxis=True)
    axes['ax_bot'].hide()

