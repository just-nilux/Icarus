from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext


class TelegramBot():

    def __init__(self, _token, _chatId):
        self.updater = Updater(_token)
        self.chatId = _chatId

        # Start the Bot
        #self.updater.start_polling()
        #self.updater.idle()

    def send(self, msg='Default Message') -> None:
        self.updater.bot.send_message(self.chatId, text=msg)


if __name__ == '__main__':
    tb = TelegramBot('1784165564:AAESd5bqPyoeVLO_ooHRHvx7Sq18jxjwraA', -518221191)
    tb.send("TelegramBot Main")
