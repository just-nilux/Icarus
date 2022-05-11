
from .utils import safe_multiply, round_step_downward

def min_notional(price, quantity, symbol_info): 
    return (safe_multiply(price, quantity) > float(symbol_info['filters'][3]['minNotional']))  # if valid: True, else: False

def lot_size(quantity, symbol_info): 
    quantity = round_step_downward(quantity, float(symbol_info['filters'][2]['stepSize']))
    if float(symbol_info['filters'][2]['minQty']) < quantity < float(symbol_info['filters'][2]['maxQty']):
        return quantity
    else:
        return None