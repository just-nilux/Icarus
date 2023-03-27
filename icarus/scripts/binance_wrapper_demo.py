from exceptions import NotImplementedException
from binance.enums import *
import asyncio
import pandas as pd
import logging
import json
import bson
import sys
from utils import time_scale_to_second, get_min_scale, \
    safe_multiply, safe_divide, round_to_period
import more_itertools
import binance_filters
from objects import Trade, OCO, ECause, ECommand, EState, Limit, Market, TradeResult, Result, trade_to_dict
from utils import setup_logger
from dataclasses import asdict
from binance import AsyncClient
from strategies.StrategyBase import StrategyBase
from brokers.binance_wrapper import BinanceWrapper

async def demo():
    if __name__ != '__main__':
        raise Exception('This function is only implemented for test purposes')

    client = await AsyncClient.create(**cred_info['Binance']['Test'])
    broker_client = BinanceWrapper(client, config, None)

    symbol_info = await broker_client.get_all_symbol_info(['BTCUSDT'])
    await test_limit_buy_instant_fill(broker_client, symbol_info)
    await test_limit_sell_instant_fill(broker_client, symbol_info)

    # NOTE: It is not possible to do instant fill for oco orders because of:
    # APIError(code=-2010): The relationship of the prices for the orders is not correct.
    #
    # Price Restrictions:
    # SELL: Limit Price > Last Price > Stop Price
    # BUY: Limit Price < Last Price < Stop Price

    orders = await client.get_open_orders(symbol='BTCUSDT')
    logger.debug(f'client.get_open_orders: \n{orders}')

    orders = await client.get_all_orders(symbol='BTCUSDT')
    logger.debug(f'client.get_all_orders: \n{orders}')

    try:
        #fees = await client.get_trade_fee()
        fees = await client.get_trade_fee(symbol='BNBBTC')
        logger.debug(f'client.get_trade_fee: \n{fees}')

        log = await client.get_dust_log()
        logger.debug(f'client.get_dust_log: \n{log}')

    except Exception as e:
        logger.debug(f'client.get_trade_fee: \n{e}')

    df = await broker_client.get_current_balance()
    logger.info(f'balance: \n{df.to_string()}')
    trade = await test_market_buy(broker_client)

    df = await broker_client.get_current_balance()
    logger.debug(f'balance: \n{df.to_string()}')
    trade = await test_market_sell(broker_client)

    df = await broker_client.get_current_balance()
    logger.debug(f'balance: \n{df.to_string()}')
    trade = await test_limit_buy(broker_client)
    df = await broker_client.get_current_balance()
    logger.debug(f'balance: \n{df.to_string()}')
    trade = await test_order_cancel(broker_client, trade)

    df = await broker_client.get_current_balance()
    logger.debug(f'balance: \n{df.to_string()}')
    trade = await test_limit_sell(broker_client)
    df = await broker_client.get_current_balance()
    logger.debug(f'balance: \n{df.to_string()}')
    trade = await test_order_cancel(broker_client, trade)

    df = await broker_client.get_current_balance()
    logger.debug(f'balance: \n{df.to_string()}')
    trade = await test_oco_sell(broker_client)
    df = await broker_client.get_current_balance()
    logger.debug(f'balance: \n{df.to_string()}')
    trade = await test_order_cancel(broker_client, trade)

    # TODO: Instant fill oco order test

    pass


async def test_market_buy(broker_client: BinanceWrapper):
    strategy_name = list(broker_client.config['strategy'].keys())[0]
    trade = Trade(1557705600000, strategy_name, 'BTCUSDT', EState.WAITING_ENTER, 
        enter=Market(amount=100, price=20000))
    trade.result = TradeResult()
    exec_status = await broker_client._execute_market_buy(trade)
    assert exec_status == True

    orders = await broker_client.get_trade_orders([trade])
    if len(orders):
        logger.debug('order:\n'+json.dumps(list(orders.values())[0], indent=4))
    
    return trade


async def test_market_sell(broker_client: BinanceWrapper):
    strategy_name = list(broker_client.config['strategy'].keys())[0]
    trade = Trade(1557705600000, strategy_name, 'BTCUSDT', EState.WAITING_EXIT, 
        exit=Market(amount=100, price=20000))
    result_enter = Result(price=30000, amount=100, fee=0)
    trade.result = TradeResult(enter=result_enter)
    exec_status = await broker_client._execute_market_sell(trade)
    assert exec_status == True

    orders = await broker_client.get_trade_orders([trade])
    if len(orders):
        logger.debug('order:\n'+json.dumps(list(orders.values())[0], indent=4))
    
    return trade



async def test_limit_buy(broker_client: BinanceWrapper):
    strategy_name = list(broker_client.config['strategy'].keys())[0]
    trade = Trade(1557705600000, strategy_name, 'BTCUSDT', EState.WAITING_ENTER, 
        enter=Limit(amount=100, price=10000))
    trade.result = TradeResult()
    exec_status = await broker_client._execute_limit_buy(trade)
    assert exec_status == True

    orders = await broker_client.get_trade_orders([trade])
    if len(orders):
        logger.debug('order:\n'+json.dumps(list(orders.values())[0], indent=4))
    
    return trade


async def test_limit_sell(broker_client: BinanceWrapper):
    strategy_name = list(broker_client.config['strategy'].keys())[0]
    trade = Trade(1557705600000, strategy_name, 'BTCUSDT', EState.WAITING_EXIT, 
        exit=Limit(quantity=0.01, price=30000))
    result_enter = Result(price=10000, amount=100, fee=0)
    trade.result = TradeResult(enter=result_enter)
    exec_status = await broker_client._execute_limit_sell(trade)
    assert exec_status == True

    orders = await broker_client.get_trade_orders([trade])
    if len(orders):
        logger.debug('order:\n'+json.dumps(list(orders.values())[0], indent=4))
    
    return trade


async def test_oco_sell(broker_client: BinanceWrapper):
    strategy_name = list(broker_client.config['strategy'].keys())[0]

    exit_order = OCO(
        price=30000,
        quantity=0.005,
        stop_price=15001,
        stop_limit_price=15000
    )

    trade = Trade(1557705600000, strategy_name, 'BTCUSDT', EState.WAITING_EXIT, 
        exit=exit_order)
    result_enter = Result(price=10000, amount=100, fee=0)
    trade.result = TradeResult(enter=result_enter)
    exec_status = await broker_client._execute_oco_sell(trade)
    assert exec_status == True

    orders = await broker_client.get_trade_orders([trade])
    if not len(orders):
        return trade

    for order in orders.values():
        logger.debug('order:\n'+json.dumps(order, indent=4))
    
    return trade


async def test_order_cancel(broker_client: BinanceWrapper, trade: Trade):
    
    exec_status = await broker_client._execute_cancel(trade)
    assert exec_status == True
    return trade


async def test_limit_buy_instant_fill(broker_client: BinanceWrapper, symbol_info: dict):
    pair = 'BTCUSDT'
    # 1. Get current price
    prices = await broker_client.get_all_tickers()
    current_price = float(prices.loc[pair,'price'])
    logger.debug(f'current_price for pair {pair}: {current_price}')

    # 2. Put limit order that is higher than current price
    target_buy_price = safe_multiply(current_price, 1.102)
    strategy_name = list(broker_client.config['strategy'].keys())[0]
    trade = Trade(1557705600000, strategy_name, pair, EState.WAITING_ENTER, 
        enter=Limit(amount=100, price=target_buy_price))
    trade.result = TradeResult()
    
    StrategyBase.apply_exchange_filters(trade.enter, symbol_info[pair])

    exec_status = await broker_client._execute_limit_buy(trade)
    assert exec_status == True

    orders = await broker_client.get_trade_orders([trade])
    if len(orders):
        logger.debug('order:\n'+json.dumps(list(orders.values())[0], indent=4))
    
    return trade


async def test_limit_sell_instant_fill(broker_client: BinanceWrapper, symbol_info: dict):
    pair = 'BTCUSDT'
    # 1. Get current price
    prices = await broker_client.get_all_tickers()
    current_price = float(prices.loc[pair,'price'])
    logger.debug(f'current_price for pair {pair}: {current_price}')

    # 2. Put limit order that is higher than current price
    target_sell_price = safe_multiply(current_price, 0.998)
    strategy_name = list(broker_client.config['strategy'].keys())[0]
    trade = Trade(1557705600000, strategy_name, pair, EState.WAITING_EXIT, 
        exit=Limit(quantity=0.01, price=target_sell_price))
    result_enter = Result(price=10000, amount=100, fee=0)
    trade.result = TradeResult(enter=result_enter)

    StrategyBase.apply_exchange_filters(trade.exit, symbol_info[pair])

    exec_status = await broker_client._execute_limit_sell(trade)
    assert exec_status == True

    orders = await broker_client.get_trade_orders([trade])
    if len(orders):
        logger.debug('order:\n'+json.dumps(list(orders.values())[0], indent=4))
    
    return trade


async def test_oco_sell_instant_fill_limit_maker(broker_client: BinanceWrapper, symbol_info: dict):
    pair = 'BTCUSDT'
    # 1. Get current price
    prices = await broker_client.get_all_tickers()
    current_price = float(prices.loc[pair,'price'])
    logger.debug(f'current_price for pair {pair}: {current_price}')

    # 2. Put limit order that is higher than current price
    target_limit_maker_price = safe_multiply(current_price, 0.998)
    target_stop_price = safe_multiply(current_price, 0.995)
    target_stop_limit_price = safe_multiply(current_price, 0.994)

    strategy_name = list(broker_client.config['strategy'].keys())[0]

    exit_order = OCO(
        price=target_limit_maker_price,
        quantity=0.005,
        stop_price=target_stop_price,
        stop_limit_price=target_stop_limit_price
    )

    trade = Trade(1557705600000, strategy_name, pair, EState.WAITING_EXIT, 
        exit=exit_order)
    result_enter = Result(price=10000, amount=100, fee=0)
    trade.result = TradeResult(enter=result_enter)

    StrategyBase.apply_exchange_filters(trade.exit, symbol_info[pair])

    exec_status = await broker_client._execute_oco_sell(trade)
    assert exec_status == True

    orders = await broker_client.get_trade_orders([trade])
    if not len(orders):
        return trade

    for order in orders.values():
        logger.debug('order:\n'+json.dumps(order, indent=4))
    
    return trade


if __name__ == '__main__':

    f = open(str(sys.argv[1]),'r')
    config = json.load(f)

    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    logger = logging.getLogger('app')
    setup_logger(logger, config['log'])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(demo())
