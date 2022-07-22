import finplot as fplt
from ..objects import OCO, ECause, Limit, Market


def plot_rectangle_frame(h1,h2,v1,v2):
    fplt.add_line((v1, h1), (v2, h1),
        color='#000000', width=3, interactive=False)
    fplt.add_line((v1, h2), (v2, h2),
        color='#000000', width=3, interactive=False)
    fplt.add_line((v1, h2), (v1, h1),
        color='#000000', width=3, interactive=False)
    fplt.add_line((v2, h2), (v2, h1),
        color='#000000', width=3, interactive=False)


def colorize_exit_order(trade):

    if trade.result.exit.price < trade.result.enter.price:
        rect_bot=trade.result.exit.price
        rect_top=trade.result.enter.price
        color = '#FF9090'
    else:
        rect_bot=trade.result.enter.price
        rect_top=trade.result.exit.price
        color = '#60FF60'


    if trade.order_stash:
        # If there is stashed orders then use the "expire" of last stashed order
        fplt.add_rect((trade.order_stash[-1].expire, rect_top), (trade.result.exit.time, rect_bot), color=color, interactive=False)
    else:
        # Else use the time that only exit order placed
        fplt.add_rect((trade.result.enter.time, rect_top), (trade.result.exit.time, rect_bot), color=color, interactive=False)
    pass


def plot_exit_order_frames(trade):

    # TODO: The logic can be improved a bit more
    if not trade.order_stash:
        if type(trade.exit) == Market:
            fplt.add_line((trade.result.enter.time, trade.result.enter.price), 
                (trade.result.exit.time, trade.result.enter.price), color='#000000', width=3, interactive=False)                                    # Horizontal bar
            fplt.add_line((trade.result.exit.time, trade.result.enter.price), 
                (trade.result.exit.time, trade.result.exit.price), color='#000000', width=3, interactive=False)                                     # Vertical bar

        elif type(trade.exit) == Limit:
            plot_rectangle_frame(trade.result.enter.price, trade.exit.price, trade.result.enter.time, trade.result.exit.time)                             # Single rectangle

        elif type(trade.exit) == OCO:
            plot_rectangle_frame(trade.result.enter.price, trade.exit.price, trade.result.enter.time, trade.result.exit.time)                             # Above rectangle
            plot_rectangle_frame(trade.result.enter.price, trade.exit.stop_limit_price, trade.result.enter.time, trade.result.exit.time)                  # Below rectangle

        return

    exit_orders = trade.order_stash
    exit_orders.append(trade.exit)

    left_vertical_bar = trade.result.enter.time
    for i in range(len(exit_orders)):
        if i == len(exit_orders)-1:
            right_vertical_bar = trade.result.exit.time
        else:
            right_vertical_bar = trade.order_stash[0].expire

        # Plot the frames and bars for the order
        if type(exit_orders[i]) == Market:
            fplt.add_line((left_vertical_bar, trade.result.enter.price), 
                (right_vertical_bar, trade.result.enter.price), color='#000000', width=3, interactive=False)                                    # Horizontal bar
            fplt.add_line((right_vertical_bar, trade.result.enter.price), 
                (right_vertical_bar, trade.order_stash[i].price), color='#000000', width=3, interactive=False)                                  # Vertical bar

        elif type(exit_orders[i]) == Limit:
            plot_rectangle_frame(trade.result.enter.price, trade.order_stash[i].price, left_vertical_bar, right_vertical_bar)                   # Single rectangle

        elif type(exit_orders[i]) == OCO:
            plot_rectangle_frame(trade.result.enter.price, trade.order_stash[i].price, left_vertical_bar, right_vertical_bar)                   # Above rectangle
            plot_rectangle_frame(trade.result.enter.price, trade.order_stash[i].stop_limit_price, left_vertical_bar, right_vertical_bar)        # Below rectangle

        if i != len(exit_orders)-1:
            left_vertical_bar = trade.order_stash[i].expire
        pass


def write_profits(trade_list):
    for trade in trade_list:
        if trade.result.exit.price < trade.result.enter.price:
            rect_top = trade.result.enter.price
        else:
            rect_top = trade.result.exit.price

        profit_perc = trade.result.profit / trade.result.enter.amount
        fplt.add_text((trade.result.exit.time, rect_top), "%{:.2f}".format(profit_perc), color='#000000', anchor=(1,0))


def write_strategy_names(trade_list):
    for trade in trade_list:
        fplt.add_text((trade.decision_time, trade.enter.price), "{}".format(trade.strategy), color='#000000')


def write_descriptions(trade_list) -> None:
    write_profits(trade_list)
    write_strategy_names(trade_list)        


def plot_exit_orders(trade_list) -> None:
    for trade in trade_list:
        colorize_exit_order(trade)
        plot_exit_order_frames(trade)

def plot_enter_orders(trade_list) -> None:
    for trade in trade_list:
        if trade.result.cause == ECause.ENTER_EXP:
            fplt.add_line((trade.decision_time, trade.enter.price),
                (trade.enter.expire, trade.enter.price),
                color='#9900ff', interactive=False)
        elif trade.result.cause == ECause.CLOSED:
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

