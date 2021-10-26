from Ikarus.strategies.StrategyBase import StrategyBase
from Ikarus.exceptions import NotImplementedException
from asyncio.tasks import gather
from binance.exceptions import BinanceAPIException
from binance.enums import *
from Ikarus.enums import *
from Ikarus import notifications
import asyncio
import pandas as pd
import logging
import json
import bson
import time
from itertools import chain, groupby
import copy
from .utils import time_scale_to_second, get_min_scale, calculate_fee, time_scale_to_milisecond, get_lto_phase
from . import balance_manager

class BinanceWrapper():

    kline_column_names = ["open_time", "open", "high", "low", "close", "volume", "close_time","quote_asset_volume", 
                        "nbum_of_trades", "taker_buy_base_ast_vol", "taker_buy_quote_ast_vol", "ignore"]

    def __init__(self, _client, _config, _telbot):
        # TODO: Think about the binance.exceptions.BinanceAPIException: APIError(code=-1021): Timestamp for this request was 1000ms ahead of the server's time.
        #       The alternative slution (the wrapper for the binane client can be added to here):
        #       https://github.com/sammchardy/python-binance/issues/249

        self.client = _client
        self.config = _config
        self.telbot = _telbot
        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.logger.info('creating an instance of {}'.format(__name__))

        # Set reference currencies
        self.quote_currency = _config['broker']['quote_currency']
        self.credit_currency = _config['broker']['credit_currency']
        self.pricePrecision = 8
        # TODO: get the precision from symbol info and use it in the orders

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

        '''
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
        '''
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


    async def get_all_symbol_info(self, all_pairs):
        all_info = await self.client.get_exchange_info()

        selected_info = {}
        for item in all_info['symbols']:
            if item['symbol'] in all_pairs:
                selected_info[item['symbol']] = item

        return selected_info


    async def get_current_balance(self):

        df_balance, df_tickers = await asyncio.gather(
            self.get_info(),
            self.get_all_tickers()
        )

        # Add current prices to df_balance
        #price = [float(df_tickers.loc[pair]['price'])
        #         if pair != self.quote_currency
        #         else 1
        #         for pair in df_balance['pair']]
        '''
        price = []
        for pair in df_balance['pair']:
            if pair == "USDTBTC":
                print("HERE")
            if pair != self.quote_currency:
                price.append(float(df_tickers.loc[pair]['price']))
            else:
                price.append(1)

        df_balance['price'] = price

        # Evaluate the equity in terms of quote_currency
        df_balance['ref_balance'] = df_balance['price'] * df_balance['total']
        '''
        return df_balance


    async def get_data_dict(self, meta_data_pool, ikarus_time):
        """
        meta_do = [('1m', 'BTCUSDT'), ('15m', 'BTCUSDT'), ('15m', 'XRPUSDT')]
        (time_scale, pair)
        length = meta_do['time_scale']
        """
        self.logger.debug('get_data_dict started')
        tasks_klines_scales = []
        for meta_data in meta_data_pool:

            if type(ikarus_time) == int:
                # NOTE: If you need exactly 720 candles not 719 (unclosed (last) candle removed) then push hist_data_start_time back 1 step
                # NOTE: The cause of +1 comes from the desire to not the make hist_data_start_time an exact minute, Because when it is an exact 1m or 15m, 1 extra hist_kline is retrived addi
                hist_data_start_time = ikarus_time - time_scale_to_second(meta_data[0]) * (self.config['time_scales'][meta_data[0]][1]) * 1000 + 1 # ms = start_time + x sec * y times * 1000 + 1
            else:
                raise NotImplementedException('start_time is not integer')

            tasks_klines_scales.append(asyncio.create_task(self.client.get_historical_klines(meta_data[1], meta_data[0], start_str=hist_data_start_time, end_str=ikarus_time )))

        composit_klines = list(await asyncio.gather(*tasks_klines_scales, return_exceptions=True))
        data_dict = await self.decompose(meta_data_pool, composit_klines)
        self.logger.debug('get_data_dict ended')

        # TODO: Length check for Data dict items could help a lot to detect anomalies
        return data_dict


    async def decompose(self, meta_data_pool, composit_klines):

        self.logger.debug("decompose started")
        do_dict = dict()
        for idx, meta_data in enumerate(meta_data_pool):
            
            if not meta_data[1] in do_dict.keys():
                do_dict[meta_data[1]] = dict()
            
            df = pd.DataFrame(composit_klines[idx], columns=BinanceWrapper.kline_column_names)
            df = df.set_index(['open_time'])
            # NOTE: WARNING: Be aware that the last line is removed to not to affect analysis, since it requires closed candles.
            df.drop(df.index[-1], inplace=True)
            df = df.astype(float)

            if len(df) != int(self.config['time_scales'][meta_data[0]][1]-1):
                self.logger.warn(f"Missing historical candle for {meta_data[1]} {meta_data[0]}: {len(df)} instead of {self.config['time_scales'][meta_data[0]][1]-1}")

            do_dict[meta_data[1]][meta_data[0]] = df

        self.logger.debug("decompose ended")
        return do_dict


    async def get_data_dict_old(self, pairs, time_df):
        """
        This functions returns the historical kline values in the data_dict format.

        Args:
            pairs (list): [description]
            time_df (pd.DataFrame): [description]

        Returns:
            dict: [description]
        """
        self.logger.debug('get_data_dict started')

        tasks_klines_scales = []
        for pair in pairs:
            for index, row in time_df.iterrows():
                tasks_klines_scales.append(asyncio.create_task(self.client.get_historical_klines(pair, row["scale"], start_str="{} ago UTC".format(row["length_str"]))))

        #composit_klines = await self.client.get_historical_klines(pair, row["scale"], start_str="{} ago UTC".format(row["length_str"]))
        composit_klines = list(await asyncio.gather(*tasks_klines_scales, return_exceptions=True))

        data_dict = await self.decompose(pairs, time_df, composit_klines)

        # NOTE: Keep in mind that the last row is the current candle that has not been completed
        self.logger.debug('get_data_dict ended')
        return data_dict


    async def get_lto_orders(self, lto_list):
        """
        This functions gathers the corresponding order objects of LTOs from the brokers
        
        If the status is STAT_OPEN_EXIT, then open enter is taken and no need to get the enter order.
        Thus, the order gathering logic, checks the state and decides which orders to be gathered such as:
        limit enter or limit exit or oco_limit exit andoco_stoploss exit. Whatever that is not gathered should already be FILLED

        Args:
            lto_list (list): [description]

        Returns:
            list: lto_list
        """
        self.logger.debug('get_lto_orders started')

        # Check the status of LTOs:
        coroutines = []
        for lto in lto_list:
            lto_phase = get_lto_phase(lto)
            if lto_phase == PHASE_ENTER:
                coroutines.append(self.client.get_order(symbol=lto['pair'], orderId=lto['enter'][TYPE_LIMIT]['orderId']))

            elif lto_phase == PHASE_EXIT:
                if self.config['strategy'][lto['strategy']]['exit']['type'] == TYPE_LIMIT:
                    coroutines.append(self.client.get_order(symbol=lto['pair'], orderId=lto['exit'][TYPE_LIMIT]['orderId']))
                elif self.config['strategy'][lto['strategy']]['exit']['type'] == TYPE_OCO:
                    coroutines.append(self.client.get_order(symbol=lto['pair'], orderId=lto['exit'][TYPE_OCO]['orderId']))
                    coroutines.append(self.client.get_order(symbol=lto['pair'], orderId=lto['exit'][TYPE_OCO]['stopLimit_orderId']))
            else: pass

        lto_orders_dict = {}
        if len(coroutines):
            for order in list(await asyncio.gather(*coroutines)):
                lto_orders_dict[order['orderId']] = order
        
        self.logger.debug('get_lto_orders started')

        return lto_orders_dict


    async def _execute_oco_sell(self, lto):
        try:
            response = await self.client.create_oco_order(
                symbol=lto['pair'],
                side=SIDE_SELL,
                quantity=lto['exit'][TYPE_OCO]['quantity'],
                price=f'%.{self.pricePrecision}f' % lto['exit'][TYPE_OCO]['limitPrice'],
                stopPrice=f'%.{self.pricePrecision}f' % lto['exit'][TYPE_OCO]['stopPrice'],
                stopLimitPrice=f'%.{self.pricePrecision}f' % lto['exit'][TYPE_OCO]['stopLimitPrice'],
                stopLimitTimeInForce=TIME_IN_FORCE_GTC)

            if response['orderReports'][0]['status'] != 'NEW' or response['orderReports'][1]['status'] != 'NEW': raise Exception('Response status is not "NEW"')

        except Exception as e:
            self.logger.error(f"{lto['strategy']} - {lto['pair']}: {e}")
            # TODO: Notification: ERROR
            return lto

        else:
            response_stoploss, response_limit_maker = response["orderReports"][0], response["orderReports"][1]
            self.logger.info(f'LTO "{lto["_id"]}": "{response_limit_maker["side"]}" "{response_limit_maker["type"]}" order placed: {response_limit_maker["orderId"]}')
            self.logger.info(f'LTO "{lto["_id"]}": "{response_stoploss["side"]}" "{response_stoploss["type"]}" order placed: {response_stoploss["orderId"]}')

            lto['exit'][TYPE_OCO]['orderId'] = response_limit_maker['orderId']
            lto['exit'][TYPE_OCO]['stopLimit_orderId'] = response_stoploss['orderId']

            lto['status'] = STAT_OPEN_EXIT
            lto['history'].append(lto['status'])
            self.telbot.send_constructed_msg('lto', *[lto['_id'], lto['strategy'], lto['pair'], 'exit', response_limit_maker["orderId"], EVENT_PLACED])

            return lto


    async def _execute_limit_sell(self, lto):
        try:
            response = await self.client.order_limit_sell(
                symbol=lto['pair'],
                quantity=lto['exit'][TYPE_LIMIT]['quantity'],
                price=f'%.{self.pricePrecision}f' % lto['exit'][TYPE_LIMIT]['price'])

            if response['status'] != 'NEW': raise Exception('Response status is not "NEW"')

        except Exception as e:
            self.logger.error(f"{lto['strategy']} - {lto['pair']}: {e}")
            # TODO: Notification: ERROR
            return lto

        else:
            self.logger.info(f'LTO "{lto["_id"]}": "{response["side"]}" "{response["type"]}" order placed: {response["orderId"]}')
            lto['exit'][TYPE_LIMIT]['orderId'] = response['orderId']

            lto['status'] = STAT_OPEN_EXIT
            lto['history'].append(lto['status'])
            self.telbot.send_constructed_msg('lto', *[lto['_id'], lto['strategy'], lto['pair'], 'exit', response["orderId"], EVENT_PLACED])
            return lto


    async def _execute_cancel(self, lto):
        try:
            phase = get_lto_phase(lto)
            type = self.config['strategy'][lto['strategy']][phase]['type']
            response = await self.client.cancel_order(
                symbol=lto['pair'],
                orderId=lto[phase][type]['orderId'])

        except Exception as e:
            self.logger.error(f"{lto['strategy']} - {lto['pair']}: {e}")
            # TODO: Notification: ERROR
            return False

        else:
            if phase == PHASE_EXIT and type == TYPE_OCO:
                response_stoploss, response_limit_maker = response['orderReports'][0], response['orderReports'][1]
                self.logger.info(f'LTO "{lto["_id"]}": "{response_stoploss["side"]}" "{response_stoploss["type"]}" order canceled: {response_stoploss["orderId"]}')
                self.logger.info(f'LTO "{lto["_id"]}": "{response_limit_maker["side"]}" "{response_limit_maker["type"]}" order canceled: {response_limit_maker["orderId"]}')
                self.telbot.send_constructed_msg('lto', *[lto['_id'], phase, response_limit_maker["orderId"], 'canceled'])

            else:
                self.logger.info(f'LTO "{lto["_id"]}": "{response["side"]}" "{response["type"]}" order canceled: {response["orderId"]}')
                self.telbot.send_constructed_msg('lto', *[lto['_id'], lto['strategy'], lto['pair'], phase, response["orderId"], 'canceled'])
            return True


    async def _execute_lto(self, lto_list):
        """
        The errors during execution of exit orders will left the status:
        STAT_WAITING_EXIT 
            write_updated_ltos_to_db will write the status to db,
            strategy will add the action ACTN_EXEC_EXIT so that LTO will be executed again

        STAT_EXIT_EXP:
            write_updated_ltos_to_db will write the status to db,
            strategy will add the action ACTN_UPDATE or ACTN_MARKET_EXIT, so that LTO will be executed again

        Args:
            lto_list (list): [description]

        Returns:
            tuple: lto_dict
        """
        for i in range(len(lto_list)):
            if 'action' in lto_list[i].keys():
                self.logger.info(f"Handling action: \"{lto_list[i]['action']}\" for lto: \"{lto_list[i]['_id']}\"")
                if lto_list[i]['action'] == ACTN_CANCEL:
                    # NOTE: Assuming that the phase: enter
                    if await self._execute_cancel(lto_list[i]): # Close the LTO if the enter order canceled
                        lto_list[i]['status'] = STAT_CLOSED
                        lto_list[i]['history'].append(lto_list[i]['status'])

                elif lto_list[i]['action'] == ACTN_UPDATE:
                    '''
                    ACTN_UPDATE can only exist in the exit phase, thus no check for status
                    '''
                    exit_type = self.config['strategy'][lto_list[i]['strategy']][PHASE_EXIT]['type']
                    # Cancel the order
                    if await self._execute_cancel(lto_list[i]):
                        '''
                        No need to check the error case because if the order could not be placed due to some reason,
                        there is no way other then retry. Status will stay like 'STAT_EXIT_EXP', lto_update will not do anything,
                        strategy will create a new update action and send it here in the next cycle
                        '''
                        # Place the order
                        if exit_type == TYPE_OCO:
                            lto_list[i] = await self._execute_oco_sell(lto_list[i])
                        elif exit_type == TYPE_LIMIT:
                            lto_list[i] = await self._execute_limit_sell(lto_list[i])
                    else:
                        '''
                        If the cancel failed, then the exit orders are still there.
                        So do not create new order and keep the status as exit_expired
                        '''
                        pass

                elif lto_list[i]['action'] == ACTN_MARKET_ENTER:
                    pass

                elif lto_list[i]['action'] == ACTN_MARKET_EXIT:
                    
                    try:
                        raise Exception('Market Exit is not supported')
                        response = await self.client.order_market_sell(
                            symbol=lto_list[i]['pair'],
                            quantity=lto_list[i]['pair']) # TODO: left with typo to not to execute

                    except Exception as e:
                        self.logger.error(f"{lto_list[i]['strategy']} - {lto_list[i]['pair']}: {e}")
                        # TODO: Notification

                    else:
                        # TODO: Integrate commissions for BNB not only the quote currency
                        lto_list[i]['status'] = STAT_CLOSED
                        lto_list[i]['history'].append(lto_list[i]['status'])
                        lto_list[i]['result']['cause'] = STAT_EXIT_EXP
                        lto_list[i]['exit'][TYPE_MARKET]['orderId'] = response['orderId']

                        lto_list[i]['result']['exit']['type'] = TYPE_MARKET

                        # TODO: Multiple time scale is not supported
                        raise Exception('Fix the current time issue')
                        current_time = int(response['transactTime']/1000)                                               # exact second
                        current_time -= (current_time % 60)                                                             # exact minute
                        current_time -= (current_time % (self.config['data_input']['scales_in_minute'][0]*60))          # exact scale
                        current_time -= (self.config['data_input']['scales_in_minute'][0]*60)                           # -scale

                        lto_list[i]['result']['exit']['time'] = bson.Int64(current_time)
                        # TODO: WARNING: Non of the below is tested. So do the tests !!!
                        lto_list[i]['result']['exit']['price'] = float(sum([float(fill['price']) for fill in response['fills']]) / len(response['fills']) )
                        lto_list[i]['result']['exit']['quantity'] = float(sum([float(fill['qty']) for fill in response['fills']]))
                        lto_list[i]['result']['exit']['amount'] = lto_list[i]['result']['exit']['price'] * lto_list[i]['result']['exit']['quantity']
                        lto_list[i]['result']['exit']['fee'] = float(sum([float(fill['commission']) for fill in response['fills'] \
                            if fill['commissionAsset']==self.config['broker']['quote_currency'] ])) 

                        lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] \
                            - lto_list[i]['result']['enter']['amount'] \
                            - lto_list[i]['result']['enter']['fee'] \
                            - lto_list[i]['result']['exit']['fee']
                        lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']
                        self.telbot.send_constructed_msg('lto', *[ lto_list[i]['_id'], lto_list[i]['strategy'], lto_list[i]['pair'], 'exit', response["orderId"], EVENT_PLACED])
                        self.telbot.send_constructed_msg('lto', *[ lto_list[i]['_id'], lto_list[i]['strategy'], lto_list[i]['pair'], 'exit', response["orderId"], 'filled'])


                elif lto_list[i]['action'] == ACTN_EXEC_EXIT:
                    # If the enter is successful and the algorithm decides to execute the exit order
                    
                    '''
                    No need to check the error case because if the order could not be placed due to some reason,
                    there is no way other then retry. Status will stay like 'STAT_WAITING_EXIT', lto_update will not do anything,
                    strategy will not do anything and the flow will come here to do the same execution again
                    NOTE: This scenario above is not tested
                    
                    An alternative solution might be changing the status as 'open_exit', so that in the next iteration, exit module might be
                    updated to fix the problems such as filters etc. In this case the question is: Then what was wrong with the first time?
                    '''
                    if self.config['strategy'][lto_list[i]['strategy']]['exit']['type'] == TYPE_LIMIT:
                        lto_list[i] = await self._execute_limit_sell(lto_list[i])
                    elif self.config['strategy'][lto_list[i]['strategy']]['exit']['type'] == TYPE_OCO:
                        lto_list[i] = await self._execute_oco_sell(lto_list[i])

                # Postpone can be for the enter or the exit phase
                elif lto_list[i]['action'] == ACTN_POSTPONE:

                    if lto_list[i]['status'] == STAT_ENTER_EXP:
                        lto_list[i]['status'] = STAT_OPEN_ENTER
                        lto_list[i]['history'].append(lto_list[i]['status'])
                        self.logger.info(f'LTO {lto_list[i]["enter"]["limit"]["orderId"]}: postponed the ENTER to {lto_list[i]["enter"]["limit"]["expire"]}')

                    elif lto_list[i]['status'] == STAT_EXIT_EXP:
                        lto_list[i]['status'] = STAT_OPEN_EXIT
                        lto_list[i]['history'].append(lto_list[i]['status'])
                        exit_type = self.config["strategy"][lto_list[i]['strategy']]["exit"]["type"]
                        self.logger.info(f'LTO {lto_list[i]["exit"][exit_type]["orderId"]}: postponed the EXIT to {lto_list[i]["exit"][exit_type]["expire"]}')

                    else: pass

                # Delete the action, after the action is taken
                del lto_list[i]['action']

        return lto_list


    async def _execute_nto(self, nto_list):
        """
        If an NTO is executed:
        - 'orderId' is obtained from the response

        not executed:
        - the error message is logged
        - notification is send
        - NTO is deleted from the nto_dict

        Args:
            nto_list (list): list of brand new trade objects

        Returns:
            list: nto_list
        """
        # TODO: HIGH: Should we check the keys of an module and use the priorities or should we only use config file enter/exit types?
        nto_list_len = len(nto_list)
        live_nto_list = []
        for i in range(nto_list_len):
            # BUG: NEXT If an NTO is deleted from the list then there will be a index error since the list shrinked
            # NOTE: The status values other than STAT_OPEN_ENTER is here for lto update
            if nto_list[i]['status'] == STAT_OPEN_ENTER:
                
                if TYPE_MARKET in nto_list[i]['enter'].keys():
                    # NOTE: Since there is no risk evaluation in the market enter, It is not planned to be implemented
                    raise Exception('Market Enter is not supported')

                elif TYPE_LIMIT in nto_list[i]['enter'].keys():
                    try:
                        response = await self.client.order_limit_buy(
                            symbol=nto_list[i]['pair'],
                            quantity=nto_list[i]['enter'][TYPE_LIMIT]['quantity'],
                            price=f'%.{self.pricePrecision}f' % nto_list[i]['enter'][TYPE_LIMIT]['price'])
                        if response['status'] != 'NEW': raise Exception('Response status is not "NEW"')
                    # TODO: NEXT: For small quantities this float number create poblem such as 1.114e-05
                    #       Need the precision
                    #       f'%.{}f' % nto_list[i]['enter'][TYPE_LIMIT]['price']
                    # TODO: NEXT: Why this limit_buy is here and not in a function????
                        
                    except Exception as e:
                        self.logger.error(f"{nto_list[i]['strategy']} - {nto_list[i]['pair']}: {e}")
                        # del nto_list[i]
                        # TODO: Notification

                    else:
                        nto_list[i]['enter'][TYPE_LIMIT]['orderId'] = int(response['orderId'])
                        self.logger.info(f'NTO ({nto_list[i]["strategy"]},{nto_list[i]["pair"]}) limit order placed: {response["orderId"]}')
                        self.telbot.send_constructed_msg('lto', *['_id', nto_list[i]['strategy'], nto_list[i]['pair'], 'enter', response["orderId"], EVENT_PLACED]) # '_id' is not given yet
                        live_nto_list.append(copy.deepcopy(nto_list[i]))

                else: pass # TODO: Internal Error

            else: pass # TODO: Internal Error
        return live_nto_list


    async def execute_decision(self, nto_list, lto_list):
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
        #       Free quote currency check should be done prior to this point, If this logic should be implemented
        # TODO: _execute_lto cannot decide to not to enter if there is not enough balance. This check should be done in strategy.
        # NOTE: _execute_lto tries to execute, if things fails then it creates an error log, notification etc.
        
        # Execute decsisions about ltos
        lto_list = await self._execute_lto(lto_list)
        self.logger.debug('lto handling completed')
        # Execute new trade objects
        nto_list = await self._execute_nto(nto_list)      
        self.logger.debug('nto handling completed')

        # TODO: Consider returning trade_dict, because:
        #   - orders may not be accepted by the broker
        #       - In this case this side where to handle the issue: here or the main script
        #   - market sell causes instant fill
        #   - market enter causes instant fill

        return nto_list, lto_list


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
                   for b in last_observer_item['balances'] if float(b['free']) > 0 or float(b['locked']) > 0 or b['asset']==self.config['broker']['quote_currency'] ]
        # NOTE: Make sure that quote_currency stays in the df_balance even if it is 0

        df_balance = pd.DataFrame(balance)
        df_balance.set_index(['asset'], inplace=True)
        df_balance = df_balance.astype(float)
        df_balance['total'] = df_balance['free'] + df_balance['locked']
        '''
        pairs = []
        for asset in df_balance.index:
            if asset == self.quote_currency:
                pairs.append(str(asset))
            elif asset == self.credit_currency:
                pairs.append(str(self.quote_currency)+str(asset))
            else:
                pairs.append(str(asset)+str(self.quote_currency))
        df_balance['pair'] = pairs
        '''
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
        all_info = await self.client.get_exchange_info()

        selected_info = {}
        for item in all_info['symbols']:
            if item['symbol'] in all_pairs:
                selected_info[item['symbol']] = item

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

        self.logger.debug('get_data_dict started')

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
        self.logger.debug('get_data_dict ended')

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
                hist_data_start_time = session_start_time - time_scale_to_second(meta_data[0]) * (self.config['time_scales'][meta_data[0]][1]) * 1000 + 1 # ms = start_time + x sec * y times * 1000
            else:
                raise NotImplementedException('start_time is not integer')

            tasks_klines_scales.append(asyncio.create_task(self.client.get_historical_klines(meta_data[1], meta_data[0], start_str=hist_data_start_time, end_str=session_end_time )))
        composit_klines = list(await asyncio.gather(*tasks_klines_scales, return_exceptions=True))
        self.downloaded_data = await self.decompose(meta_data_pool, composit_klines)
        self.logger.debug('download ended')

        # The returned dict supposed to be used by the visulize_indicators.py
        return self.downloaded_data


    async def get_data_dict_download(self, meta_data_pool, ikarus_time):
        """
        meta_do = [('1m', 'BTCUSDT'), ('15m', 'BTCUSDT'), ('15m', 'XRPUSDT')]
        (time_scale, pair)
        length = meta_do['time_scale']
        """
        self.logger.debug('get_data_dict started')

        tasks_klines_scales = []
        data_dict = {}
        for meta_data in meta_data_pool:

            if type(ikarus_time) == int:
                # NOTE: If you need exactly 720 candles not 719 (unclosed (last) candle removed) then push hist_data_start_time back 1 step
                # NOTE: The cause of +1 comes from the desire to not the make hist_data_start_time an exact minute, Because when it is an exact 1m or 15m, 1 extra hist_kline is retrived addi
                hist_data_end_time = ikarus_time - time_scale_to_second(meta_data[0]) * 1000
                hist_data_start_time = ikarus_time - time_scale_to_second(meta_data[0]) * (self.config['time_scales'][meta_data[0]][1]) * 1000 + 1 # ms = start_time + x sec * y times * 1000 + 1
                if not meta_data[1] in data_dict.keys():
                    data_dict[meta_data[1]] = dict()

                data_dict[meta_data[1]][meta_data[0]] = self.downloaded_data[meta_data[1]][meta_data[0]].loc[hist_data_start_time:hist_data_end_time]
            else:
                raise NotImplementedException('start_time is not integer')

        self.logger.debug('get_data_dict ended')

        return data_dict


    async def get_historical_klines(self, start_time, end_time, pair, time_scale):

        hist_klines = await self.client.get_historical_klines(pair, time_scale, start_str=start_time, end_str=end_time )
        df = pd.DataFrame(hist_klines, columns=TestBinanceWrapper.kline_column_names)
        df = df.set_index(['open_time'])
        df = df.astype(float)
        return df


    async def decompose(self, meta_data_pool, composit_klines):

        self.logger.debug("decompose started")
        do_dict = dict()
        for idx, meta_data in enumerate(meta_data_pool):
            
            if not meta_data[1] in do_dict.keys():
                do_dict[meta_data[1]] = dict()
            
            df = pd.DataFrame(composit_klines[idx], columns=TestBinanceWrapper.kline_column_names)
            df = df.set_index(['open_time'])
            # NOTE: WARNING: Be aware that the last line is removed to not to affect analysis
            #       Since it requires closed candles.
            df.drop(df.index[-1], inplace=True)
            df = df.astype(float)
            do_dict[meta_data[1]][meta_data[0]] = df

        self.logger.debug("decompose ended")
        return do_dict


    async def _execute_lto(self, lto_list, df_balance, data_dict):
        """
        Execution Logic:
        for i in range(len(lto_list)):
            if 'action' in lto_list[i].keys():
                1. cancel
                    In case of enter expire, it might be decided to cancel the order
                2. update
                    cancel the prev order and place the same type of order with updated values
                3. market_enter
                    In case of enter expire, it might be decided to enter with market order
                4. market_exit
                    In case of exit expire, it might be decided to exit with market order

        Args:
            lto_list (list): [description]
            df_balance (pd.DataFrame): [description]

        Returns:
            tuple: lto_list, df_balance
        """
        for i in range(len(lto_list)):
            if 'action' in lto_list[i].keys():
                if lto_list[i]['action'] == ACTN_CANCEL:
                    # TODO: ACTN_CANCEL action currently only used for enter phase, exit phase cancel can be added
                    lto_list[i]['status'] = STAT_CLOSED
                    lto_list[i]['history'].append(lto_list[i]['status'])

                    # No need to check the enter type because lto do not contain TYPE_MARKET. It only contains TYPE_LIMIT
                    df_balance = balance_manager.cancel_enter_order(df_balance, self.quote_currency, lto_list[i]['enter'][TYPE_LIMIT])
            
                elif lto_list[i]['action'] == ACTN_UPDATE:
                    lto_list[i]['status'] = STAT_OPEN_EXIT
                    '''
                    - Since the enter is succesful, the quantity to exit is already determined.
                    - Uptate operation will cause the locked base asset to go to free and locked again since the quantity will not change
                    - The changes in the price levels are already in the LTO so no action needed here
                    - Thus no need to update df_balance
                    '''
                    
                    # Cancel the order

                    # Place the order
                    # NOTE: No need to do anything for backtest
                    # TODO: NEXT: Cancel the previous order and place the new order
                    #       Do not change the exit order amount price etc because here the df_balance is not updated accordingly
                    pass
                
                elif lto_list[i]['action'] == ACTN_MARKET_ENTER:
                    pass
                
                elif lto_list[i]['action'] == ACTN_MARKET_EXIT:

                    lto_list[i]['status'] = STAT_CLOSED
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['cause'] = STAT_EXIT_EXP

                    min_scale = await get_min_scale(self.config['time_scales'].keys(), self.config['strategy'][lto_list[i]['strategy']]['time_scales'])
                    last_kline = data_dict[lto_list[i]['pair']][min_scale].tail(1)

                    # NOTE: TEST: Simulation of the market sell is normally the open price of the future candle,
                    #             For the sake of simplicity closed price of the last candle is used in the market sell
                    #             by assumming that the 'close' price is pretty close to the 'open' of the future

                    lto_list[i]['result']['exit']['type'] = TYPE_MARKET
                    lto_list[i]['result']['exit']['time'] = bson.Int64(last_kline.index.values + time_scale_to_milisecond(min_scale))
                    lto_list[i]['result']['exit']['price'] = float(last_kline['close'])
                    lto_list[i]['result']['exit']['quantity'] = lto_list[i]['exit'][TYPE_MARKET]['quantity']
                    lto_list[i]['result']['exit']['amount'] = lto_list[i]['result']['exit']['price'] * lto_list[i]['result']['exit']['quantity']
                    lto_list[i]['result']['exit']['fee'] = calculate_fee(lto_list[i]['result']['exit']['amount'], StrategyBase.fee)

                    #lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] - lto_list[i]['result']['enter']['amount']
                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] \
                        - lto_list[i]['result']['enter']['amount'] \
                        - lto_list[i]['result']['enter']['fee'] \
                        - lto_list[i]['result']['exit']['fee']

                    base_cur = lto_list[i]['pair'].replace(self.config['broker']['quote_currency'],'')
                    
                    df_balance = balance_manager.cancel_exit_order(df_balance, base_cur, lto_list[i]['result']['exit']['quantity'])
                    df_balance = balance_manager.place_exit_order(df_balance, base_cur, lto_list[i]['result']['enter']['quantity'])
                    df_balance = balance_manager.sell(df_balance, self.config['broker']['quote_currency'], base_cur, lto_list[i]['result']['exit'])
            
                elif lto_list[i]['action'] == ACTN_EXEC_EXIT:
                    # If the enter is successfull and the algorithm decides to execute the exit order

                    # NOTE: TYPE_MARKET orders executed and closed right here
                    # TODO: NEXT: Check here why do we need TYPE_MARKET section here???
                    if TYPE_MARKET in lto_list[i]['exit'].keys():
                        # TODO: Consider a more elegant way of doing this
                        min_scale = await get_min_scale(self.config['time_scales'].keys(), self.config['strategy'][lto_list[i]['strategy']]['time_scales'])
                        last_kline = data_dict[lto_list[i]['pair']][min_scale].tail(1)

                        lto_list[i]['status'] = STAT_CLOSED
                        lto_list[i]['history'].append(lto_list[i]['status'])
                        lto_list[i]['result']['cause'] = STAT_CLOSED

                        lto_list[i]['result']['exit']['type'] = TYPE_MARKET
                        # TODO: NEXT: CAREFULL about the close time of the market exit, it requires ikarus_time
                        lto_list[i]['result']['exit']['time'] = bson.Int64(last_kline.index.values + time_scale_to_milisecond(min_scale))
                        lto_list[i]['result']['exit']['price'] = float(last_kline['close'])
                        lto_list[i]['result']['exit']['quantity'] = lto_list[i]['exit'][TYPE_MARKET]['quantity']
                        lto_list[i]['result']['exit']['amount'] = lto_list[i]['result']['exit']['price'] * lto_list[i]['result']['exit']['quantity']
                        lto_list[i]['result']['exit']['fee'] = calculate_fee(lto_list[i]['result']['exit']['amount'], StrategyBase.fee)
                        # TODO NEXT: safe calcualtion for profit and fee
                        lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] \
                            - lto_list[i]['result']['enter']['amount'] \
                            - lto_list[i]['result']['enter']['fee'] \
                            - lto_list[i]['result']['exit']['fee']
                        lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']

                        # TODO: result.enter.quantity shoudl be copied to exit.x.quantity as well
                        base_cur = lto_list[i]['pair'].replace(self.config['broker']['quote_currency'],'')
                        df_balance = balance_manager.place_exit_order(df_balance, base_cur, lto_list[i]['result']['enter']['quantity'])
                        df_balance = balance_manager.sell(df_balance, self.config['broker']['quote_currency'], base_cur, lto_list[i]['result']['exit'])

                    # NOTE: For the TYPE_LIMIT and TYPE_OCO the orders are only placed, not executed yet
                    elif TYPE_LIMIT in lto_list[i]['exit'].keys() or TYPE_OCO in lto_list[i]['exit'].keys():
                        lto_list[i]['status'] = STAT_OPEN_EXIT
                        lto_list[i]['history'].append(lto_list[i]['status'])
                        base_cur = lto_list[i]['pair'].replace(self.config['broker']['quote_currency'],'')
                        df_balance = balance_manager.place_exit_order(df_balance, base_cur, lto_list[i]['result']['enter']['quantity'])

                    else: pass # TODO: Internal Error


                # Postpone can be for the enter or the exit phase
                elif lto_list[i]['action'] == ACTN_POSTPONE:
                    if lto_list[i]['status'] == STAT_ENTER_EXP:
                        lto_list[i]['status'] = STAT_OPEN_ENTER
                        lto_list[i]['history'].append(lto_list[i]['status'])

                    elif lto_list[i]['status'] == STAT_EXIT_EXP:
                        lto_list[i]['status'] = STAT_OPEN_EXIT
                        lto_list[i]['history'].append(lto_list[i]['status'])
                        pass
                    else: pass

                # Delete the action, after the action is taken
                del lto_list[i]['action']

        return lto_list, df_balance


    async def _execute_nto(self, nto_list, df_balance, data_dict):
        """
        Args:
            nto_list (list): [description]
            df_balances (pd.DataFrame): [description]

        Returns:
            tuple: nto_list, df_balance
        """
        for i in range(len(nto_list)):
            # NOTE: The status values other than STAT_OPEN_ENTER is here for lto update
            if nto_list[i]['status'] == STAT_OPEN_ENTER:
                
                # TODO: Consider using the direct enter and exit types rather than checking the keys with a order
                if TYPE_MARKET in nto_list[i]['enter'].keys():

                    nto_list[i]['status'] = STAT_OPEN_EXIT
                    nto_list[i]['history'].append(nto_list[i]['status'])

                    # NOTE: The order is PLACED and FILLED
                    min_scale = await get_min_scale(self.config['time_scales'].keys(), self.config['strategy'][nto_list[i]['strategy']]['time_scales'])
                    last_kline = data_dict[nto_list[i]['pair']][min_scale].tail(1)

                    nto_list[i]['enter'][TYPE_MARKET]['orderId'] = int(time.time() * 1000) # Get the order id from the broker
                    nto_list[i]['result'][PHASE_ENTER]['type'] = TYPE_MARKET
                    nto_list[i]['result'][PHASE_ENTER]['time'] = bson.Int64(last_kline.index.values + time_scale_to_milisecond(min_scale))
                    nto_list[i]['result'][PHASE_ENTER]['price'] = float(last_kline['close'])
                    nto_list[i]['result'][PHASE_ENTER]['quantity'] = nto_list[i][PHASE_ENTER][TYPE_MARKET]['quantity']
                    nto_list[i]['result'][PHASE_ENTER]['amount'] = nto_list[i][PHASE_ENTER][TYPE_MARKET]['amount']
                    nto_list[i]['result'][PHASE_ENTER]['fee'] = calculate_fee(nto_list[i]['result'][PHASE_ENTER]['amount'], StrategyBase.fee)
                    # TODO: Instead of directly modifying the value, just create a wrapper that also checks if the withdraw or deposit is successfull
                    #       There might be some cases where the balance go below zero, (Which indicates some bgs in implementation of logic)

                    base_cur = nto_list[i]['pair'].replace(self.config['broker']['quote_currency'],'')
                    
                    df_balance = balance_manager.place_enter_order(df_balance, self.quote_currency, nto_list[i][PHASE_ENTER][TYPE_MARKET])
                    df_balance = balance_manager.buy(df_balance, self.quote_currency, base_cur, nto_list[i]['result'][PHASE_ENTER], TYPE_MARKET)

                    pass

                elif TYPE_LIMIT in nto_list[i]['enter'].keys():
                    # NOTE: In live-trading orderId's are gathered from the broker and it is unique. Here it is set to a unique
                    #       timestamp values

                    # NOTE: The order is only PLACED but not FILLED. No fee here
                    nto_list[i]['enter'][TYPE_LIMIT]['orderId'] = int(time.time() * 1000) # Get the order id from the broker
                    df_balance = balance_manager.place_enter_order(df_balance, self.quote_currency, nto_list[i]['enter'][TYPE_LIMIT])

                else: pass # TODO: Internal Error

            else: pass # TODO: Internal Error
        return nto_list, df_balance


    async def execute_decision(self, nto_list, df_balance, lto_list, data_dict):
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

        # Execute decsisions about ltos
        lto_list, df_balance = await self._execute_lto(lto_list, df_balance, data_dict)

        # Execute new trade objects
        nto_list, df_balance = await self._execute_nto(nto_list, df_balance, data_dict)
            
        # TODO: HIGH: TEST: In the execute section commission needs to be evaluated. This section should behave
        #       exactly as the broker. 
        # NOTE: As a result the equity will be less than evaluated since the comission has been cut.

        return df_balance, lto_list, nto_list