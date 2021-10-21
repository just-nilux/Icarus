import finplot as fplt

def ma(x, y, ax, axo, ax_rsi): disable_ax_bot(ax, ax_rsi); line_handler(x, y, ax)
def rsi(x, y, ax, axo, ax_rsi): enable_ax_bot(ax, ax_rsi); line_handler(x, y, ax_rsi)
def bband(x, y, ax, axo, ax_rsi): disable_ax_bot(ax, ax_rsi); line_handler(x, y, ax)


def line_handler(x, y, ax):
    # TODO: Improve the plot configuration, such as legend texts and the colors
    if type(y) == dict:
        for param, data in y.items():
            fplt.plot(x, data, width=3, ax=ax, legend=str(param))

    elif type(y) == list:
        fplt.plot(x, y, width=3, ax=ax)


def enable_ax_bot(ax_top, ax_bot):
    ax_top.set_visible(xaxis=False)
    ax_bot.show()
    fplt.set_y_range(0, 100, ax=ax_bot)
    fplt.add_band(30, 70, color='#6335', ax=ax_bot)


def disable_ax_bot(ax_top, ax_bot):
    ax_top.set_visible(xaxis=True)
    ax_bot.hide()

