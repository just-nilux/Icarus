from ..exceptions import NotImplementedException
from binance.enums import *
import asyncio
import pandas as pd
import logging
import json
import bson
import sys
from ..utils import time_scale_to_second, get_min_scale, \
    safe_multiply, safe_divide, round_to_period
import more_itertools
from .. import binance_filters
from ..objects import Trade, OCO, ECause, ECommand, EState, Limit, Market, TradeResult, Result, trade_to_dict
from ..utils import setup_logger
from dataclasses import asdict
from binance import AsyncClient
from ..strategies.StrategyBase import StrategyBase
from ..brokers.binance_wrapper import BinanceWrapper
import argparse

async def run_command(args):

    f = open(args.config,'r')
    config = json.load(f)
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    client = await AsyncClient.create(**cred_info['Binance']['Test'])
    broker_client = BinanceWrapper(client, config, None)

    if hasattr(broker_client, args.command):
        result = await getattr(broker_client, args.command)(args.args)
    print(result)
    
    await broker_client.close_connection()


if __name__ == '__main__':
    # python -m src.Ikarus.scripts.binance_wrapper_cli '--config' 'C:\Users\bilko\PycharmProjects\trade-bot/configs/live-test/config.json' '--command' 'get_all_orders' '--args' 'BTCUSDT'
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--config', help='config file')
    parser.add_argument('--command', help='binance api call')
    parser.add_argument('--args', required=False, help='args for the api call')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_command(args))

    
