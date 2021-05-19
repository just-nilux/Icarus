import asyncio
from binance import Client, AsyncClient, BinanceSocketManager
from datetime import datetime, timedelta
import json
from Ikarus import Ikarus, Algorithms, Notification
import logging
from logging.handlers import TimedRotatingFileHandler


credential_file = r'./test_credentials.json'
with open(credential_file, 'r') as cred_file:
    cred_info = json.load(cred_file)

# Global Variables
SYSTEM_STATUS = 0
STATUS_TIMEOUT = 0


def setup_logger():
    # create logger with 'spam_application'
    log_filename = 'log/ikarus-app.log'
    logger = logging.getLogger('app')
    logger.setLevel(logging.DEBUG)
    # create file handler which logs even debug messages
    #fh = logging.FileHandler(log_filename)
    rfh = TimedRotatingFileHandler(filename=log_filename,
                                   when='m',
                                   interval=1,
                                   backupCount=5)

    #rfh.rotation_filename = filer
    rfh.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    rfh.setFormatter(formatter)
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(rfh)
    logger.addHandler(ch)

    logger.info('logger has been set')

    logger = logging.getLogger()



async def wait_until(dt):
    now = int(datetime.timestamp(datetime.now()))
    sleep_time = dt - now
    print("dt:{}, now:{}, sleeptime:{}".format(dt,now,sleep_time))
    await asyncio.sleep(dt - now)


async def run_at(dt, coro):
    await wait_until(dt)
    return await coro



async def application(ikarus, client, telbot):

    print('Application started:', str(datetime.now()))

    prev_time = int(datetime.timestamp(datetime.now() - timedelta(minutes=60))) * 1000
    now_time = int(datetime.timestamp(datetime.now())) * 1000

    # Get multiple klines
    pair_list = ["BTCUSDT","XRPUSDT"]
    klines = await ikarus.get_all_klines(client, pair_list, prev_time, now_time)
    print(len(klines), len(klines[0]), len(klines[1]))

    decision = await asyncio.create_task(Algorithms.empty_algorithm(pair_list, klines[0]))
    if decision['operation'] is not None:
        exec_status = await asyncio.create_task(ikarus.exec_decision(decision))
    tasks = ikarus.update_db(), ikarus.monitor_account()
    a, b = await asyncio.gather(*tasks)

    if not b:
        await asyncio.create_task(telbot(b))

    print('Application ended:', str(datetime.now()))
    return True


async def main(period):
    global SYSTEM_STATUS, STATUS_TIMEOUT

    client = await AsyncClient.create(api_key=cred_info['Binance']['Production']['PUBLIC-KEY'],
                                      api_secret=cred_info['Binance']['Production']['SECRET-KEY'])

    bm = BinanceSocketManager(client)
    ikarus = Ikarus.Ikarus()
    await ikarus.logger_test()

    telbot = Notification.TelegramBot(cred_info['Telegram']['Token'], cred_info['Telegram']['ChatId'])
    balance = await ikarus.get_current_balance(client)
    print(balance)
    print(balance['ref_balance'].sum())
    while True:
        try:
            sys_stat = await asyncio.wait_for(client.get_system_status(), timeout=5)
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

            STATUS_TIMEOUT=0
            start_ts = int(server_time['serverTime']/1000)
            start_ts = start_ts - (start_ts % 60) + 61  # 1 minute 1 second ahead
            result = await asyncio.create_task(run_at(start_ts, application(ikarus, client, telbot)))

            '''
            await asyncio.gather(
                asyncio.sleep(period),
                application(ikarus, client, telbot),
            )
            '''
        except:
            if STATUS_TIMEOUT != 1:
                print("EXCEPTION")
                STATUS_TIMEOUT = 1
                telbot.send('Exception: STATUS_TIMEOUT')

    await client.close_connection()

if __name__ == "__main__":
    setup_logger()
    period = 60
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(period))
    print("Completed")