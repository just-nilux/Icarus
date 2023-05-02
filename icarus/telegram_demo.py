from connectivity.telegram_wrapper import TelegramBot, TelegramMessageFormat, unknown_command, unknown_text
import telegram_interface
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import filters

import json
import sys
import time
from objects import Trade, Limit, EState, ECommand, ECause, TradeResult, trade_to_dict, trade_from_dict
from dataclasses import asdict
import pandas as pd
import asyncio

sample_trade = {
    "_id" : "8ab65baf-3d90-4117-a4a5-5958e50dc181",
    "decision_time" : 1682812800,
    "strategy" : "FixedLimitTargetAdaptive_24_24_03",
    "pair" : "XRPUSDT",
    "status" : "closed",
    "enter" : {
        "price" : 0.478,
        "amount" : 74.568,
        "quantity" : 156.0,
        "orderId" : 5158447835
    },
    "exit" : {
        "price" : 0.4633,
        "amount" : 71.8115,
        "quantity" : 155.0,
        "orderId" : 5159603156
    },
    "result" : {
        "cause" : "market",
        "enter" : {
            "price" : 0.478,
            "amount" : 74.493432,
            "quantity" : 155.844,
            "orderId" : 5158447835,
            "type" : "market",
            "time" : 1682812800,
            "fee" : 0.156
        },
        "exit" : {
            "price" : 0.4627,
            "amount" : 71.6467815,
            "quantity" : 155.0,
            "orderId" : 5159603156,
            "type" : "market",
            "time" : 1682906400,
            "fee" : 0.0717185
        },
        "profit" : -2.9212185,
        "live_time" : 93600
    },
    "command" : "None",
    "order_stash" : [ 
        {
            "price" : 0.4923,
            "amount" : 76.3065,
            "quantity" : 155.0,
            "orderId" : 5158484419,
            "expire" : 1682902800
        }
    ]
}

async def send_formatted_messages():
    trade = trade_from_dict(sample_trade)
    TelegramBot.send_formatted_message('order_filled', asdict(trade.result.enter), ['BUY', trade.strategy, trade.pair], [trade._id])
    time.sleep(0.1)
    TelegramBot.send_formatted_message('order_executed', asdict(trade.exit),['SELL',trade.strategy, trade.pair], [trade._id])
    time.sleep(0.1)
    TelegramBot.send_formatted_message('trade_closed', asdict(trade.result), [trade.strategy, trade.pair], [trade._id])


async def db_demo():
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)

    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    telegram_interface.init_telegram_bot(cred_info['ConnectivityBot']['token'], cred_info['ConnectivityBot']['chat_id'])
    telegram_interface.enable_db_interface(config['mongodb'])
    telegram_interface.enable_binance_interface((cred_info['Binance']['Test']))
    telegram_interface.start_telegram_bot()

    await send_formatted_messages()

    counter = 0
    while(True):
        print("in loop", str(counter))
        time.sleep(1)

if __name__ == '__main__':

    loop = asyncio.get_event_loop()
    loop.run_until_complete(db_demo())
