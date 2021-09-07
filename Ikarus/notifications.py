from telegram import Update, ForceReply
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import json
import sys
from datetime import datetime, timezone
class TelegramBot():

    def __init__(self, _token, _chatId):
        self.updater = Updater(_token)
        self.chatId = _chatId

        # Start the Bot
        #self.updater.start_polling()
        #self.updater.idle()
        # TODO: Apply alingment to messages
        self.templates = {
            'lto': 'LTO {}:\n        {} order {} {}'.format,
            # {_id} {phase} {orderId} {event}

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
        text = self.templates[type](*args)
        self.send_raw(text)


    def send_raw(self, msg='Default Message') -> None:  
        self.updater.bot.send_message(self.chatId, text=msg)


def test_lto():
    args = ['611eb00fe9350843f569a567', 'enter', 7237001592, 'closed'] 
    telbot.send_constructed_msg('lto', *args )
    pass

def test_hto():
    args = ['611eb00fe9350843f569a567', 'AlwaysEnter', 'AVAXUSDT', datetime.fromtimestamp(1589418000, timezone.utc), datetime.fromtimestamp(1589418000, timezone.utc), 27.75, 0.29951430113329736]
    telbot.send_constructed_msg('hto', *args )
    pass

def test_error():
    telbot.send_constructed_msg('error', *['message message message message message'] )
    pass

if __name__ == '__main__':
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    telbot = TelegramBot(cred_info['Telegram']['Token'], cred_info['Telegram']['ChatId'])
    test_hto()
    test_error()