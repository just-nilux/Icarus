from objects import EState
from utils import safe_sum, safe_divide, safe_multiply, safe_substract


def distribute(free_trade_slot, free_capital, free_pairs):
    if free_trade_slot == 0:
        return {}

    capital_per_trade = safe_divide(free_capital, free_trade_slot)
    disribution = dict()
    
    for pair in free_pairs:
        if free_trade_slot <= 0:
            break
        free_trade_slot -= 1
        disribution[pair] = capital_per_trade

    return disribution


def evaluate_size(pairs, max_live_trade, strategy_capital, trade_list):

    in_trade_capital = 0
    in_trade_pairs = set()
    for trade in trade_list:
        if trade.status == EState.CLOSED:
            continue
        in_trade_pairs.add(trade.pair)
        in_trade_capital = safe_sum(in_trade_capital, trade.enter.amount)
    
    free_capital = safe_substract(strategy_capital, in_trade_capital)
    if free_capital <= 0:
        return {}
    
    free_pairs = set(pairs) - in_trade_pairs
    free_trade_slot = max_live_trade-len(in_trade_pairs)
    
    return distribute(free_trade_slot, free_capital, free_pairs)


def evaluate_stop_loss(strategy_capital, max_loss_coeff, trade, fee_rate=None):
    '''
    Total capital: 1000
    capital_at_risk = 1000*0.02 = 20

    Amount Price Quantity
    100    20    5
    98     20    4.9
    100-20=80

    stop_loss price calculation with fee_rate:
        4.9 * price = 80 + 4.9 * price * fee_rate
        4.9 * price * (1-fee_rate) = 80
        4.9 * price * 0.98 = 80
        price = 16.65
        81.5   16.65 4.9

    stop_loss price calculation without fee_rate:

        100-20=80
        4.9 * price = 80
        4.9 * price = 80
        price = 16.65
        81.5   16.65 4.9
    '''
    max_loss = safe_multiply(strategy_capital, max_loss_coeff)
    min_amount = safe_substract(trade.enter.amount, max_loss)
    
    if fee_rate == None:
        stop_loss_price = safe_divide(min_amount, trade.enter.quantity)
    else:
        denominator = safe_multiply(trade.result.enter.quantity, safe_substract(1, fee_rate))
        stop_loss_price = safe_divide(min_amount, denominator)

    return stop_loss_price
