import time
import json
from binance.client import Client
from binance.enums import *

# Global Variables
credential_file = r'C:\Users\bilko\PycharmProjects\trading-bot\test_credentials.json'
with open(credential_file, 'r') as cred_file:
    cred_info = json.load(cred_file)

client = Client(api_key=cred_info['Binance']['Production']['PUBLIC-KEY'], api_secret=cred_info['Binance']['Production']['SECRET-KEY'])

# Place the break point here
pass