from Ikarus.enums import *
# TODO: Test Canceled cases or remove the statment
async def fill_open_enter(lto_list, orders):

    for lto in lto_list:
        if lto['status'] == 'open_enter': 
            orders[lto['enter'][TYPE_LIMIT]['orderId']]['status'] = 'FILLED'
            orders[lto['enter'][TYPE_LIMIT]['orderId']]['executedQty'] = str(lto['enter'][TYPE_LIMIT]['quantity'])

    return orders

async def fill_open_exit_limit(lto_list, orders):

    for lto in lto_list:
        if lto['status'] == 'open_exit' and TYPE_LIMIT in list(lto['exit'].keys()): 
            orders[lto['exit'][TYPE_LIMIT]['orderId']]['status'] = 'FILLED'
            orders[lto['exit'][TYPE_LIMIT]['orderId']]['executedQty'] = str(lto['exit'][TYPE_LIMIT]['quantity'])

    return orders

async def stoploss_taken_oco(lto_list, orders):

    for lto in lto_list:
        if lto['status'] == 'open_exit' and TYPE_OCO in list(lto['exit'].keys()): 
            stopLimit_orderId = lto['exit'][TYPE_OCO]['stopLimit_orderId']
            orders[lto['exit'][TYPE_OCO]['orderId']]['status'] = 'EXPIRED'
            orders[stopLimit_orderId]['status'] = 'FILLED'
            orders[stopLimit_orderId]['executedQty'] = str(lto['exit'][TYPE_OCO]['quantity'])
            # NOTE: No need to update the limit_maker to expired

    return orders

async def limit_maker_taken_oco(lto_list, orders):

    for lto in lto_list:
        if lto['status'] == 'open_exit' and TYPE_OCO in list(lto['exit'].keys()): 
            orders[lto['exit'][TYPE_OCO]['orderId']]['status'] = 'FILLED'
            orders[lto['exit'][TYPE_OCO]['orderId']]['executedQty'] = str(lto['exit'][TYPE_OCO]['quantity'])
            # NOTE: No need to update the stop_limit to expired

    return orders