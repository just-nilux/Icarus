from asyncio.tasks import gather
from typing import Awaitable
from binance import Client
import asyncio
import pandas as pd
import logging
from Ikarus.objects import GenericObject
import json
import bson
import time

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

    kline_column_names = ["open_time", "open", "high", "low", "close", "volume", "close_time","quote_asset_volume", 
                        "nbum_of_trades", "taker_buy_base_ast_vol", "taker_buy_quote_ast_vol", "ignore"]

    def __init__(self, _client, _config):
        self.client = _client
        self.config = _config
        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.logger.info('creating an instance of {}'.format(__name__))

        # Set reference currencies
        self.quote_currency = _config['broker']['quote_currency']
        self.credit_currency = _config['broker']['credit_currency']

        # Currency pairs compare the value of one currency to another—the base currency (or the first one) 
        # versus the second or the quote currency. It indicates how much of the quote currency is needed to 
        # purchase one unit of the base currency.
        
        # The quotation EUR/USD = 1.2500 means that one euro is exchanged for 1.2500 U.S. dollars. In this case, 
        # EUR is the base currency and USD is the quote currency (counter currency). This means that 1 euro can be 
        # exchanged for 1.25 U.S. dollars. Another way of looking at this is that it will cost you $125 to buy 100 euros.
        pass


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

        # TODO: The logic of creating pairs might be updated to try the both combination
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
                tasks_klines_scales.append(asyncio.create_task(self.client.get_historical_klines(pair, row["scale"], start_str="{} ago UTC".format(row["length_str"]))))

        composit_klines = list(await asyncio.gather(*tasks_klines_scales))
        data_dict = await self.decompose(pairs, time_df, composit_klines)

        await self.dump_data_obj(data_dict)
        # NOTE: Keep in mind that the last row is the current candle that has not been completed
        return data_dict


    async def get_lto_orders(self, lto_dict):
        """
        This functions gathers the corresponding order objects of LTOs from the brokers

        Args:
            lto_dict (dict): [description]

        Returns:
            [dict]: Each tradeid (orderId) is mapped to it's order object
        """
        # Check the status of LTOs:
        coroutines = []
        for tradeid, lto in lto_dict:
            coroutines.append(self.client.get_order(symbol=lto['tradeid'], orderId=tradeid))
            # NOTE: 'tradeid' can be changed with 'orderid' for the consistency with the api

        lto_orders_dict = {} # TODO: It can be a dict
        if len(coroutines):
            for order in list(asyncio.gather(*coroutines)):
                lto_orders_dict[order['orderId']] = order
        
        # TESTING PURPOSES
        await self.get_open_orders()

        return lto_orders_dict


    async def get_open_orders(self):
        """
        This method returns all the open orders. 
        It might be useful to detect if there is an external source of order and keep track

        Returns:
            [type]: [description]
        """
        # NOTE: Currently it is not needed to take the external orders in account.
        # TODO: Decide what to do with all orders or all open orders
        orders = await self.client.get_order(symbol='BLZUSDT', orderId=173122044) # OCO-LIMIT SUCCESFULL / MULTIPLE COMISSION
        orders = await self.client.get_order(symbol='BLZUSDT', orderId=173122043) # OCO-STOPLOSS EXPIRED

        orders = await self.client.get_order(symbol='BTCUSDT', orderId=6002017720) # SUCCESFUL
        orders = await self.client.get_order(symbol='AVAXUSDT', orderId=340304592) # CANCEL
        orders = await self.client.get_order(symbol='DOGETRY', orderId=67156655) # OCO-STOPLOSS
        orders = await self.client.get_order(symbol='DOGETRY', orderId=67156656) # OCO-LIMIT EXPIRED


        orders = await self.client.get_open_orders(symbol='BTCUSDT')         
        orders = await self.client.get_open_orders(symbol='XRPUSDT')
        orders = await self.client.get_open_orders(symbol='AVAXUSDT')

        orders = await self.client.get_all_orders(symbol='BTCUSDT')
        orders = await self.client.get_all_orders(symbol='AVAXUSDT')
        orders = await self.client.get_all_orders(symbol='XRPUSDT')

        return orders


    async def monitor_account(self):
        return True


    async def _execute_lto(self, lto_dict):
        """
        Execution Logic:
        for tradeid in lto_dict.keys():
            if 'action' in lto_dict[tradeid].keys():
                1. cancel
                    In case of enter expire, it might be decided to cancel the order
                2. update
                    cancel the prev order and place the same type of order with updated values
                3. market_enter
                    In case of enter expire, it might be decided to enter with market order
                4. market_exit
                    In case of exit expire, it might be decided to exit with market order

        Args:
            lto_dict (dict): [description]
            df_balance (pd.DataFrame): [description]

        Returns:
            tuple: lto_dict, df_balance
        """
        for tradeid in lto_dict.keys():
            if 'action' in lto_dict[tradeid].keys():

                # NOTE: Consider the fact that each pair may contain more than 1 trade in future
                if lto_dict[tradeid]['action'] == 'cancel':
                    # TODO: 'cancel' action currently only used for enter phase, exit phase cancel can be added

                    # TODO: DEPLOY: Binance cancel the order
                    lto_dict[tradeid]['status'] = 'closed'
                    lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])
            
                elif lto_dict[tradeid]['action'] == 'update':
                    pass
                
                elif lto_dict[tradeid]['action'] == 'market_enter':
                    pass
                
                elif lto_dict[tradeid]['action'] == 'market_exit':

                    # TODO: DEPLOY: Execute Market Order in Binance
                    # TODO: DEPLOY: Wait until the execution and fill the TO 
                    '''
                    lto_dict[tradeid]['status'] = 'closed'
                    lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])
                    lto_dict[tradeid]['result']['cause'] = 'exit_expire'
                    last_kline = data_dict[lto_dict[tradeid]['pair']]['15m'].tail(1)

                    lto_dict[tradeid]['result']['exit']['type'] = 'market'
                    lto_dict[tradeid]['result']['exit']['time'] = bson.Int64(last_kline.index.values)
                    lto_dict[tradeid]['result']['exit']['price'] = float(last_kline['close'])
                    lto_dict[tradeid]['result']['exit']['quantity'] = lto_dict[tradeid]['exit']['market']['quantity']
                    lto_dict[tradeid]['result']['exit']['amount'] = lto_dict[tradeid]['result']['exit']['price'] * lto_dict[tradeid]['result']['exit']['quantity']

                    lto_dict[tradeid]['result']['profit'] = lto_dict[tradeid]['result']['exit']['amount'] - lto_dict[tradeid]['result']['enter']['amount']
                    '''
                    pass
            
                elif lto_dict[tradeid]['action'] == 'execute_exit':
                    # If the enter is successful and the algorithm decides to execute the exit order
                    # TODO: LIVE: Place the exit order to Binance: oco or limit
                    # TODO: LIVE: If the exit type is OCO, then fill the stoploss tradeid in the exit section

                    lto_dict[tradeid]['status'] = 'open_exit'
                    lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])
                    pass

                # Postpone can be for the enter or the exit phase
                elif lto_dict[tradeid]['action'] == 'postpone':
                    if lto_dict[tradeid]['status'] == 'enter_expire':
                        lto_dict[tradeid]['status'] = 'open_enter'
                        lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])

                    elif lto_dict[tradeid]['status'] == 'exit_expire':
                        lto_dict[tradeid]['status'] = 'open_exit'
                        lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])
                        pass
                    else: pass

                # Delete the action, after the action is taken
                del lto_dict[tradeid]['action']

        return lto_dict


    async def _execute_nto(self, trade_dict):
        """
        for to in trade_dict:
            1. open_enter
                a. market
                    - Get the 'result'
                b. limit
            2. partially_closed_enter
                -
            3. open_exit
                a. market
                    - Get the 'result'
                b. limit
                c. oco
            4. partially_closed_exit
            -

        Args:
            trade_dict (dict): [description]
            df_balances (pd.DataFrame): [description]

        Returns:
            [type]: [description]
        """
        for tradeid in trade_dict.keys():
            # NOTE: The status values other than 'open_enter' is here for lto update
            if trade_dict[tradeid]['status'] == 'open_enter':
                
                if 'market' in trade_dict[tradeid]['enter'].keys():
                    # NOTE: Since there is no risk evaluation in the market enter, It is not planned to be implemented
                    pass

                elif 'limit' in trade_dict[tradeid]['enter'].keys():
                    # TODO: NEXT: LIVE: Execute limit order
                    pass

                else: pass # TODO: Internal Error

            else: pass # TODO: Internal Error
        return trade_dict


    async def execute_decision(self, trade_dict, lto_dict):
        """
        'execute_decision' method is responsible for
            - execute new to's
            - execute lto updates
                - Strategy do not update the status. It creates the 'action' and the execute_decision update the status
            - update the df_balance

        TestBinanceWrapper: In test sessions, executing a trade_object means
        changing the df_balance columns 'free' and 'locked' when a trade is
        started

        Execution Logic:
        1. Execute live_trade_objects
        2. Execute new_trade_objects

        Args:
            trade_dict (dict): [description]
            df_balances (pd.DataFrame): [description]

        Returns:
            tuple: result, df_balances
        """
        result = True
        # TODO: These two execution can be done in paralel from the main script. No need for execute_decision (at least for the live-trading)

        # Execute decsisions about ltos
        # TODO: _execute_lto cannot decide to not to enter if there is not enough balance. This check should be done in strategy.
        # NOTE: _execute_lto tries to execute, if things fails then it creates an error log, notification etc.
        lto_dict = await self._execute_lto(lto_dict)

        # Execute new trade objects
        trade_dict = await self._execute_nto(trade_dict)      
            
        # TODO: Consider returning trade_dict, because:
        #   - orders may not be accepted by the broker
        #       - In this case this side where to handle the issue: here or the main script
        #   - market sell causes instant fill
        #   - market enter causes instant fill

        return result, lto_dict


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
        # TODO: Change the GenericObject to dict
        do_dict = dict()
        num_of_scale = len(time_df.index)
        for idx_pair,pair in enumerate(pairs):
            self.logger.debug("decompose started: [{}]".format(pair))
            do = dict()
            for idx_row, row in time_df.iterrows():
                self.logger.debug("decomposing [{}]: [{}]".format(pair,row["scale"]))
                df = pd.DataFrame(list_klines[idx_row + idx_pair*num_of_scale])
                df.columns = BinanceWrapper.kline_column_names
                do[row["scale"]] = df
            do_dict[pair] = do
            self.logger.debug("decompose ended [{}]:".format(pair))
            #self.logger.debug("{}-{}".format(pair,type(do_dict[pair][row["scale"]])))

        self.logger.debug("decompose ended")
        return do_dict


    async def dump_data_obj(self, js_obj):

        copy_obj = dict()
        for pair,do in js_obj.items():
            pair_obj = dict()
            for k,v in do.items():
                pair_obj[k] = v.to_string()
            copy_obj[pair] = pair_obj

        js_file = open("run-time-objs/data_obj.json", "w")
        json.dump(copy_obj, js_file, indent=4)
        js_file.close()

        return True


class TestBinanceWrapper():

    kline_column_names = ["open_time", "open", "high", "low", "close", "volume", "close_time","quote_asset_volume", 
                        "nbum_of_trades", "taker_buy_base_ast_vol", "taker_buy_quote_ast_vol", "ignore"]

    df_tickers = None

    def __init__(self, _client, _config):

        self.client = _client
        self.config = _config
        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.logger.info('creating an instance of {}'.format(__name__))

        # Set reference currencies
        self.quote_currency = _config['broker']['quote_currency']
        self.credit_currency = _config['broker']['credit_currency']

        # TestBinanceWrapper: get df_tickers once
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
        # NOTE: Ticker hack for testing
        f = open('tickers.json','r')
        tickers_json = json.load(f)
        tickers = tickers_json['tickers']
        df = pd.DataFrame(tickers)
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
        ---------------------------------------
            scale   length_str      length_int
        0   15m     96/"1 day"      96
        1   1h      168/"1 week"    x   
        ---------------------------------------
        '''

        do_dict = dict()
        for idx_pair,pair in enumerate(pairs):
            do = dict()
            # This only works if only 1 time scale(i.e. 15m) is given for each pair and they are the same
            for idx_row, row in time_df.iterrows():
                do[row["scale"]] = df_list[idx_pair]

            do_dict[pair] = do
        
        # await self.dump_data_obj(do_dict)
        return do_dict    


    async def dump_data_obj(self, js_obj):

            copy_obj = dict()
            for pair,do in js_obj.items():
                pair_obj = dict()
                for k,v in do.items():
                    pair_obj[k] = v.to_string()
                copy_obj[pair] = pair_obj

            js_file = open("run-time-objs/test-data_obj.json", "w")
            json.dump(copy_obj, js_file, indent=4)
            js_file.close()

            return True


    async def _execute_lto(self, lto_dict, df_balance, data_dict):
        """
        Execution Logic:
        for tradeid in lto_dict.keys():
            if 'action' in lto_dict[tradeid].keys():
                1. cancel
                    In case of enter expire, it might be decided to cancel the order
                2. update
                    cancel the prev order and place the same type of order with updated values
                3. market_enter
                    In case of enter expire, it might be decided to enter with market order
                4. market_exit
                    In case of exit expire, it might be decided to exit with market order

        Args:
            lto_dict (dict): [description]
            df_balance (pd.DataFrame): [description]

        Returns:
            tuple: lto_dict, df_balance
        """
        for tradeid in lto_dict.keys():
            if 'action' in lto_dict[tradeid].keys():

                # NOTE: Consider the fact that each pair may contain more than 1 trade in future
                if lto_dict[tradeid]['action'] == 'cancel':
                    # TODO: 'cancel' action currently only used for enter phase, exit phase cancel can be added
                    # (This requires other updates for TEST)
                    # TODO: DEPLOY: Binance cancel the order
                    lto_dict[tradeid]['status'] = 'closed'
                    lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])

                    # TEST: Update df_balance
                    # No need to check the enter type because lto do not contain 'market'. It only contains 'limit'
                    df_balance.loc[self.quote_currency,'free'] += lto_dict[tradeid]['enter']['limit']['amount']
                    df_balance.loc[self.quote_currency,'locked'] -= lto_dict[tradeid]['enter']['limit']['amount']
            
                elif lto_dict[tradeid]['action'] == 'update':
                    pass
                
                elif lto_dict[tradeid]['action'] == 'market_enter':
                    pass
                
                elif lto_dict[tradeid]['action'] == 'market_exit':
                    # TODO: DEPLOY: Execute Market Order in Bnance

                    lto_dict[tradeid]['status'] = 'closed'
                    lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])
                    lto_dict[tradeid]['result']['cause'] = 'exit_expire'
                    last_kline = data_dict[lto_dict[tradeid]['pair']]['15m'].tail(1)

                    # NOTE: TEST: Simulation of the market sell is normally the open price of the future candle,
                    #             For the sake of simplicity closed price of the last candle is used in the market sell
                    #             by assumming that the 'close' price is pretty close to the 'open' of the future

                    lto_dict[tradeid]['result']['exit']['type'] = 'market'
                    lto_dict[tradeid]['result']['exit']['time'] = bson.Int64(last_kline.index.values)
                    lto_dict[tradeid]['result']['exit']['price'] = float(last_kline['close'])
                    lto_dict[tradeid]['result']['exit']['quantity'] = lto_dict[tradeid]['exit']['market']['quantity']
                    lto_dict[tradeid]['result']['exit']['amount'] = lto_dict[tradeid]['result']['exit']['price'] * lto_dict[tradeid]['result']['exit']['quantity']

                    lto_dict[tradeid]['result']['profit'] = lto_dict[tradeid]['result']['exit']['amount'] - lto_dict[tradeid]['result']['enter']['amount']

                    # Update df_balance: write the amount of the exit
                    df_balance.loc[self.quote_currency,'free'] += lto_dict[tradeid]['result']['exit']['amount']
                    df_balance.loc[self.quote_currency,'total'] = df_balance.loc[self.quote_currency,'free'] + df_balance.loc[self.quote_currency,'locked']
                    df_balance.loc[self.quote_currency,'ref_balance'] = df_balance.loc[self.quote_currency,'total']
                    # NOTE: For the quote_currency total and the ref_balance is the same
                    # TODO: Add enter and exit times to result section and remove from enter and exit items. Evalutate liveTime based on that
                    pass
            
                elif lto_dict[tradeid]['action'] == 'execute_exit':
                    # If the enter is successfull and the algorithm decides to execute the exit order
                    # TODO: DEPLOY: Place the exit order to Binance: oco or limit
                    #       No need to fill anything in 'result' or 'exit' sections.

                    lto_dict[tradeid]['status'] = 'open_exit'
                    lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])
                    pass

                # Postpone can be for the enter or the exit phase
                elif lto_dict[tradeid]['action'] == 'postpone':
                    if lto_dict[tradeid]['status'] == 'enter_expire':
                        lto_dict[tradeid]['status'] = 'open_enter'
                        lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])

                    elif lto_dict[tradeid]['status'] == 'exit_expire':
                        lto_dict[tradeid]['status'] = 'open_exit'
                        lto_dict[tradeid]['history'].append(lto_dict[tradeid]['status'])
                        pass
                    else: pass

                # Delete the action, after the action is taken
                del lto_dict[tradeid]['action']

        return lto_dict, df_balance


    async def _execute_nto(self, trade_dict, df_balance):
        """
        for to in trade_dict:
            1. open_enter
                a. market
                    - Get the 'result'
                b. limit
            2. partially_closed_enter
                -
            3. open_exit
                a. market
                    - Get the 'result'
                b. limit
                c. oco
            4. partially_closed_exit
            -

        Args:
            trade_dict (dict): [description]
            df_balances (pd.DataFrame): [description]

        Returns:
            [type]: [description]
        """
        for key in trade_dict.keys():
            # NOTE: The status values other than 'open_enter' is here for lto update
            if trade_dict[key]['status'] == 'open_enter':
                
                if 'market' in trade_dict[key]['enter'].keys():
                    # NOTE: Since there is no risk evaluation in the market enter, It is not planned to be implemented
                    pass

                elif 'limit' in trade_dict[key]['enter'].keys():
                    # NOTE: In live-trading tradeid's are gathered from the broker and it is unique. Here it is set to a unique
                    #       timestamp values

                    trade_dict[key]['tradeid'] = int(time.time() * 1000) 
                    df_balance.loc[self.quote_currency,'free'] -= trade_dict[key]['enter']['limit']['amount']
                    df_balance.loc[self.quote_currency,'locked'] += trade_dict[key]['enter']['limit']['amount']

                else: pass # TODO: Internal Error

            else: pass # TODO: Internal Error
        return trade_dict, df_balance


    async def execute_decision(self, trade_dict, df_balance, lto_dict, data_dict):
        """
        'execute_decision' method is responsible for
            - execute new to's
            - execute lto updates
                - Strategy do not update the status. It creates the 'action' and the execute_decision update the status
            - update the df_balance

        TestBinanceWrapper: In test sessions, executing a trade_object means
        changing the df_balance columns 'free' and 'locked' when a trade is
        started

        Execution Logic:
        1. Execute live_trade_objects
        2. Execute new_trade_objects

        Args:
            trade_dict (dict): [description]
            df_balances (pd.DataFrame): [description]

        Returns:
            tuple: result, df_balances
        """
        result = True

        # Execute decsisions about ltos
        lto_dict, df_balance = await self._execute_lto(lto_dict, df_balance, data_dict)

        # Execute new trade objects
        trade_dict, df_balance = await self._execute_nto(trade_dict, df_balance)      
            
        # TODO: HIGH: TEST: In the execute section commission needs to be evaluated. This section should behave
        #       exactly as the broker. 
        # NOTE: As a result the equity will be less than evaluated since the comission has been cut.

        # TODO: Consider returning trade_dict, because:
        #   - orders may not be accepted by the broker
        #       - In this case this side where to handle the issue: here or the main script
        #   - market sell causes instant fill
        #   - market enter causes instant fill

        return result, df_balance, lto_dict