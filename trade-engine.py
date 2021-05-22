import asyncio
from binance import Client, AsyncClient, BinanceSocketManager
from datetime import datetime, timedelta
import json
from Ikarus import Ikarus, Algorithms, Notification, Analyzer
import logging
from logging.handlers import TimedRotatingFileHandler


credential_file = r'./test_credentials.json'
with open(credential_file, 'r') as cred_file:
    cred_info = json.load(cred_file)

# Global Variables
SYSTEM_STATUS = 0
STATUS_TIMEOUT = 0
logger = logging.getLogger('app')


def setup_logger():
    global logger
    log_filename = 'log/ikarus-app.log'
    logger = logging.getLogger('app')
    logger.setLevel(logging.DEBUG)

    rfh = TimedRotatingFileHandler(filename=log_filename,
                                   when='H',
                                   interval=1,
                                   backupCount=5)

    rfh.setLevel(logging.DEBUG)

    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)

    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    rfh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(rfh)
    logger.addHandler(ch)

    logger.info('logger has been set')


async def wait_until(dt):
    now = int(datetime.timestamp(datetime.now()))
    sleep_time = dt - now
    print("dt:{}, now:{}, sleeptime:{}".format(dt,now,sleep_time))
    await asyncio.sleep(dt - now)


async def run_at(dt, coro):
    await wait_until(dt)
    return await coro


async def application(ikarus, telbot):
    logger.debug('Application started: {}'.format(str(datetime.now())))
    prev_time = int(datetime.timestamp(datetime.now() - timedelta(minutes=60))) * 1000
    now_time = int(datetime.timestamp(datetime.now())) * 1000

    # Get multiple klines
    pair_list = ["BTCUSDT"]
    klines = await ikarus.get_all_klines(pair_list, prev_time, now_time)
    logger.debug('Klines obtained with length: {}'.format(len(klines)))

    analysis_objs = await asyncio.create_task(Analyzer.default_analyzer(pair_list))
    trade_objs = await asyncio.create_task(Algorithms.default_algorithm(analysis_objs))
    exec_status = await asyncio.create_task(ikarus.execute_decision(trade_objs))
    #tasks = ikarus.update_db(), ikarus.monitor_account()
    #a, b = await asyncio.gather(*tasks)
    #if not b:
    #    await asyncio.create_task(telbot(b))

    logger.debug('Application ended: {}'.format(str(datetime.now())))
    return True


async def main(period):
    global SYSTEM_STATUS, STATUS_TIMEOUT

    client = await AsyncClient.create(api_key=cred_info['Binance']['Production']['PUBLIC-KEY'],
                                      api_secret=cred_info['Binance']['Production']['SECRET-KEY'])

    # bm = BinanceSocketManager(client)
    ikarus = Ikarus.Ikarus(client)

    telbot = Notification.TelegramBot(cred_info['Telegram']['Token'], cred_info['Telegram']['ChatId'])
    balance = await ikarus.get_current_balance()
    print(balance)
    print(balance['ref_balance'].sum())
    while True:
        try:
            sys_stat = await asyncio.wait_for(client.get_system_status(), timeout=5)
            print(sys_stat)
            server_time = await client.get_server_time()
            # sys_stat ve server time gather() edilebilir

            # Check system status
            if sys_stat['status'] != 0:
                if SYSTEM_STATUS != 1:
                    SYSTEM_STATUS = 1
                    telbot.send('Exception: SYSTEM_STATUS')
                await asyncio.sleep(period)
                continue
            else:
                SYSTEM_STATUS = 0

            STATUS_TIMEOUT = 0
            '''
            start_ts = int(server_time['serverTime']/1000)
            start_ts = start_ts - (start_ts % 60) + 61  # 1 minute 1 second ahead
            result = await asyncio.create_task(run_at(start_ts, application(ikarus, client, telbot)))
            '''

            await asyncio.gather(
                asyncio.sleep(period),
                application(ikarus, telbot),
            )

        except:
            if STATUS_TIMEOUT != 1:
                logger.error('Exception occured: STATUS_TIMEOUT 1')
                STATUS_TIMEOUT = 1
                #telbot.send('Exception: STATUS_TIMEOUT')

    await client.close_connection()

if __name__ == "__main__":
    setup_logger()
    logger.info("------------------- Engine Restarted --------------------")
    period = 5
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(period))
    print("Completed")