import unittest
from connectivity_bot.telegram_wrapper import *

class test_TelegramMessageFormat(unittest.TestCase):
    
    def test_format_from_list(self):
        format = TelegramMessageFormat('Header','\ntailer','\n        ','/{} <-')
        format_name = 'default_format'
        TelegramBot.add_format(format_name,format)
        data = ['item1', 'item2']
        message_evaluated = TelegramBot.telegram_formats[format_name].build(data)
        message_expected = """Header\n        /item1 <-\n        /item2 <-\ntailer"""
        
        self.assertEqual(message_evaluated, message_expected)

    def test_format_from_dict(self):
        format = TelegramMessageFormat('Header','\ntailer','\n        ','/{}: {}')
        format_name = 'default_format'
        TelegramBot.add_format(format_name,format)
        data = {'key1':'value1', 'key2':'value2'}
        message_evaluated = TelegramBot.telegram_formats[format_name].build(data)
        message_expected = """Header\n        /key1: value1\n        /key2: value2\ntailer"""
        
        self.assertEqual(message_evaluated, message_expected)

    def test_format_constant(self):
        data = {'key1':'value1', 'key2':'value2'}
        format = TelegramMessageFormat('Header','\ntailer','\n        ','/{}: {}')
        format_name = 'constant_format'
        TelegramBot.add_format(format_name, format, constant_data=data)
        message_evaluated = TelegramBot.send_formatted_message(format_name)
        message_expected = """Header\n        /key1: value1\n        /key2: value2\ntailer"""
        
        self.assertEqual(message_evaluated, message_expected)


    def setUp(self):
        print(self.id())
    
    def tearDown(self):
        #print(self._testMethodName)
        pass


if __name__ == '__main__':
    unittest.main(verbosity=2)