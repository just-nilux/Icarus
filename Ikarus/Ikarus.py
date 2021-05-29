from binance import Client
import asyncio
import pandas as pd
import logging
from datetime import datetime, timedelta
import json
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
class Ikarus():

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

        self.ref_currency = 'USDT'
        self.base_currency = 'TRY'

        # Default Parameters
        

        print(Ikarus.def_time_df)
        pass

    async def logger_test(self):
        self.logger.debug('logger_test')
        self.logger.info('logger_test')
        self.logger.warning('logger_test')
        self.logger.error('logger_test')
        self.logger.critical('logger_test')

    async def get_info(self):
        info = await self.client.get_account()
        balance = [{'asset':b['asset'], 'free':b['free'], 'locked':b['locked']}
                   for b in info['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]

        df_balance = pd.DataFrame(balance)
        df_balance.set_index(['asset'], inplace=True)
        df_balance = df_balance.astype(float)
        df_balance['total'] = df_balance['free'] + df_balance['locked']
        pairs = []
        for asset in df_balance.index:
            if asset == self.ref_currency:
                pairs.append(str(asset))
            elif asset == self.base_currency:
                pairs.append(str(self.ref_currency)+str(asset))
            else:
                pairs.append(str(asset)+str(self.ref_currency))
        df_balance['pair'] = pairs
        return df_balance

    async def get_all_tickers(self):
        df = pd.DataFrame(await self.client.get_all_tickers())
        df.set_index('symbol', inplace=True)
        df.astype(float)
        return df

    async def get_current_balance(self):

        df_balance, df_tickers = await asyncio.gather(
            self.get_info(),
            self.get_all_tickers()
        )

        price = [float(df_tickers.loc[pair]['price'])
                 if pair != self.ref_currency
                 else 1
                 for pair in df_balance['pair']]

        df_balance['price'] = price
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

        kline_dict = dict()
        num_of_scale = len(time_df.index)
        for idx_pair,pair in enumerate(pairs):
            self.logger.debug("decompose started: [{}]".format(pair))
            kline_dict_pair={}
            for idx_row, row in time_df.iterrows():
                self.logger.debug("decomposing [{}]: [{}]".format(pair,row["scale"]))
                df = pd.DataFrame(list_klines[idx_row + idx_pair*num_of_scale])
                df.columns = Ikarus.kline_column_names
                kline_dict_pair[row["scale"]] = df
                
            kline_dict[pair] = kline_dict_pair
            self.logger.debug("decompose ended [{}]:".format(pair))
            #self.logger.debug("{}-{}".format(pair,type(kline_dict[pair][row["scale"]])))

        self.logger.debug("decompose ended")
        return kline_dict

    # Ikaus Test Methods
    async def get_test_data_dict(self, pairs, time_df):
        """
        This functions returns the TEST historical kline values in the data_dict format.

        Args:
            pairs (list): [description]
            time_df (pd.DataFrame): [description]

        Returns:
            dict: [description]
        """
        # TODO: create test-data folder and gather sample to test each scenario such as:
        #       Enter: [ succesful | expire ]
        #       Enter: [ limit | oco-limit | oco-stop-loss | expire ]
        tasks_klines_scales = []
        for pair in pairs:
            for index, row in time_df.iterrows():
                tasks_klines_scales.append(asyncio.create_task(self.client.get_historical_klines(pair, row["scale"], start_str="{} ago UTC".format(row["length"]))))
            
        composit_klines = list(await asyncio.gather(*tasks_klines_scales))
        data_dict = await self.decompose(pairs, time_df, composit_klines)
        return data_dict