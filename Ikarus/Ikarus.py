from binance import Client
import asyncio
import pandas as pd
import logging


class Ikarus():

    def __init__(self, _client):
        self.client = _client

        self.logger = logging.getLogger('app.{}'.format(__name__))
        self.logger.info('creating an instance of {}'.format(__name__))

        self.ref_currency = 'USDT'
        self.base_currency = 'TRY'

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

    async def get_all_klines(self, pairs, start_ts, end_ts):
        """[This function returns all of the klines]

        Args:
            pairs ([list]): [List of pairs]
            start_ts ([timestamp]): [description]
            end_ts ([tytimestamppe]): [description]

        Returns:
            [type]: [description]
        """        

        tasks = []
        for pair in pairs:
            task_kline = asyncio.create_task(self.client.get_historical_klines(pair, Client.KLINE_INTERVAL_1MINUTE,
                                                                               start_str=start_ts,
                                                                               end_str=end_ts))
            tasks.append(task_kline)
        return await asyncio.gather(*tasks)

    async def monitor_account(self):

        return True


    async def update_db(self,trade_objs):
        return True


    async def execute_decision(self, trade_objs):
        return True



