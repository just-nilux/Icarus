from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import json
import sys
from datetime import datetime, timezone

class EMail():

    def __init__(self):
        raise NotImplementedError('Email is not supported yet')
        pass


class TelegramBot():

    def __init__(self, _token, _chatId, _telegram_config):
        self.updater = Updater(_token)
        self.chatId = _chatId
        self.telegram_config = _telegram_config

        # Start the Bot
        #self.updater.start_polling()
        #self.updater.idle()
        # TODO: NEXT: Instead of writing 'format', and giving list of values, just give the lto/hto itself and handle the data in function
        #       Buy doing so you dont need to change much thing if any update is needed
        self.templates = {
            'lto': 'LTO {}:\n\
        Strategy: {}\n\
        Pair: {}\n\
        {} order {} {}'.format,

            'hto': 'HTO {}:\n\
         Strategy: {}\n\
         Pair: {}\n\
         Start Time: {}\n\
         End Time: {}\n\
         Absolute Profit: {:.2f}\n\
         Total Profit: %{:.2f}'.format,

            'app': 'Application: {}'.format,

            'error': 'Error: {}'.format,

            'stat': 'STAT {}: {} order {} placed'.format,
        }

        '''
        TODO: Some queries would be fine
              - Get all LTOs
              - Get a specific LTO/HTO from DB
                  - current status
                  - stats (for HTO)
            \lto _id
            \hto _id
        
        TODO: Commandline tool:
            \cmd closeall
            \cmd stop
            \cmd start
            \cmd restart
        '''

    def send_constructed_msg(self, type, *args) -> None:
        # NOTE: This try-except statement is here to encapsulate timeout errors
        # TODO: Add proper logging instead of printing
        try:
            if type in self.telegram_config.keys() and self.telegram_config[type]:
                text = self.templates[type](*args)
                self.send_raw(text)

        except Exception as e:
            print(e)


    def send_raw(self, msg='Default Message') -> None:
        try:
            self.updater.bot.send_message(self.chatId, text=msg)
        except Exception as e:
            print(e)
            # TODO: NEXT: Add logging


def test_lto():
    args = ['611eb00fe9350843f569a567', 'StrategyName', 'Pair', 'enter', 7237001592, 'closed'] 
    telbot.send_constructed_msg('lto', *args )
    pass

def test_hto():
    args = ['611eb00fe9350843f569a567', 'AlwaysEnter', 'AVAXUSDT', datetime.fromtimestamp(1589418000, timezone.utc), datetime.fromtimestamp(1589418000, timezone.utc), 27.75, 0.29951430113329736]
    telbot.send_constructed_msg('hto', *args )
    pass

def test_error():
    telbot.send_constructed_msg('error', *['message message message message message'] )
    pass

def test_config():
    telbot.send_constructed_msg('error', *['message message message message message'] )
    pass

if __name__ == '__main__':
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    telbot = TelegramBot(cred_info['Telegram']['Token'], cred_info['Telegram']['ChatId'], config['notification']['telegram'])
    #test_hto()
    #test_error()
    test_config()