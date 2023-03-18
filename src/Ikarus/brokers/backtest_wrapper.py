from ..exceptions import NotImplementedException
from asyncio.tasks import gather
from binance.exceptions import BinanceAPIException
from binance.enums import *
from .. import notifications
import asyncio
import pandas as pd
import logging
import json
import bson
import time
import copy
from ..utils import time_scale_to_second, get_min_scale, time_scale_to_milisecond, \
    safe_multiply, safe_divide, round_to_period
from .. import balance_manager
import more_itertools
from ..objects import OCO, ECause, ECommand, EState, Limit, Market, trade_to_dict
from abc import ABC, abstractmethod
from .. import binance_filters
import os
from collections import defaultdict

logger = logging.getLogger('app')

# This variable added as deus ex machina
symbol_info = None

class BacktestWrapper():

    kline_column_names = ["open_time", "open", "high", "low", "close", "volume", "close_time","quote_asset_volume", 
                        "num_of_trades", "taker_buy_base_ast_vol", "taker_buy_quote_ast_vol", "ignore"]

    df_tickers = None
    fee_rate = 0
    def __init__(self, _client, _config):

        self.client = _client
        self.config = _config
        logger.info('creating an instance of {}'.format(__name__))

        # Set reference currencies
        self.quote_currency = _config['broker']['quote_currency']
        BacktestWrapper.fee_rate = _config['broker']['fee_rate']

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
                   for b in last_observer_item['data'] if float(b['free']) > 0 or float(b['locked']) > 0 or b['asset']==self.config['broker']['quote_currency'] ]
        # NOTE: Make sure that quote_currency stays in the df_balance even if it is 0

        df_balance = pd.DataFrame(balance)
        df_balance.set_index(['asset'], inplace=True)
        df_balance = df_balance.astype(float)
        df_balance['total'] = df_balance['free'] + df_balance['locked']

        return df_balance


    async def get_all_tickers(self):
        """
        Get all possible tickers

        Returns:
            pd.DataFrame: tickers
        """       

        #f = open('tickers.json','r')
        #tickers_json = json.load(f)
        #tickers = tickers_json['tickers']
        #df = pd.DataFrame(tickers)

        df = pd.DataFrame(await self.client.get_all_tickers())
        df.set_index('symbol', inplace=True)
        df.astype(float)
        return df


    async def get_all_symbol_info(self, all_pairs):
        global symbol_info
        all_info = await self.client.get_exchange_info()

        selected_info = {}
        for item in all_info['symbols']:
            if item['symbol'] in all_pairs:
                selected_info[item['symbol']] = item

        symbol_info =selected_info
        return selected_info


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
        '''
        # Add current prices to df_balance
        price = [float(TestBinanceWrapper.df_tickers.loc[pair]['price'])
                 if pair != self.quote_currency
                 else 1
                 for pair in df_balance['pair']]
        df_balance['price'] = price

        # Evaluate the equity in terms of quote_currency
        #df_balance['ref_balance'] = df_balance['price'] * df_balance['total']
        '''
        return df_balance

    async def get_data_dict_from_file(self, pairs, time_df, df_list):
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
        
        return do_dict


    async def get_data_dict(self, meta_data_pool, ikarus_time):
        """
        meta_do = [('1m', 'BTCUSDT'), ('15m', 'BTCUSDT'), ('15m', 'XRPUSDT')]
        (time_scale, pair)
        length = meta_do['time_scale']
        """

        tasks_klines_scales = []
        for meta_data in meta_data_pool:

            if type(ikarus_time) == int:
                # NOTE: If you need exactly 720 candles not 719 (unclosed (last) candle removed) then push hist_data_start_time back 1 step
                # NOTE: The cause of +1 comes from the desire to not the make hist_data_start_time an exact minute, Because when it is an exact 1m or 15m, 1 extra hist_kline is retrived addi
                hist_data_start_time = ikarus_time - time_scale_to_second(meta_data[0]) * (self.config['time_scales'][meta_data[0]][1]) * 1000 + 1 # ms = start_time + x sec * y-1 times * 1000
            else:
                raise NotImplementedException('start_time is not integer')

            tasks_klines_scales.append(asyncio.create_task(self.client.get_historical_klines(meta_data[1], meta_data[0], start_str=hist_data_start_time, end_str=ikarus_time )))

        composit_klines = list(await asyncio.gather(*tasks_klines_scales, return_exceptions=True))
        # TODO: NEXT: BUG: If a pair does not exist in the given time, then composit kline comes empty: [[], [[...], [...]]
        data_dict = await self.decompose(meta_data_pool, composit_klines)

        return data_dict


    async def download_all_data(self, meta_data_pool, session_start_time, session_end_time):
        """
        meta_data_pool = [('1m', 'BTCUSDT'), ('15m', 'BTCUSDT'), ('15m', 'XRPUSDT')]
        length = meta_do['time_scale']
        """
        tasks_klines_scales = []
        for meta_data in meta_data_pool:
            if type(session_start_time) == int:
                # NOTE: -1 added due to fix the difference between the gathering methods between BinanceWrapper and the TestBinanceWrapper. 
                hist_data_start_time = session_start_time - time_scale_to_second(meta_data[0]) * (self.config['time_scales'][meta_data[0]]) * 1000 + 1 # ms = start_time + x sec * y times * 1000
            else:
                raise NotImplementedException('start_time is not integer')

            tasks_klines_scales.append(asyncio.create_task(self.client.get_historical_klines(meta_data[1], meta_data[0], start_str=hist_data_start_time, end_str=session_end_time )))
        composit_klines = list(await asyncio.gather(*tasks_klines_scales, return_exceptions=True))
        downloaded_data = await self.decompose(meta_data_pool, composit_klines)
        logger.debug('download ended')

        return downloaded_data
    

    async def obtain_candlesticks(self, meta_data_pool, session_start_time, session_end_time):
        not_found_meta_data_pool, data_dict = self.load_candlesticks(meta_data_pool, session_start_time, session_end_time)
        
        if not_found_meta_data_pool:
            downloaded_data = await self.download_all_data(not_found_meta_data_pool, session_start_time, session_end_time)

            # Only save the candlesticks of not_found_meta_data_pool
            for nfmt in not_found_meta_data_pool:
                data_dict[nfmt[1]][nfmt[0]] = downloaded_data[nfmt[1]][nfmt[0]]
            
            # TODO: Cover the cases where the data is not properly downloaded
            self.save_candlesticks(not_found_meta_data_pool, downloaded_data, session_start_time, session_end_time)

        self.downloaded_data = data_dict

    
    def save_candlesticks(self, meta_data_pool, downloaded_data, session_start_time, session_end_time):

        filename_template = '{}-{}-{}-{}.csv'
        for meta_data in meta_data_pool:
            filename = filename_template.format(meta_data[1], meta_data[0], session_start_time, session_end_time)
            downloaded_data[meta_data[1]][ meta_data[0]].to_csv(filename)
            logger.debug(f'File saved: {filename}')


    def load_candlesticks(self, meta_data_pool, session_start_time, session_end_time):
        filename_template = '{}-{}-{}-{}.csv'
        recursive_dict = lambda: defaultdict(recursive_dict)
        data_dict = recursive_dict()
        
        not_found_meta_data = []
        for meta_data in meta_data_pool:
            filename = filename_template.format(meta_data[1], meta_data[0], session_start_time, session_end_time)

            if not os.path.isfile(filename):
                not_found_meta_data.append(meta_data)
                logger.debug(f'File cannot be loaded: {filename}')
                continue
            
            data_dict[meta_data[1]][meta_data[0]] = pd.read_csv(filename, index_col=0)
            logger.debug(f'File loaded: {filename}')
        
        return not_found_meta_data, data_dict


    async def get_data_dict_download(self, meta_data_pool, ikarus_time):
        """
        meta_do = [('1m', 'BTCUSDT'), ('15m', 'BTCUSDT'), ('15m', 'XRPUSDT')]
        (time_scale, pair)
        length = meta_do['time_scale']
        """
        tasks_klines_scales = []
        data_dict = {}
        for meta_data in meta_data_pool:

            if type(ikarus_time) == int:
                # NOTE: If you need exactly 720 candles not 719 (unclosed (last) candle removed) then push hist_data_start_time back 1 step
                # NOTE: The cause of +1 comes from the desire to not the make hist_data_start_time an exact minute, Because when it is an exact 1m or 15m, 1 extra hist_kline is retrived addi
                hist_data_end_time = ikarus_time - time_scale_to_second(meta_data[0]) * 1000
                hist_data_start_time = ikarus_time - time_scale_to_second(meta_data[0]) * (self.config['time_scales'][meta_data[0]]) * 1000 + 1 # ms = start_time + x sec * y times * 1000 + 1
                if not meta_data[1] in data_dict.keys():
                    data_dict[meta_data[1]] = dict()

                data_dict[meta_data[1]][meta_data[0]] = self.downloaded_data[meta_data[1]][meta_data[0]].loc[hist_data_start_time:hist_data_end_time]
            else:
                raise NotImplementedException('start_time is not integer')

        return data_dict


    async def get_historical_klines(self, start_time, end_time, pair, time_scale):

        hist_klines = await self.client.get_historical_klines(pair, time_scale, start_str=start_time, end_str=end_time )
        df = pd.DataFrame(hist_klines, columns=BacktestWrapper.kline_column_names)
        df = df.set_index(['open_time'])
        df = df.astype(float)
        return df


    async def decompose(self, meta_data_pool, composit_klines):

        logger.debug("decompose started")
        do_dict = dict()
        for idx, meta_data in enumerate(meta_data_pool):
            
            if not meta_data[1] in do_dict.keys():
                do_dict[meta_data[1]] = dict()
            
            df = pd.DataFrame(composit_klines[idx], columns=BacktestWrapper.kline_column_names)
            df = df.set_index(['open_time'])
            # NOTE: WARNING: Be aware that the last line is removed to not to affect analysis
            #       Since it requires closed candles.
            if composit_klines[idx] != []:
                df.drop(df.index[-1], inplace=True)
            df = df.astype(float)
            do_dict[meta_data[1]][meta_data[0]] = df

        logger.debug("decompose ended")
        return do_dict


    def execute_cancel(self, trade, df_balance) -> bool:
        if trade.status in [EState.OPEN_ENTER, EState.ENTER_EXP] : # NOTE: REFACTORING: EState.CLOSED was here as well
            return balance_manager.cancel_enter_order(df_balance, self.quote_currency, trade.enter)
        elif trade.status in [EState.EXIT_EXP, EState.OPEN_EXIT]:
            base_cur = trade.pair.replace(self.config['broker']['quote_currency'],'')
            return balance_manager.cancel_exit_order(df_balance, base_cur, trade.exit)
        logger.warning(f'execute_cancel failed for trade:{trade_to_dict(trade)}')
        return False


    def execute_buy(self, trade, df_balance):
        if balance_manager.place_enter_order(df_balance, self.quote_currency, trade.enter):
            trade.enter.orderId = int(time.time() * 1000) # Get the order id from the broker
            trade.status = EState.OPEN_ENTER
            return True
        logger.warning(f'execute_buy failed for trade:{trade_to_dict(trade)}')
        return False


    def execute_sell(self, trade, df_balance):
        base_cur = trade.pair.replace(self.quote_currency,'')
        if balance_manager.place_exit_order(df_balance, base_cur, trade.exit):
            trade.status = EState.OPEN_EXIT
            trade.exit.orderId = int(time.time() * 1000)
            return True
        logger.warning(f'execute_sell failed for trade:{trade_to_dict(trade)}')
        return False


    def _execute_lto(self, trade_list, df_balance):
        for i in range(len(trade_list)):
            if trade_list[i].command == ECommand.CANCEL:

                if self.execute_cancel(trade_list[i], df_balance):
                    trade_list[i].status = EState.CLOSED
                    trade_list[i].reset_command()
                
            elif trade_list[i].command == ECommand.UPDATE:
                # First cancel, then place the new order
                # Cancel the order
                if self.execute_cancel(trade_list[i], df_balance):
                    '''
                    No need to check the error case because if the order could not be placed due to some reason,
                    there is no way other then retry. Status will stay like 'STAT_EXIT_EXP', lto_update will not do anything,
                    strategy will create a new update action and send it here in the next cycle
                    '''
                    # Place the order
                    is_success = self.execute_sell(trade_list[i], df_balance)
                    if is_success:
                        trade_list[i].reset_command()

                else:
                    '''
                    If the cancel failed, then the exit orders are still there.
                    So do not create new order and keep the status as exit_expired
                    '''
                    pass
                pass

            elif trade_list[i].command == ECommand.EXEC_EXIT:
                # If the enter is successful and the algorithm decides to execute the exit order

                is_success = self.execute_sell(trade_list[i], df_balance)
                if is_success:
                    trade_list[i].reset_command()


    def _execute_nto(self, new_trades, df_balance):

        for i in range(len(new_trades)):

            if new_trades[i].command == ECommand.NONE:
                continue

            if self.execute_buy(new_trades[i], df_balance): 
                new_trades[i].command = ECommand.NONE
            else:
                new_trades[i] = None

    def execute_decision(self, new_trades, df_balance, live_trades):
        # Execute decsisions about ltos
        self._execute_lto(live_trades, df_balance)

        # Execute new trade objects
        self._execute_nto(new_trades, df_balance)


async def sync_trades_of_backtest(trade_list, data_dict, strategy_period_mapping, df_balance, quote_currency):
    global symbol_info
    # NOTE: Only get the related LTOs and ONLY update the related LTOs. Doing the same thing here is pointless.
    for i in range(len(trade_list)):
        pair = trade_list[i].pair

        strategy_min_scale = strategy_period_mapping[trade_list[i].strategy]
        last_kline = data_dict[pair][strategy_min_scale].tail(1)
        last_closed_candle_open_time = bson.Int64(last_kline.index.values[0])
        base_cur = pair.replace(quote_currency,'')

        if trade_list[i].status == EState.OPEN_ENTER:
            # NOTE: There is 2 method to enter: TYPE_LIMIT and TYPE_MARKET. Since market executed directly, it is not expected to have market at this stage
            if type(trade_list[i].enter) == Limit:

                # Check if the open enter trade is filled else if the trade is expired
                if float(last_kline['low']) < trade_list[i].enter.price:                    
                    trade_list[i].set_result_enter(last_closed_candle_open_time, fee_rate=BacktestWrapper.fee_rate)
                    if not balance_manager.buy(df_balance, quote_currency, base_cur, trade_list[i]):
                        logger.error(f"Function failed: balance_manager.buy().")
                        # TODO: Fix the logic. The balance manager should be called prior

                elif int(trade_list[i].enter.expire) <= last_closed_candle_open_time:
                    trade_list[i].status = EState.ENTER_EXP
                    # NOTE: No update on command because it is, only placed by the strategies

            elif type(trade_list[i].enter) == Market:

                # NOTE: Market order execution is a bit tricky. Since strategy only decides the amount
                # for the market buy orders

                market_order_qty = safe_divide(trade_list[i].enter.amount, float(last_kline['open']))
                market_order_qty = binance_filters.lot_size(market_order_qty, symbol_info[trade_list[i].pair])
                trade_list[i].set_result_enter( last_closed_candle_open_time, 
                    price=float(last_kline['open']),
                    quantity=market_order_qty,
                    fee_rate=BacktestWrapper.fee_rate)

                if not balance_manager.buy(df_balance, quote_currency, base_cur, trade_list[i]):
                    logger.error(f"Function failed: balance_manager.buy().")

            else:
                # TODO: Internal Error
                pass

        elif trade_list[i].status == EState.OPEN_EXIT:

            if type(trade_list[i].exit) == Limit:

                # Check if the open sell trade is filled or stoploss is taken
                if float(last_kline['high']) > trade_list[i].exit.price:

                    trade_list[i].set_result_exit(last_closed_candle_open_time, 
                        fee_rate=BacktestWrapper.fee_rate, 
                        cause=ECause.LIMIT)
                    base_cur = pair.replace(quote_currency,'')
                    if not balance_manager.sell(df_balance, quote_currency, base_cur, trade_list[i]):
                        logger.error(f"Function failed: balance_manager.sell().")
                        # TODO: Fix the logic. The balance manager should be called prior

                elif int(trade_list[i].exit.expire) <= last_closed_candle_open_time:
                    trade_list[i].status = EState.EXIT_EXP


            elif type(trade_list[i].exit) == OCO:
                # NOTE: Think about the worst case and check the stop loss first.

                if float(last_kline['low']) < trade_list[i].exit.stop_price:
                    # Stop Loss takens
                    trade_list[i].set_result_exit(last_closed_candle_open_time,
                        cause=ECause.STOP_LIMIT,
                        price=trade_list[i].exit.stop_limit_price,
                        fee_rate=BacktestWrapper.fee_rate)

                    base_cur = pair.replace(quote_currency,'')
                    balance_manager.sell(df_balance, quote_currency, base_cur, trade_list[i])
                
                elif float(last_kline['high']) > trade_list[i].exit.price:
                    # Limit taken
                    trade_list[i].set_result_exit(last_closed_candle_open_time,
                        fee_rate=BacktestWrapper.fee_rate,
                        cause=ECause.LIMIT)

                    base_cur = pair.replace(quote_currency,'')
                    if not balance_manager.sell(df_balance, quote_currency, base_cur, trade_list[i]):
                        logger.error(f"Function failed: balance_manager.sell().")
                        # TODO: Fix the logic. The balance manager should be called prior

                elif int(trade_list[i].exit.expire) <= last_closed_candle_open_time:
                    trade_list[i].status = EState.EXIT_EXP

                else:
                    pass


            elif type(trade_list[i].exit) == Market:

                # NOTE: Market order execution is a bit tricky. Since strategy only decides the quantity
                # for the market sell orders

                trade_list[i].set_result_exit( last_closed_candle_open_time, 
                    price=float(last_kline['open']),
                    fee_rate=BacktestWrapper.fee_rate,
                    cause=ECause.MARKET)
                if not balance_manager.sell(df_balance, quote_currency, base_cur, trade_list[i]):
                    logger.error(f"Function failed: balance_manager.sell().")

            else:
                # TODO: Internal Error
                pass

        else:
            # TODO: Internal Error
            pass