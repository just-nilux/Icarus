from .telegram_wrapper import TelegramBot, TelegramMessageFormat
from telegram.ext.updater import Updater
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.filters import Filters
from telegram.ext.dispatcher import run_async
import asyncio
import mongo_utils
from pymongo import ASCENDING, DESCENDING

broker_client = None
loop = None

def init_telegram_bot(token, chat_id):
    TelegramBot.setToken(token)
    TelegramBot.setChatId(chat_id)
    TelegramBot.add_handler(CommandHandler('kill', TelegramBot.kill), description="Killing the bot...")
    TelegramBot.add_handler(CommandHandler('help', TelegramBot.help), description="Print help message")
    TelegramBot.add_handler(CommandHandler('ping', TelegramBot.pong), description="Ping the bot")
    TelegramBot.add_handler(CommandHandler('balance', balance_message, run_async=True), description="Balance")
    #TelegramBot.updater.dispatcher.run_async(balance_message)

    #TelegramBot.add_handler(CommandHandler('async', async_command, run_async=True), description="async")

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


def enable_broker_interface(broker, client, config):
    
    TelegramBot.broker_args = [client, config]
    TelegramBot.broker_class = broker


def start_telegram_bot():
    TelegramBot.updater.start_polling()
    TelegramBot.send_raw_message("Icarus started")
    #TelegramBot.send_formatted_message('help')

def unknown_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Sorry '%s' is not a valid command" % update.message.text)

def aexec(func):
    #global loop
    def wrapper(update: Update, context: CallbackContext):
        asyncio.run(func(update, context))
    return wrapper

@aexec
async def balance_message(update: Update, context: CallbackContext):
    mongo_client = mongo_utils.MongoClient(**TelegramBot.client_config['mongodb'])
    last_balance = await mongo_client.get_n_docs('observer', {'type':'balance'}, order=DESCENDING) # pymongo.ASCENDING
    update.message.reply_text(str(last_balance))

