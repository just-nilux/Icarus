from pymongo import mongo_client
from Ikarus import mongo_utils
from binance import Client
import asyncio
import pandas as pd
import logging
from datetime import datetime, timedelta
from Ikarus.objects import GenericObject, ObjectEncoder
import json
import numpy as np
'''
[
  [
    1499040000000,      // Open time
    "0.01634790",       // Open
    "0.80000000",       // High
    "0.01575800",       // Low
    "0.01577100",       // Close
    "148976.11427815",  // Volume
    1499644799999,      // Close time
    "2434.19055334",    // Quote asset volume
    308,                // Number of trades
    "1756.87402397",    // Taker buy base asset volume
    "28.46694368",      // Taker buy quote asset volume
    "17928899.62484339" // Ignore.
  ]
]
'''
class BinanceWrapper():

    def_time_scales = [Client.KLINE_INTERVAL_1MINUTE, 
                            Client.KLINE_INTERVAL_15MINUTE, 
                            Client.KLINE_INTERVAL_1HOUR, 
                            Client.KLINE_INTERVAL_1DAY, 
                            Client.KLINE_INTERVAL_1WEEK, 
                            Client.KLINE_INTERVAL_1MONTH]
    def_time_lengths_str = ["1 hour", "1 day", "1 week", "1 month", "6 months", "12 months"]

    kline_column_names = ["open_time", "open", "high", "low", "close", "volume", "close_time","quote_asset_volume", 
                        "nbum_of_trades", "taker_buy_base_ast_vol", "taker_buy_quote_ast_vol", "ignore"]

    # def_time_df stores the time scale and length for klines
    def_time_df = pd.DataFrame({"scale":def_time_scales, "length":def_time_lengths_str})

    def __init__(self, _client):
        self.client = _client

        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.logger.info('creating an instance of {}'.format(__name__))

        self.quote_currency = 'USDT'
        self.credit_currency = 'TRY'


        # Currency pairs compare the value of one currency to another—the base currency (or the first one) 
        # versus the second or the quote currency. It indicates how much of the quote currency is needed to 
        # purchase one unit of the base currency.
        
        # The quotation EUR/USD = 1.2500 means that one euro is exchanged for 1.2500 U.S. dollars. In this case, 
        # EUR is the base currency and USD is the quote currency (counter currency). This means that 1 euro can be 
        # exchanged for 1.25 U.S. dollars. Another way of looking at this is that it will cost you $125 to buy 100 euros.

        # Default Parameters
        

        print(BinanceWrapper.def_time_df)
        pass

    async def logger_test(self):
        self.logger.debug('logger_test')
        self.logger.info('logger_test')
        self.logger.warning('logger_test')
        self.logger.error('logger_test')
        self.logger.critical('logger_test')

    async def get_info(self):
        """
        Get all assets with 'free' and 'locked' parts

        Returns:
            pd.DataFrame: df_balance
        """        
        info = await self.client.get_account()
        balance = [{'asset':b['asset'], 'free':b['free'], 'locked':b['locked']}
                   for b in info['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]

        df_balance = pd.DataFrame(balance)
        df_balance.set_index(['asset'], inplace=True)
        df_balance = df_balance.astype(float)
        df_balance['total'] = df_balance['free'] + df_balance['locked']
        pairs = []
        for asset in df_balance.index:
            if asset == self.quote_currency:
                pairs.append(str(asset))
            elif asset == self.credit_currency:
                pairs.append(str(self.quote_currency)+str(asset))
            else:
                pairs.append(str(asset)+str(self.quote_currency))
        df_balance['pair'] = pairs
        return df_balance

    async def get_all_tickers(self):
        """
        Get all possible tickers

        Returns:
            pd.DataFrame: tickers
        """        
        df = pd.DataFrame(await self.client.get_all_tickers())
        df.set_index('symbol', inplace=True)
        df.astype(float)
        return df

    async def get_current_balance(self):

        df_balance, df_tickers = await asyncio.gather(
            self.get_info(),
            self.get_all_tickers()
        )

        # Add current prices to df_balance
        price = [float(df_tickers.loc[pair]['price'])
                 if pair != self.quote_currency
                 else 1
                 for pair in df_balance['pair']]
        df_balance['price'] = price

        # Evaluate the equity in terms of quote_currency
        df_balance['ref_balance'] = df_balance['price'] * df_balance['total']

        return df_balance

    async def get_data_dict(self, pairs, time_df):
        """
        This functions returns the historical kline values in the data_dict format.

        Args:
            pairs (list): [description]
            time_df (pd.DataFrame): [description]

        Returns:
            dict: [description]
        """
        tasks_klines_scales = []
        for pair in pairs:
            for index, row in time_df.iterrows():
                tasks_klines_scales.append(asyncio.create_task(self.client.get_historical_klines(pair, row["scale"], start_str="{} ago UTC".format(row["length"]))))
            
        composit_klines = list(await asyncio.gather(*tasks_klines_scales))
        data_dict = await self.decompose(pairs, time_df, composit_klines)

        await self.dump_data_obj(data_dict)

        # data_dict
        return data_dict


    async def monitor_account(self):
        return True


    async def update_db(self,trade_objs):
        return True


    async def execute_decision(self, trade_objs):
        return True


    async def pprint_klines(self, list_klines):
        self.logger.debug("Length of klines: {}".format(len(list_klines)))
        for idx,kline in enumerate(list_klines):
            self.logger.debug("-->Lenth of kline {}: {}".format(idx, len(kline)))
            self.logger.debug("----> 0:[{}] 1:[{}] ... {}:[{}]".format(kline[0][0],kline[1][0],len(kline)-1,kline[-1][0]))


    async def decompose(self, pairs, time_df, list_klines):
        """
        decompose is the function that splits the asyncio.gather()

        Args:
            pairs (list): ["BTCUSDT","XRPUSDT","BTTUSDT"]
            time_df (pd.DataFrame): pd.DataFrame({"scale":def_time_scales, "length":def_time_lengths_str})
            list_klines (list): output of asyncio.gather()

        Returns:
            dict: decomposed list_klines
        """        
        self.logger.debug("decompose started")

        do_dict = dict()
        num_of_scale = len(time_df.index)
        for idx_pair,pair in enumerate(pairs):
            self.logger.debug("decompose started: [{}]".format(pair))
            do = GenericObject()
            for idx_row, row in time_df.iterrows():
                self.logger.debug("decomposing [{}]: [{}]".format(pair,row["scale"]))
                df = pd.DataFrame(list_klines[idx_row + idx_pair*num_of_scale])
                df.columns = BinanceWrapper.kline_column_names
                do.load(row["scale"],df)
                print(row["scale"])
                print(df)
            do_dict[pair] = do
            self.logger.debug("decompose ended [{}]:".format(pair))
            #self.logger.debug("{}-{}".format(pair,type(do_dict[pair][row["scale"]])))

        self.logger.debug("decompose ended")
        return do_dict


    async def dump_data_obj(self, js_obj):

        copy_obj = dict()
        for pair,do in js_obj.items():
            pair_obj = dict()
            for k,v in do.get().items():
                pair_obj[k] = v.to_string()
            copy_obj[pair] = pair_obj


        self.logger.debug("data.json file created")
        js_file = open("run-time-objs/data.json", "w")
        json.dump(copy_obj, js_file, indent=4)
        js_file.close()

        return True



class TestBinanceWrapper():

    def_time_scales = [Client.KLINE_INTERVAL_1MINUTE, 
                            Client.KLINE_INTERVAL_15MINUTE, 
                            Client.KLINE_INTERVAL_1HOUR, 
                            Client.KLINE_INTERVAL_1DAY, 
                            Client.KLINE_INTERVAL_1WEEK, 
                            Client.KLINE_INTERVAL_1MONTH]
    def_time_lengths_str = ["1 hour", "1 day", "1 week", "1 month", "6 months", "12 months"]

    kline_column_names = ["open_time", "open", "high", "low", "close", "volume", "close_time","quote_asset_volume", 
                        "nbum_of_trades", "taker_buy_base_ast_vol", "taker_buy_quote_ast_vol", "ignore"]

    # def_time_df stores the time scale and length for klines
    def_time_df = pd.DataFrame({"scale":def_time_scales, "length":def_time_lengths_str})

    df_tickers = None

    def __init__(self, _client, _commission):

        self.client = _client

        # Set initial cash in the quote_currency
        self.comission = float(_commission)

        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.logger.info('creating an instance of {}'.format(__name__))

        # Set reference currencies
        self.quote_currency = 'USDT'
        self.credit_currency = 'TRY'

        # TestBinanceWrapper: get df_tickers once

        print(TestBinanceWrapper.def_time_df)
        pass


    async def get_info(self,last_observer_item):
        """
        Get all assets with 'free' and 'locked' parts

        Returns:
            pd.DataFrame: df_balance
                    free      locked       total      pair
            asset                                            
            BTC    0.024519    0.010736    0.035255   BTCUSDT
            USDT   0.009022    0.000000    0.009022      USDT
            DOGE   0.000000  215.300000  215.300000  DOGEUSDT
            TRY    0.213130    0.000000    0.213130   USDTTRY
            
            Initial contidition:
                    free      locked       total      pair
            asset                                            
            USDT   0.009022    0.000000    0.009022      USDT
        """

        '''
        Normally self.client.get_account() receives data from Binance API, instead the observer db can be used
        to store df_balances. It might be inserted to the DB in the beginning, then a new observer item would be
        inserted in each iteration. Using this method, equity can be traced throughout the session
        '''

        balance = [{'asset':b['asset'], 'free':b['free'], 'locked':b['locked']}
                   for b in last_observer_item['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]

        df_balance = pd.DataFrame(balance)
        df_balance.set_index(['asset'], inplace=True)
        df_balance = df_balance.astype(float)
        df_balance['total'] = df_balance['free'] + df_balance['locked']
        pairs = []
        for asset in df_balance.index:
            if asset == self.quote_currency:
                pairs.append(str(asset))
            elif asset == self.credit_currency:
                pairs.append(str(self.quote_currency)+str(asset))
            else:
                pairs.append(str(asset)+str(self.quote_currency))
        df_balance['pair'] = pairs

        return df_balance


    async def get_all_tickers(self):
        """
        Get all possible tickers

        Returns:
            pd.DataFrame: tickers
        """        
        df = pd.DataFrame(await self.client.get_all_tickers())
        df.set_index('symbol', inplace=True)
        df.astype(float)
        return df

    async def get_current_balance(self,last_observer_item):
        '''
        Get all assets with 'free' and 'locked' parts

        Returns:
            pd.DataFrame: df_balance
                    free      locked       total      pair        price  ref_balance
            asset                                                                      
            BTC    0.024519    0.010736    0.035255   BTCUSDT  33299.74000  1173.982334
            BNB    0.192785    0.000000    0.192785   BNBUSDT    287.19000    55.365798
            USDT   0.009022    0.000000    0.009022      USDT      1.00000     0.009022
            XRP    0.006440   55.000000   55.006440   XRPUSDT      0.66190    36.408763
            DOGE   0.000000  215.300000  215.300000  DOGEUSDT      0.24518    52.787254
            TRY    0.213130    0.000000    0.213130   USDTTRY      8.68100     1.850185
            AVAX   0.000000    5.793000    5.793000  AVAXUSDT     11.21300    64.956909
        '''        
        
        # Since current price does not matter getting the ticker once will be enough
        '''
        df_balance, df_tickers = await asyncio.gather(
            self.get_info(last_observer_item),
            self.get_all_tickers()
        )
        '''

        df_balance = await self.get_info(last_observer_item)

        # Add current prices to df_balance
        price = [float(TestBinanceWrapper.df_tickers.loc[pair]['price'])
                 if pair != self.quote_currency
                 else 1
                 for pair in df_balance['pair']]
        df_balance['price'] = price

        # Evaluate the equity in terms of quote_currency
        df_balance['ref_balance'] = df_balance['price'] * df_balance['total']

        return df_balance

    async def get_data_dict(self, pairs, time_df, df_list):
        '''
        time_df:
        -------------------------
            scale   length
        0   15m     96/"1 day" 
        1   1h      168/"1 week"
        -------------------------
        '''

        do_dict = dict()
        for idx_pair,pair in enumerate(pairs):
            do = GenericObject()
            # This only works if only 1 time scale(i.e. 15m) is given for each pair and they are the same
            for idx_row, row in time_df.iterrows():
                do.load(row["scale"],df_list[idx_pair])

            do_dict[pair] = do
            
        await self.dump_data_obj(do_dict)
        return do_dict    


    async def dump_data_obj(self, js_obj):

            copy_obj = dict()
            for pair,do in js_obj.items():
                pair_obj = dict()
                for k,v in do.get().items():
                    pair_obj[k] = v.to_string()
                copy_obj[pair] = pair_obj

            js_file = open("run-time-objs/test-data_obj.json", "w")
            json.dump(copy_obj, js_file, indent=4)
            js_file.close()

            return True

    async def execute_decision(self, trade_dict, df_balances):
        """
        TestBinanceWrapper: In test sessions, executing a trade_object means
        changing the df_balance columns 'free' and 'locked' when a trade is
        started

        Args:
            trade_dict (dict): [description]
            df_balances (pd.DataFrame): [description]

        Returns:
            tuple: result, df_balances
        """
        result = True
        # Execute trade_dict
        # TODO: HIGH: In the execute section commission needs to be evaluated. This section should behave
        #       exactly as the broker. 
        # NOTE: As a result the equity will be less than evaluated since the comission has been cut.

        # TODO: Evaluate 'free' and 'locked' sizes

        # Update free and locked amount of df_balances
        for pair,to in trade_dict.items():
            if to.get('status') == 'open_enter':
                #TODO: V2: 'USDT' should not be hardcoded
                df_balances.loc['USDT','free'] -= to.get(['enter','limitBuy','amount'])
                df_balances.loc['USDT','locked'] += to.get(['enter','limitBuy','amount'])

        return result, df_balances