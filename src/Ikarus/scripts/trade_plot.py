import finplot as fplt
from ..objects import OCO, ECause, Limit, Market

def plot_market_frame():
    pass


def plot_limit_frame(trade):
    rect_bot=trade.result.enter.price
    rect_top=trade.result.exit.price
    color = '#60FF60'
    if trade.result.exit.price < trade.result.enter.price:
        rect_bot, rect_top = rect_top, rect_bot
        color = '#FF9090'
    fplt.add_rect((trade.decision_time, rect_top), (trade.result.exit.time, rect_bot), color=color, interactive=False)


def plot_oco_frame():
    pass


def write_descriptions(trade_list) -> None:

    for trade in trade_list:
        
        if trade.result.exit.price < trade.result.enter.price:
            rect_top = trade.result.enter.price
        else:
            rect_top = trade.result.exit.price

        profit_perc = trade.result.profit / trade.result.enter.amount
        fplt.add_text((trade.result.exit.time, rect_top), "%{:.2f}".format(profit_perc), color='#000000', anchor=(1,0))
        fplt.add_text((trade.decision_time, trade.result.enter.price), "{}".format(trade.strategy), color='#000000')
        


def plot_exit_orders(trade_list) -> None:
    for trade in trade_list:
        if type(trade.exit) == Market:
            plot_market_frame()
        elif type(trade.exit) == Limit:
            plot_limit_frame(trade)
        elif type(trade.exit) == OCO:
            plot_oco_frame()


def plot_enter_orders(trade_list) -> None:
    for trade in trade_list:
        if trade.cause = ECause.Enter

        fplt.add_line((trade.decision_time, trade.result.enter.price),
            (trade.result.exit.time, trade.result.enter.price),
            color='#0000FF', width=3, interactive=False)


def scatter_buy_points(ax, trade_list) -> None:
    enter_time_list = [trade.result.enter.time for trade in trade_list]
    enter_price_list = [trade.result.enter.price for trade in trade_list]
    plot_spec = {'color':'#00ff00','style':'^', 'ax':ax, 'legend':'Buy Point'}
    fplt.plot(x=enter_time_list, y=enter_price_list, kind='scatter', color=plot_spec['color'], width=2, ax=plot_spec['ax'], zoomscale=False, style=plot_spec['style'])
    #for x,y in zip(decision_time_list,enter_price_list):
    #    fplt.plot(x=x, y=y, kind='scatter', color=plot_spec['color'], width=2, ax=plot_spec['ax'], zoomscale=False, style=plot_spec['style'])


def scatter_sell_points(ax, trade_list) -> None:
    exit_time_list = [trade.result.exit.time for trade in trade_list]
    exit_price_list = [trade.result.exit.price for trade in trade_list]
    plot_spec = {'color':'#ff0000','style':'v', 'ax':ax, 'legend':'Sell Point'}
    fplt.plot(x=exit_time_list, y=exit_price_list, kind='scatter', color=plot_spec['color'], width=2, ax=plot_spec['ax'], zoomscale=False, style=plot_spec['style'])
    #for x,y in zip(decision_time_list,enter_price_list):
    #    fplt.plot(x=x, y=y, kind='scatter', color=plot_spec['color'], width=2, ax=plot_spec['ax'], zoomscale=False, style=plot_spec['style'])


def scatter_decision_points(ax, trade_list) -> None:
    decision_time_list = [trade.decision_time for trade in trade_list]
    enter_price_list = [trade.result.enter.price for trade in trade_list]
    plot_spec = {'color':'#0000ff','style':'t2', 'ax':ax, 'legend':'Decision Point'}
    fplt.plot(x=decision_time_list, y=enter_price_list, kind='scatter', color=plot_spec['color'], width=2, ax=plot_spec['ax'], zoomscale=False, style=plot_spec['style'])
    #for x,y in zip(decision_time_list,enter_price_list):
    #    fplt.plot(x=x, y=y, kind='scatter', color=plot_spec['color'], width=2, ax=plot_spec['ax'], zoomscale=False, style=plot_spec['style'])


def plot_buy_sell_points(ax, trade_list) -> None:
    scatter_decision_points(ax, trade_list)
    scatter_buy_points(ax, trade_list)
    scatter_sell_points(ax, trade_list)

