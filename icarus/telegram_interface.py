from connectivity.telegram_wrapper import TelegramBot, TelegramMessageFormat, asynchandler
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.filters import Filters
import mongo_utils
from pymongo import ASCENDING, DESCENDING
from brokers.binance_wrapper import BinanceWrapper
from binance import AsyncClient
import pandas as pd
from dataclasses import asdict
import datetime

def init_telegram_bot(token, chat_id):
    desc_padding = '                '

    TelegramBot.setToken(token)
    TelegramBot.setChatId(chat_id)
    TelegramBot.add_handler(CommandHandler('kill', TelegramBot.kill), description="Killing the bot...")
    TelegramBot.add_handler(CommandHandler('help', TelegramBot.help), description="Print help message")
    TelegramBot.add_handler(CommandHandler('ping', TelegramBot.pong), description="Ping the bot")

    description = f'Database\n{desc_padding}getbalance\n{desc_padding}gettrades\n{desc_padding}trade <_id>'
    TelegramBot.add_handler(CommandHandler('db', db_handler, run_async=True), description=description)

    description = f'Binance\n{desc_padding}get_status\n{desc_padding}get_current_balance'
    TelegramBot.add_handler(CommandHandler('binance', binance_handler, run_async=True), description=description)
    TelegramBot.add_handler(MessageHandler(Filters.text, unknown_command))

    format = TelegramMessageFormat('Balance:','\n','\n        ','{}')
    TelegramBot.add_format('balance', format)

    # Enter order executed: StrategyName
    format = TelegramMessageFormat('{} order executed: {}','\nTrade ID: {}','\n        ','{}: {}')
    TelegramBot.add_format('order_executed', format)

    # Enter order filled: StrategyName
    format = TelegramMessageFormat('{} order filled: {}','\nTrade ID: {}','\n        ','{}: {}')
    TelegramBot.add_format('order_filled', format)

    # Trade closed: StrategyName
    format = TelegramMessageFormat('Trade closed: {}','\nTrade ID: {}','\n        ','{}: {}')
    TelegramBot.add_format('trade_closed', format)

    format = TelegramMessageFormat('Trade: {}','','\n        ','{}: {}')
    TelegramBot.add_format('trade_basic', format)

    format = TelegramMessageFormat('Help:','\n','\n        ','/{}: {}')
    TelegramBot.add_format('help', format, constant_data=TelegramBot.command_desc)

    format = TelegramMessageFormat('Error occured:','\n','','{}')
    TelegramBot.add_format('error', format)


def enable_db_interface(config):
    TelegramBot.database_config = config


def enable_binance_interface(credentials):
    TelegramBot.binance_credentials = credentials


def start_telegram_bot():
    TelegramBot.updater.start_polling()
    TelegramBot.send_raw_message("Icarus started")
    #TelegramBot.send_formatted_message('help')


def unknown_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Sorry '%s' is not a valid command" % update.message.text)


@asynchandler
async def db_handler(update: Update, context: CallbackContext):
    if len(context.args) < 1:
        return
    
    command_arg = context.args[0]

    if TelegramBot.database_config == None:
        update.message.reply_text('Database interface is not enabled!')
        return
    
    mongo_client = mongo_utils.MongoClient(**TelegramBot.database_config)

    # TODO: Generalize the logic
    if command_arg == 'getbalance':
        balance = await mongo_client.get_n_docs('observer', {'type':'balance'}, order=DESCENDING) # pymongo.ASCENDING

        df_balance = pd.DataFrame(balance[0]['data'])
        df_balance.set_index(['asset'], inplace=True)
        df_balance = df_balance.astype(float)
        df_balance['total'] = df_balance['free'] + df_balance['locked']
        TelegramBot.send_table(df_balance.to_markdown())
        return


    elif command_arg == 'gettrades':
        trades = await mongo_utils.do_aggregate_trades(mongo_client, 'live-trades', [])
        reply_text = ''
        for trade in trades:
            trade_basic = {
                'status':trade.status, 
                'strategy':trade.strategy, 
                'creation': datetime.datetime.fromtimestamp(trade.decision_time).strftime('%Y-%m-%d %H:%M')
                }
            reply_text += TelegramBot.telegram_formats['trade_basic'].build(trade_basic, [trade._id],[])
            reply_text += '\n'

    elif command_arg == 'trade' and context.args[1] != '':
        [trade] = await mongo_utils.do_aggregate_trades(mongo_client, 'live-trades', [{ '$match': { '_id': str(context.args[1])} }])
        TelegramBot.send_formatted_message('trade_basic', asdict(trade), [trade._id], [])
        return


    update.message.reply_text(str(reply_text))


@asynchandler
async def binance_handler(update: Update, context: CallbackContext):
    if len(context.args) != 1:
        return
    
    command_arg = context.args[0]

    if TelegramBot.binance_credentials == None:
        update.message.reply_text('Binance interface is not enabled!')
        return
    
    client = await AsyncClient.create(**TelegramBot.binance_credentials)
    mock_config = {'broker':{'quote_currency': 'USDT'}}
    broker_client = BinanceWrapper(client, mock_config)

    try:
        if command_arg == 'balance':
            df_balance = await broker_client.get_current_balance()
            TelegramBot.send_table(df_balance.to_markdown())
            return

        elif hasattr(broker_client, command_arg):
            result = await getattr(broker_client, command_arg)()
        elif hasattr(client, command_arg):
            result = await getattr(client, command_arg)()
        else:
            print('No such command as {}'.format(command_arg))
            return
        update.message.reply_text(str(result))
    except Exception as e:
        TelegramBot.send_formatted_message('error', [str(e)])

    await broker_client.close_connection()
    


