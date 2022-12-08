
from .utils import safe_multiply, round_step_downward

def min_notional(price, quantity, symbol_info):
    if symbol_info['filters'][2]['filterType'] == 'MIN_NOTIONAL':
        filter = symbol_info['filters'][2]
    else:
        raise Exception('No LOT_SIZE filter on symbol info')
    return (safe_multiply(price, quantity) > float(filter['minNotional']))  # if valid: True, else: False

def lot_size(quantity, symbol_info): 
    if symbol_info['filters'][1]['filterType'] == 'LOT_SIZE':
        filter = symbol_info['filters'][1]
    else:
        raise Exception('No LOT_SIZE filter on symbol info')

    quantity = round_step_downward(quantity, float(filter['stepSize']))
    if float(filter['minQty']) < quantity < float(filter['maxQty']):
        return quantity
    else:
        return None

# TODO: Percent price filter
# https://dev.binance.vision/t/what-does-the-percent-price-filter-mean/134