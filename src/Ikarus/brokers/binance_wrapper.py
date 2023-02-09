from ..exceptions import NotImplementedException
from binance.enums import *
import asyncio
import pandas as pd
import logging
import json
import bson
import copy
from ..utils import time_scale_to_second, get_min_scale, \
    safe_multiply, safe_divide, round_to_period
import more_itertools
from .. import binance_filters
from ..objects import OCO, ECause, ECommand, EState, Limit, Market, trade_to_dict
from dataclasses import asdict

logger = logging.getLogger('app')

# This variable added as deus ex machina
symbol_info = None

class BinanceWrapper():

    kline_column_names = ["open_time", "open", "high", "low", "close", "volume", "close_time","quote_asset_volume", 
                        "num_of_trades", "taker_buy_base_ast_vol", "taker_buy_quote_ast_vol", "ignore"]

    def __init__(self, _client, _config, _telbot):
        # TODO: Think about the binance.exceptions.BinanceAPIException: APIError(code=-1021): Timestamp for this request was 1000ms ahead of the server's time.
        #       The alternative slution (the wrapper for the binane client can be added to here):
        #       https://github.com/sammchardy/python-binance/issues/249

        self.client = _client
        self.config = _config
        self.telbot = _telbot

        # Set reference currencies
        self.quote_currency = _config['broker']['quote_currency']
        self.pricePrecision = 8
        # TODO: get the precision from symbol info and use it in the orders 


    async def get_status(self):
        broker_status = await self.client.get_system_status()
        return broker_status['status']


    async def get_time(self):
        '''
        { 
            "status": 0,              // 0: normal, 1: system maintenance
            "msg": "normal"           // "normal", "system_maintenance"
        }
        '''
        server_time = await self.client.get_server_time()
        return int(server_time['serverTime']/1000)


    async def get_info(self):

        info = await self.client.get_account()
        balance = [{'asset':b['asset'], 'free':b['free'], 'locked':b['locked']}
                   for b in info['balances'] if float(b['free']) > 0 or float(b['locked']) > 0]

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

        df_balance = await self.get_info()
        return df_balance


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
                hist_data_start_time = ikarus_time - time_scale_to_second(meta_data[0]) * (self.config['time_scales'][meta_data[0]]) * 1000 + 1 # ms = start_time + x sec * y times * 1000 + 1
            else:
                raise NotImplementedException('start_time is not integer')

            tasks_klines_scales.append(asyncio.create_task(self.client.get_historical_klines(meta_data[1], meta_data[0], start_str=hist_data_start_time, end_str=ikarus_time )))

        composit_klines = list(await asyncio.gather(*tasks_klines_scales, return_exceptions=True))

        for result in composit_klines:
            if type(result) != list:
                logger.error(f'Invalid kline receiived: {result}')
                raise result

        # TODO: NEXT: BUG: If a pair does not exist in the given time, then composit kline comes empty: [[], [[...], [...]]
        data_dict = await self.decompose(meta_data_pool, composit_klines)

        # TODO: Length check for Data dict items could help a lot to detect anomalies
        return data_dict


    async def decompose(self, meta_data_pool, composit_klines):

        do_dict = dict()
        for idx, meta_data in enumerate(meta_data_pool):
            
            if not meta_data[1] in do_dict.keys():
                do_dict[meta_data[1]] = dict()
            
            df = pd.DataFrame(composit_klines[idx], columns=BinanceWrapper.kline_column_names)
            df = df.set_index(['open_time'])
            # NOTE: WARNING: Be aware that the last line is removed to not to affect analysis, since it requires closed candles.
            df.drop(df.index[-1], inplace=True)
            df = df.astype(float)

            if len(df) != int(self.config['time_scales'][meta_data[0]]-1):
                logger.warn(f"Missing historical candle for {meta_data[1]} {meta_data[0]}: {len(df)} instead of {self.config['time_scales'][meta_data[0]][1]-1}")

            do_dict[meta_data[1]][meta_data[0]] = df

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
        tasks_klines_scales = []
        for pair in pairs:
            for index, row in time_df.iterrows():
                tasks_klines_scales.append(asyncio.create_task(self.client.get_historical_klines(pair, row["scale"], start_str="{} ago UTC".format(row["length_str"]))))

        #composit_klines = await self.client.get_historical_klines(pair, row["scale"], start_str="{} ago UTC".format(row["length_str"]))
        composit_klines = list(await asyncio.gather(*tasks_klines_scales, return_exceptions=True))

        data_dict = await self.decompose(pairs, time_df, composit_klines)

        # NOTE: Keep in mind that the last row is the current candle that has not been completed
        return data_dict


    async def get_trade_orders(self, lto_list):

        logger.debug('get_lto_orders started')

        # Check the status of LTOs:
        coroutines = []
        for lto in lto_list:
            if lto['status'] in [STAT_OPEN_ENTER, STAT_ENTER_EXP]:
                coroutines.append(self.client.get_order(symbol=lto['pair'], orderId=lto['enter'][TYPE_LIMIT]['orderId']))

            elif lto['status'] in [STAT_OPEN_EXIT, STAT_EXIT_EXP]:
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
        
        logger.debug('get_lto_orders started')

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

        except Exception as e:
            logger.error(f"{lto['strategy']} - {lto['pair']}: {e}")
            # TODO: Notification: ERROR
            return False

        else:
            response_stoploss, response_limit_maker = response["orderReports"][0], response["orderReports"][1]
            logger.info(f'LTO "{lto["_id"]}": "{response_limit_maker["side"]}" "{response_limit_maker["type"]}" order placed: {response_limit_maker["orderId"]}')
            logger.info(f'LTO "{lto["_id"]}": "{response_stoploss["side"]}" "{response_stoploss["type"]}" order placed: {response_stoploss["orderId"]}')

            lto['exit'][TYPE_OCO]['orderId'] = response_limit_maker['orderId']
            lto['exit'][TYPE_OCO]['stopLimit_orderId'] = response_stoploss['orderId']

            lto['status'] = STAT_OPEN_EXIT
            lto['history'].append(lto['status'])
            self.telbot.send_constructed_msg('lto', *[lto['_id'], lto['strategy'], lto['pair'], 'exit', response_limit_maker["orderId"], EVENT_PLACED])

            return True


    async def _execute_limit_sell(self, lto):
        try:
            response = await self.client.order_limit_sell(
                symbol=lto['pair'],
                quantity=lto['exit'][TYPE_LIMIT]['quantity'],
                price=f'%.{self.pricePrecision}f' % lto['exit'][TYPE_LIMIT]['price'])

        except Exception as e:
            logger.error(f"{lto['strategy']} - {lto['pair']}: {e}")
            # TODO: Notification: ERROR
            return False

        else:
            logger.info(f'LTO "{lto["_id"]}": "{response["side"]}" "{response["type"]}" order placed: {response["orderId"]}')
            lto['exit'][TYPE_LIMIT]['orderId'] = response['orderId']

            lto['status'] = STAT_OPEN_EXIT
            lto['history'].append(lto['status'])
            self.telbot.send_constructed_msg('lto', *[lto['_id'], lto['strategy'], lto['pair'], 'exit', response["orderId"], EVENT_PLACED])
            return True


    async def _execute_limit_buy(self, lto):
        try:
            response = await self.client.order_limit_buy(
                symbol=lto['pair'],
                quantity=lto[PHASE_ENTER][TYPE_LIMIT]['quantity'],
                price=f'%.{self.pricePrecision}f' % lto[PHASE_ENTER][TYPE_LIMIT]['price'])

        except Exception as e:
            logger.error(f"{lto['strategy']} - {lto['pair']}: {e}")
            logger.debug(json.dumps(lto[PHASE_ENTER][TYPE_LIMIT]))
            return False

        else:
            logger.info(f'LTO "_id": "{response["side"]}" "{response["type"]}" order placed: {response["orderId"]}')
            lto[PHASE_ENTER][TYPE_LIMIT]['orderId'] = response['orderId']

            lto['status'] = STAT_OPEN_ENTER
            lto['history'].append(lto['status'])
            self.telbot.send_constructed_msg('lto', *['_id', lto['strategy'], lto['pair'], PHASE_ENTER, response["orderId"], EVENT_PLACED])
            return True


    async def _execute_cancel(self, lto):
        # NOTE: Since cancel can be called to end the life of LTO if the phase is enter and to update if
        #       the phase is exit, status change should not be here        
        try:
            phase = get_lto_phase(lto)
            type = more_itertools.one(lto[phase].keys())
            response = await self.client.cancel_order(
                symbol=lto['pair'],
                orderId=lto[phase][type]['orderId'])

        except Exception as e:
            logger.error(f"{lto['strategy']} - {lto['pair']}: {e}")
            # TODO: Notification: ERROR
            return False

        else:
            if phase == PHASE_EXIT and type == TYPE_OCO:
                response_stoploss, response_limit_maker = response['orderReports'][0], response['orderReports'][1]
                logger.info(f'LTO "{lto["_id"]}": "{response_stoploss["side"]}" "{response_stoploss["type"]}" order canceled: {response_stoploss["orderId"]}')
                logger.info(f'LTO "{lto["_id"]}": "{response_limit_maker["side"]}" "{response_limit_maker["type"]}" order canceled: {response_limit_maker["orderId"]}')
                self.telbot.send_constructed_msg('lto', *[lto['_id'], phase, response_limit_maker["orderId"], 'canceled'])

            else:
                logger.info(f'LTO "{lto["_id"]}": "{response["side"]}" "{response["type"]}" order canceled: {response["orderId"]}')
                self.telbot.send_constructed_msg('lto', *[lto['_id'], lto['strategy'], lto['pair'], phase, response["orderId"], 'canceled'])
            return True


    async def _execute_market_buy(self, trade):
        try:
            logger.debug(asdict(trade.enter))
            response = await self.client.order_market_buy(
                symbol=trade.pair,
                quantity=trade.enter.quantity)
            logger.debug(json.dumps(response))

        except Exception as e:
            logger.error(f"{e}")
            return False

        else:
            logger.info(f'LTO "_id": "{response["side"]}" "{response["type"]}" order placed: {response["orderId"]}')
            lto[PHASE_ENTER][TYPE_MARKET]['orderId'] = response['orderId']

            lto['status'] = STAT_WAITING_EXIT
            lto['history'].append(lto['status'])
            
            if response['executedQty'] != response['origQty']:
                # TODO: Send an Error msg
                pass
            avg_price = safe_divide(sum([safe_multiply(fill['price'],fill['qty']) for fill in response['fills']]), response['executedQty'])
        
            strategy_cycle_period = await get_min_scale(self.config['time_scales'].keys(), self.config['strategy'][lto['strategy']]['time_scales'])
            strategy_cycle_period_in_sec = time_scale_to_second(strategy_cycle_period)
            time_value = int(response["transactTime"]/1000)

            # Get the start time of the current candle
            execution_time = round_to_period(time_value, strategy_cycle_period_in_sec, direction='floor')

            lto['result'][PHASE_ENTER]['type'] = TYPE_MARKET
            lto['result'][PHASE_ENTER]['time'] = execution_time*1000
            lto['result'][PHASE_ENTER]['price'] = avg_price
            lto['result'][PHASE_ENTER]['quantity'] = float(response["executedQty"])
            lto['result'][PHASE_ENTER]['amount'] = float(lto['result'][PHASE_ENTER]['price'] * lto['result'][PHASE_ENTER]['quantity'])
            lto['result'][PHASE_ENTER]['fee'] = calculate_fee(lto['result'][PHASE_ENTER]['amount'], TestBinanceWrapper.fee_rate)   # TODO: Obtain the comission from the order
            return True

    async def _execute_market_sell(self, lto):
        try:
            response = await self.client.order_market_sell(
                symbol=lto['pair'],
                quantity=lto[PHASE_EXIT][TYPE_MARKET]['quantity'])
            logger.debug(json.dumps(response))
            logger.debug(json.dumps(lto[PHASE_EXIT][TYPE_MARKET]))

        except Exception as e:
            logger.error(f"{lto['strategy']} - {lto['pair']}: {e}")
            logger.debug(json.dumps(lto[PHASE_EXIT][TYPE_MARKET]))
            return False

        else:
            logger.info(f'LTO "_id": "{response["side"]}" "{response["type"]}" order placed: {response["orderId"]}')
            lto[PHASE_EXIT][TYPE_MARKET]['orderId'] = response['orderId']

            lto['status'] = STAT_CLOSED
            lto['history'].append(lto['status'])
            lto['result']['cause'] = STAT_CLOSED

            if response['executedQty'] != response['origQty']:
                # TODO: Send an Error msg
                pass
            
            avg_price = safe_divide(sum([safe_multiply(fill['price'],fill['qty']) for fill in response['fills']]), response['executedQty'])
        
            strategy_cycle_period = await get_min_scale(self.config['time_scales'].keys(), self.config['strategy'][lto['strategy']]['time_scales'])
            strategy_cycle_period_in_sec = time_scale_to_second(strategy_cycle_period)
            time_value = int(response["transactTime"]/1000)

            # Get the start time of the current candle
            execution_time = round_to_period(time_value, strategy_cycle_period_in_sec, direction='floor')

            lto['result'][PHASE_EXIT]['type'] = TYPE_MARKET
            lto['result'][PHASE_EXIT]['time'] = execution_time*1000
            lto['result'][PHASE_EXIT]['price'] = avg_price
            lto['result'][PHASE_EXIT]['quantity'] = float(response["executedQty"])
            lto['result'][PHASE_EXIT]['amount'] = float(lto['result'][PHASE_EXIT]['price'] * lto['result'][PHASE_EXIT]['quantity'])
            lto['result'][PHASE_EXIT]['fee'] = calculate_fee(lto['result'][PHASE_EXIT]['amount'], TestBinanceWrapper.fee_rate)

            lto['result']['profit'] = lto['result'][PHASE_EXIT]['amount'] \
                - lto['result'][PHASE_ENTER]['amount'] \
                - lto['result'][PHASE_ENTER]['fee'] \
                - lto['result'][PHASE_EXIT]['fee']
            lto['result']['liveTime'] = lto['result'][PHASE_EXIT]['time'] - lto['result'][PHASE_ENTER]['time']

            self.telbot.send_constructed_msg('lto', *[lto['_id'], lto['strategy'], lto['pair'], 'exit', response["orderId"], EVENT_FILLED])

            return True

    async def _execute_lto(self, trades):
        for i in range(len(trades)):
            if trades[i].command == ECommand.CANCEL:

                if self.execute_cancel(trades[i]):
                    trades[i].status = EState.CLOSED
                    trades[i].reset_command()


                if lto_list[i]['action'] == ACTN_UPDATE:
                    '''
                    ACTN_UPDATE can only exist in the exit phase, thus no check for status
                    '''
                    # Cancel the order
                    if await self._execute_cancel(lto_list[i]):
                        '''
                        No need to check the error case because if the order could not be placed due to some reason,
                        there is no way other then retry. Status will stay like 'STAT_EXIT_EXP', lto_update will not do anything,
                        strategy will create a new update action and send it here in the next cycle
                        '''
                        # Place the order
                        exit_type = more_itertools.one(lto_list[i][PHASE_EXIT].keys())
                        if exit_type == TYPE_OCO:
                            await self._execute_oco_sell(lto_list[i])
                        elif exit_type == TYPE_LIMIT:
                            await self._execute_limit_sell(lto_list[i])
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
                        logger.error(f"{lto_list[i]['strategy']} - {lto_list[i]['pair']}: {e}")

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
                    
                    if self.config['strategy'][lto_list[i]['strategy']]['exit']['type'] == TYPE_MARKET:
                        await self._execute_market_sell(lto_list[i])  
                    elif self.config['strategy'][lto_list[i]['strategy']]['exit']['type'] == TYPE_LIMIT:
                        await self._execute_limit_sell(lto_list[i])
                    elif self.config['strategy'][lto_list[i]['strategy']]['exit']['type'] == TYPE_OCO:
                        await self._execute_oco_sell(lto_list[i])


                # Delete the action, after the action is taken
                del lto_list[i]['action']



    async def _execute_nto(self, trades):

        for i in range(len(trades)):

            if trades[i].command == ECommand.NONE:
                continue

            buy_method = f'_execute_{type(trades[i].enter).__name__.lower()}_buy'
            if await getattr(self, buy_method)(trades[i]): 
                trades[i].command = ECommand.NONE
            else:
                trades[i] = None


    async def execute_decision(self, new_trades, live_trades):
        
        # Execute decsisions about ltos
        await self._execute_lto(live_trades)

        # Execute new trade objects
        await self._execute_nto(new_trades)


async def sync_trades_with_orders(trade_list, data_dict, strategy_period_mapping, orders_dict):


    # NOTE: In broker, an OCO order actually 2 different orders. The solution might be:
    #       - Keep the limit order as the trade id.
    #       - If the limit_maker is FILLED then we are fine
    #       - If the limit_maker İS EXPIRED then read the tradeid of to oco_stoploss and do what needs to be done
    #       - If the limit_maker İS CANCELED they bot oco orders canceld and this is an external touch
    #       : Keep the limit_maker as the 'tradeid' of the lto and keep the oco_stoploss in that lto. If needed reach it.

    # NOTE: Each lto with enter/exit type TYPE_LIMIT has 1 order in orders_dict. However, each OCO exit has 2 orders in orders dict.
    #       len(orders_dict) >= len(lto_dict)

    for i in range(len(trade_list)):

        if trade_list[i].status == EState.WAITING_EXIT:
            # NOTE: If the condition is true, then there is no active order for that LTO, so the statement: orders_dict[orderId]
            #       will cause exception since there is no orderId
            continue

        pair = trade_list[i].pair

        #scale = list(data_dict[pair].keys())[0]
        #last_closed_candle_open_time = bson.Int64(data_dict[pair][scale].index[-1])  # current_candle open_time
        # NOTE: last_closed_candle_open_time is used because for the anything that happens: it happend in the last closed kline

        strategy_min_scale = strategy_period_mapping[lto_list[i]['strategy']]
        last_kline = data_dict[pair][strategy_min_scale].tail(1)
        last_closed_candle_open_time = bson.Int64(last_kline.index.values[0])

        phase_lto = get_lto_phase(lto_list[i])
        type = config['strategy'][lto_list[i]['strategy']][phase_lto]['type']
        orderId = lto_list[i][phase_lto][type]['orderId'] # Get the orderId of the exit module

        # BUG: If the lto has market enter order or simply the exit order execution failed, then the status will remain STAT_WAITING_EXIT.
        #       In this case the phase become the PHASE_EXIT and the order ID is searched for the exit order which does not exist yet
        if orders_dict[orderId]['status'] == 'CANCELED':
            logger.warning(f'LTO: "{lto_list[i]["_id"]}": canceled at the phase {phase_lto}. Order ID: {orderId}. Closing the LTO')
            telbot.send_constructed_msg('lto', *[lto_list[i]['_id'], lto_list[i]['strategy'], lto_list[i]['pair'], phase_lto, orderId, 'manually canceled'])

            # NOTE: In case of Manual Interventions, close the LTO without any change
            lto_list[i]['status'] = STAT_CLOSED
            lto_list[i]['result']['cause'] = CAUSE_MANUAL_CHANGE
            lto_list[i]['result']['exit']['time'] = last_closed_candle_open_time

            if lto_list[i]['result']['enter']['time'] != '':
                lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']

            # Skip the rest of the evaluation since the LTO exposed to manual change
            continue

        if lto_list[i]['status'] == STAT_OPEN_ENTER:
            if TYPE_LIMIT in lto_list[i]['enter'].keys():
                
                enter_orderId = lto_list[i]['enter'][TYPE_LIMIT]['orderId'] # Get the orderId of the enter module
                # Check if the open enter trade is filled else if the trade is expired
                if orders_dict[enter_orderId]['status'] == 'FILLED':

                    lto_list[i]['status'] = STAT_WAITING_EXIT
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['enter']['type'] = TYPE_LIMIT
                    lto_list[i]['result']['enter']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['enter']['price'] = float(orders_dict[enter_orderId]['price'])
                    lto_list[i]['result']['enter']['quantity'] = float(orders_dict[enter_orderId]['executedQty'])
                    lto_list[i]['result']['enter']['amount'] = float(lto_list[i]['result']['enter']['price'] * lto_list[i]['result']['enter']['quantity'])
                    lto_list[i]['result']['enter']['fee'] = calculate_fee(lto_list[i]['result']['enter']['amount'], StrategyBase.fee)
                    telbot.send_constructed_msg('lto', *[lto_list[i]['_id'], lto_list[i]['strategy'], lto_list[i]['pair'], 'enter', enter_orderId, 'filled'])


                elif int(lto_list[i]['enter'][TYPE_LIMIT]['expire']) <= last_closed_candle_open_time:
                    # Report the expiration to algorithm
                    lto_list[i]['status'] = STAT_ENTER_EXP
                    lto_list[i]['history'].append(lto_list[i]['status'])

            else:
                # TODO: Internal Error
                pass

        elif lto_list[i]['status'] == STAT_PART_CLOSED_ENTER:
            # Ignore for the tests
            pass

        elif lto_list[i]['status'] == STAT_OPEN_EXIT:

            if TYPE_LIMIT in lto_list[i]['exit'].keys():
                exit_orderId = lto_list[i]['exit'][TYPE_LIMIT]['orderId'] # Get the orderId of the exit module
                # Check if the open sell trade is filled or stoploss is taken
                if orders_dict[exit_orderId]['status'] == 'FILLED':

                    lto_list[i]['status'] = STAT_CLOSED
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['cause'] = STAT_CLOSED

                    lto_list[i]['result']['exit']['type'] = TYPE_LIMIT
                    lto_list[i]['result']['exit']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['exit']['price'] = float(orders_dict[exit_orderId]['price'])
                    lto_list[i]['result']['exit']['quantity'] = float(orders_dict[exit_orderId]['executedQty'])
                    lto_list[i]['result']['exit']['amount'] = float(lto_list[i]['result']['exit']['price'] * lto_list[i]['result']['exit']['quantity'])
                    lto_list[i]['result']['exit']['fee'] = calculate_fee(lto_list[i]['result']['exit']['amount'], StrategyBase.fee)

                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] \
                        - lto_list[i]['result']['enter']['amount'] \
                        - lto_list[i]['result']['enter']['fee'] \
                        - lto_list[i]['result']['exit']['fee']
                    lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']

                    telbot.send_constructed_msg('lto', *[lto_list[i]['_id'], lto_list[i]['strategy'], lto_list[i]['pair'], 'exit', exit_orderId, 'filled'])

                elif int(lto_list[i]['exit'][TYPE_LIMIT]['expire']) <= last_closed_candle_open_time:
                    lto_list[i]['status'] = STAT_EXIT_EXP
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    
                else:
                    pass

            elif TYPE_OCO in lto_list[i]['exit'].keys():
                oco_limit_orderId = lto_list[i]['exit'][TYPE_OCO]['orderId'] # Get the orderId of the enter module
                oco_stopLimit_orderId = lto_list[i]['exit'][TYPE_OCO]['stopLimit_orderId'] # Get the orderId of the enter module

                if orders_dict[oco_limit_orderId]['status'] == 'EXPIRED' and orders_dict[oco_stopLimit_orderId]['status'] == 'FILLED':

                    # Stop Loss takens
                    lto_list[i]['status'] = STAT_CLOSED
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['cause'] = STAT_CLOSED
                    lto_list[i]['result']['exit']['type'] = 'oco_stoploss'
                    lto_list[i]['result']['exit']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['exit']['price'] = float(orders_dict[oco_stopLimit_orderId]['price'])
                    lto_list[i]['result']['exit']['quantity'] = float(orders_dict[oco_stopLimit_orderId]['executedQty'])
                    lto_list[i]['result']['exit']['amount'] = float(lto_list[i]['result']['exit']['price'] * lto_list[i]['result']['exit']['quantity'])
                    lto_list[i]['result']['exit']['fee'] = calculate_fee(lto_list[i]['result']['exit']['amount'], StrategyBase.fee)

                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] \
                        - lto_list[i]['result']['enter']['amount'] \
                        - lto_list[i]['result']['enter']['fee'] \
                        - lto_list[i]['result']['exit']['fee']
                    lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']
                    
                    telbot.send_constructed_msg('lto', *[lto_list[i]['_id'], lto_list[i]['strategy'], lto_list[i]['pair'], 'exit', oco_stopLimit_orderId, 'filled'])

                elif orders_dict[oco_limit_orderId]['status'] == 'FILLED' and orders_dict[oco_stopLimit_orderId]['status'] == 'EXPIRED':

                    # Limit taken
                    lto_list[i]['status'] = STAT_CLOSED
                    lto_list[i]['history'].append(lto_list[i]['status'])
                    lto_list[i]['result']['cause'] = STAT_CLOSED

                    lto_list[i]['result']['exit']['type'] = 'oco_limit'
                    lto_list[i]['result']['exit']['time'] = last_closed_candle_open_time
                    lto_list[i]['result']['exit']['price'] = float(orders_dict[oco_limit_orderId]['price'])
                    lto_list[i]['result']['exit']['quantity'] = float(orders_dict[oco_limit_orderId]['executedQty'])
                    lto_list[i]['result']['exit']['amount'] = float(lto_list[i]['result']['exit']['price'] * lto_list[i]['result']['exit']['quantity'])
                    lto_list[i]['result']['exit']['fee'] = calculate_fee(lto_list[i]['result']['exit']['amount'], StrategyBase.fee)

                    lto_list[i]['result']['profit'] = lto_list[i]['result']['exit']['amount'] \
                        - lto_list[i]['result']['enter']['amount'] \
                        - lto_list[i]['result']['enter']['fee'] \
                        - lto_list[i]['result']['exit']['fee']
                    lto_list[i]['result']['liveTime'] = lto_list[i]['result']['exit']['time'] - lto_list[i]['result']['enter']['time']
                    
                    telbot.send_constructed_msg('lto', *[lto_list[i]['_id'], lto_list[i]['strategy'], lto_list[i]['pair'], 'exit', oco_limit_orderId, 'filled'])


                elif int(lto_list[i]['exit'][TYPE_OCO]['expire']) <= last_closed_candle_open_time:
                    lto_list[i]['status'] = STAT_EXIT_EXP
                    lto_list[i]['history'].append(lto_list[i]['status'])

                else:
                    # TODO: LOG WARNING
                    pass

            else:
                # TODO: Internal Error
                pass
                
        elif lto_list[i]['status'] == STAT_PART_CLOSED_EXIT:
            # Ignore for the tests
            pass

        else:
            # TODO: Internal Error
            pass

    return trade_list

