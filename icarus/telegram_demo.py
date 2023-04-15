from connectivity.telegram_wrapper import TelegramBot, TelegramMessageFormat, unknown_command, unknown_text
import telegram_interface
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import filters

import json
import sys
import time
from objects import Trade, Limit, EState, ECommand, ECause, TradeResult, trade_to_dict
from dataclasses import asdict
import pandas as pd
import asyncio

def send_trade():
    # Send a whole trade
    format = TelegramMessageFormat('trade:','\n','\n        ','{}: {}')
    TelegramBot.add_format('trade', format)
    trade_sample = Trade(1557705600000, 'ObjectStrategy', 'XRPUSDT', EState.OPEN_ENTER, 
        Limit(0.2906, 4749.5664, 16344.0, 1652629743339, 1559001600000),
        Limit(0.3372, 5511.5102, 16344.9296, None, 1559001600000),
        None, ECommand.NONE, [], _id="ObjectId('628120f012791ee7ba')")
    TelegramBot.send_formatted_message('trade',trade_to_dict(trade_sample))


def send_trade_order():
    format = TelegramMessageFormat('trade_order:','\n','\n        ','{}: {}')
    TelegramBot.add_format('trade_order', format)
    enter_order = {
        "price": 93.67,
        "amount": 50.0047928,
        "quantity": 0.53384,
        "orderId": 3107228,
        "type": "market",
        "time": 1677627900000,
        "price": {"xy":12},
    }
    TelegramBot.send_formatted_message('trade_order',enter_order)


def send_trade_result():
    format = TelegramMessageFormat('trade_result:','\n','\n        ','{}: {}')
    TelegramBot.add_format('trade_result', format)

    fee_rate = 0.001 
    trade = Trade(123, "StrategyName", "XRPUSDT")
    trade.set_enter(Limit(price=5,amount=100,quantity=20))
    trade.result = TradeResult()
    trade.set_result_enter(123456, fee_rate=fee_rate)
    trade.set_result_exit(123456,
        cause=ECause.STOP_LIMIT,
        price=6,
        quantity=trade.result.enter.quantity,
        fee_rate=fee_rate,
        orderId=9876)
    TelegramBot.send_formatted_message('trade_result', asdict(trade.result))

def send_balance():
    format = TelegramMessageFormat('balance:','\n','\n        ','{}')
    TelegramBot.add_format('balance', format)

    balance_raw = [ 
        {
            "asset" : "BNB",
            "free" : 1000.0,
            "locked" : 0.0,
            "total" : 1000.0
        }, 
        {
            "asset" : "BTC",
            "free" : 1.235676,
            "locked" : 0.0,
            "total" : 1.235676
        }, 
        {
            "asset" : "BUSD",
            "free" : 9891.21795,
            "locked" : 0.0,
            "total" : 9891.21795
        }, 
        {
            "asset" : "ETH",
            "free" : 100.33015,
            "locked" : 0.0,
            "total" : 100.33015
        }, 
        {
            "asset" : "LTC",
            "free" : 501.06411,
            "locked" : 0.53441,
            "total" : 501.59852
        }, 
        {
            "asset" : "TRX",
            "free" : 500000.0,
            "locked" : 0.0,
            "total" : 500000.0
        }, 
        {
            "asset" : "USDT",
            "free" : 4594.86836402,
            "locked" : 0.0,
            "total" : 4594.86836402
        }, 
        {
            "asset" : "XRP",
            "free" : 50000.0,
            "locked" : 133.3,
            "total" : 50133.3
        }
    ]
    df = pd.DataFrame(balance_raw)
    TelegramBot.send_formatted_message('balance', [df.to_string(index=False)])


async def db_demo():
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)

    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    telegram_interface.init_telegram_bot(cred_info['ConnectivityBot']['token'], cred_info['ConnectivityBot']['chat_id'])
    telegram_interface.enable_db_interface(config['mongodb'])
    telegram_interface.enable_binance_interface((cred_info['Binance']['Test']))
    telegram_interface.start_telegram_bot()

    counter = 0
    while(True):
        print("in loop", str(counter))
        time.sleep(1)

if __name__ == '__main__':

    loop = asyncio.get_event_loop()
    loop.run_until_complete(db_demo())
