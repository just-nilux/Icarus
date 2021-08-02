import asyncio
from binance import AsyncClient
from datetime import datetime
import json
from Ikarus import binance_wrapper, live_strategies, notifications, analyzers, observers, mongo_utils
from Ikarus.enums import *
import logging
from logging.handlers import TimedRotatingFileHandler
import pandas as pd
import sys
import copy
import bson
import time

# Global Variables
SYSTEM_STATUS = 0
STATUS_TIMEOUT = 0

async def change_order_to_filled(lto, orders):

    '''
    {
        "symbol": "BTCUSDT",
        "orderId": 6953206668,
        "orderListId": -1,
        "clientOrderId": "ICPxru6UnQNL3EVAeMjoGi",
        "transactTime": 1627394453186,
        "price": "19245.54000000",
        "origQty": "0.00519600",
        "executedQty": "0.00000000",
        "cummulativeQuoteQty": "0.00000000",
        "status": "NEW",
        "timeInForce": "GTC",
        "type": "LIMIT",
        "side": "BUY",
        "fills": []
    }
    '''
    orders[lto['enter'][TYPE_LIMIT]['orderId']]['status'] = 'FILLED'
    orders[lto['enter'][TYPE_LIMIT]['orderId']]['executedQty'] = str(lto['enter'][TYPE_LIMIT]['quantity'])

    return orders
