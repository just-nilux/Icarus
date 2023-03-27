from connectivity.telegram_wrapper import TelegramBot, TelegramMessageFormat, unknown_command, unknown_text
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler
from telegram.ext import filters

import json
import sys
import time
from objects import Trade, Limit, EState, ECommand, ECause, TradeResult, trade_to_dict
from dataclasses import asdict
import pandas as pd

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


if __name__ == '__main__':

    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    TelegramBot.setToken(config['Telegram']['token'])
    TelegramBot.setChatId(config['Telegram']['chat_id'])
    TelegramBot.add_handler(CommandHandler('kill', TelegramBot.kill), description="Killing the bot...")
    TelegramBot.add_handler(CommandHandler('help', TelegramBot.help), description="Print help message")
    TelegramBot.add_handler(CommandHandler('ping', TelegramBot.pong), description="Ping the bot")
    TelegramBot.add_handler(MessageHandler(filters.TEXT, unknown_command))
    #TelegramBot.add_handler(MessageHandler(Filters.text(['hello','hi','hey']), unknown_text))

    # Send a raw message
    TelegramBot.send_raw_message("This is a raw message")
    time.sleep(1)
    #send_trade()
    send_trade_order()
    time.sleep(1)
    send_trade_result()
    time.sleep(1)
    send_balance()

    # Send a help message
    format = TelegramMessageFormat('Help Message header','\nHelp Message tailer','\n        ','/{}: {}')
    TelegramBot.add_format('help', format, constant_data=TelegramBot.command_desc)
    TelegramBot.send_formatted_message('help')





    #commandss = [cmd_handler.command[0] for cmd_handler in TelegramBot.updater.dispatcher.handlers[0] if type(cmd_handler) == CommandHandler]
    TelegramBot.updater.start_polling()

    counter = 0
    while(True):
        print("in loop", str(counter))
        time.sleep(1)