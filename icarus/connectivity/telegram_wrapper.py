from dataclasses import dataclass
from telegram.ext.updater import Updater
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.filters import Filters
  
import sys
import json
import time
import os
import signal

@dataclass
class TelegramMessageFormat():
    header_format: str = ''
    tailer_format: str = ''
    line_indent: str = '\n        '
    line_format: str = ''
    constant_message: None = None

    def build_from_dict(self, data) -> str:
        body = ''
        for key, pair in data.items():
            line = self.line_indent + self.line_format.format(key, pair)
            body += line
        return body 

    def build_from_list(self, data) -> str:
        body = ''
        for datum in data:
            line = self.line_indent + self.line_format.format(datum)
            body += line
        return body

    def build(self, body_data, header_data, tailer_data, is_constant=False) -> str:

        if header_data:
            message = self.header_format.format(*header_data)
        else:
            message = self.header_format

        if type(body_data) == dict:
            message += self.build_from_dict(body_data)
        elif type(body_data) == list:
            message += self.build_from_list(body_data)

        if tailer_data:
            message += self.tailer_format.format(*tailer_data)
        else:
            message += self.tailer_format

        #message += self.tailer

        # If message is constant, store it to be used
        if is_constant:
            self.constant_message = message

        return message


class TelegramBot():
    updater = None
    chatId = None
    help_message = None
    command_desc = {}
    telegram_formats = {}

    @staticmethod
    def setToken(token):
        TelegramBot.updater = Updater(token,
                  use_context=True)
    @staticmethod
    def setChatId(chatId):
        TelegramBot.chatId = chatId

    @staticmethod
    def send_raw_message(message):
        # Send the message if updater and chatId exist
        if TelegramBot.updater != None and TelegramBot.chatId != None:
            TelegramBot.updater.bot.send_message(TelegramBot.chatId, text=message)
        return message

    @staticmethod
    def send_formatted_message(format, body_data=[], header_data=[], tailer_data=[]):
        message = ''
        if message := TelegramBot.telegram_formats[format].constant_message:
            pass
        else:
            message = TelegramBot.telegram_formats[format].build(body_data, header_data, tailer_data)
        return TelegramBot.send_raw_message(message)

    @staticmethod
    def add_format(format_name, telegram_format: TelegramMessageFormat, constant_data=None):
        if constant_data != None:
            telegram_format.build(body_data=constant_data, header_data=[], tailer_data=[], is_constant=True)
        TelegramBot.telegram_formats[format_name] = telegram_format

    @staticmethod
    def add_handler(handler, description = ""):
        TelegramBot.updater.dispatcher.add_handler(handler)
        if type(handler) == CommandHandler:
            TelegramBot.command_desc[handler.command[0]] = description

    @staticmethod
    def help(update: Update, context: CallbackContext):
        message = 'Available Commands:\n'
        for command, desc in TelegramBot.command_desc.items():
            message += f'        /{command}: {TelegramBot.command_desc.get(command, "")}\n'
        update.message.reply_text(message)

    @staticmethod
    def kill(update: Update, context: CallbackContext):
        update.message.reply_text("Killing the bot!")
        os.kill(os.getpid(), signal.SIGINT)

    @staticmethod
    def pong(update: Update, context: CallbackContext):
        update.message.reply_text("pong")


def unknown_command(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Sorry '%s' is not a valid command" % update.message.text)


def unknown_text(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Sorry I can't recognize you , you said '%s'" % update.message.text)


if __name__ == "__main__":
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)

    TelegramBot.setToken(config['Telegram']['token'])
    TelegramBot.setChatId(config['Telegram']['chat_id'])
    TelegramBot.add_handler(CommandHandler('kill', TelegramBot.kill), description="Killing the bot...")
    TelegramBot.add_handler(CommandHandler('help', TelegramBot.help), description="Print help message")
    TelegramBot.add_handler(CommandHandler('ping', TelegramBot.pong), description="Ping the bot")

    TelegramBot.add_handler(MessageHandler(Filters.text, unknown_command))
    #TelegramBot.add_handler(MessageHandler(Filters.command, unknown_command))
    TelegramBot.add_handler(MessageHandler(Filters.text, unknown_text))

    # How to get chatId: https://api.telegram.org/bot<YourBOTToken>/getUpdates
    TelegramBot.send_raw_message("dummy message")

    format = TelegramMessageFormat('Header','\ntailer','\n        ','/{}: {}')
    TelegramBot.add_format('help', format, constant_data=TelegramBot.command_desc)
    TelegramBot.send_formatted_message('help')

    complex_format = TelegramMessageFormat(
        header_format='Strategy: {}, side: {}',
        tailer_format='\nTrade ID: {}',
        line_indent='\n        ',
        line_format='/{}: {}')
    TelegramBot.add_format('complex_message', complex_format)
    
    body_data = {'key1':'value1', 'key2':'value2'}
    header_data = ['text1', 'text2']
    tailer_data = ['1234567']
    TelegramBot.send_formatted_message('complex_message',body_data=body_data, header_data=header_data, tailer_data=tailer_data)

    commandss = [cmd_handler.command[0] for cmd_handler in TelegramBot.updater.dispatcher.handlers[0] if type(cmd_handler) == CommandHandler]
    TelegramBot.updater.start_polling()
    # TODO: PoC of error logging to Telegram
    #TelegramBot.updater.idle()

    counter = 0
    while(True):
        print("in loop", str(counter))
        time.sleep(1)
