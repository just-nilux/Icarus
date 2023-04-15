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

    format = TelegramMessageFormat('Help:','\n','\n        ','/{}: {}')
    TelegramBot.add_format('help', format, constant_data=TelegramBot.command_desc)

    format = TelegramMessageFormat('Error occured:','\n','\n        ','{}')
    TelegramBot.add_format('error', format, constant_data=TelegramBot.command_desc)


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
        reply_text = df_balance

    elif command_arg == 'gettrades':
        reply_text = await mongo_client.do_aggregate('live-trades', [])

    elif command_arg == 'trade' and context.args[1] != '':
        reply_text = await mongo_client.do_aggregate('live-trades',[{ '$match': { '_id': str(context.args[1])} }])

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
        if hasattr(broker_client, command_arg):
            result = await getattr(broker_client, command_arg)()
        elif hasattr(client, command_arg):
            result = await getattr(client, command_arg)()
        else:
            print('No such command as {}'.format(command_arg))
            return
    except Exception as e:
        print(e)
    await broker_client.close_connection()
    update.message.reply_text(str(result))


