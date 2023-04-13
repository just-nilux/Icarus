
from utils import safe_multiply, round_step_downward
import logging

logger = logging.getLogger('app')
def min_notional(price, quantity, symbol_info):
    min_notional_filter = None
    for filter in symbol_info['filters']:
        if filter['filterType'] in ['MIN_NOTIONAL', 'NOTIONAL']:
            min_notional_filter = filter
            break

    if min_notional_filter == None:
        logger.debug(str(symbol_info))
        raise Exception('No MIN_NOTIONAL filter on symbol info for the symbol: {}'.format(symbol_info['symbol_info']))
    return (safe_multiply(price, quantity) > float(min_notional_filter['minNotional']))  # if valid: True, else: False

def lot_size(quantity, symbol_info):
    lot_size_filter = None
    for filter in symbol_info['filters']:
        if filter['filterType'] in ['LOT_SIZE']:
            lot_size_filter = filter
            break

    if lot_size_filter == None:
        logger.debug(str(symbol_info))
        raise Exception('No LOT_SIZE filter on symbol info for the symbol: {}'.format(symbol_info['symbol_info']))

    quantity = round_step_downward(quantity, float(lot_size_filter['stepSize']))
    if float(lot_size_filter['minQty']) < quantity < float(lot_size_filter['maxQty']):
        return quantity
    else:
        return None

# TODO: Percent price filter
# https://dev.binance.vision/t/what-does-the-percent-price-filter-mean/134