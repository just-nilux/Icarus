import asyncio
from binance import Client, AsyncClient, BinanceSocketManager
from datetime import datetime, timedelta
import json
from Ikarus import Ikarus, Algorithm, Notification, Analyzer, Observer, MongoUtils
import logging
from logging.handlers import TimedRotatingFileHandler
import pandas as pd

credential_file = r'./test_credentials.json'
with open(credential_file, 'r') as cred_file:
    cred_info = json.load(cred_file)

# Global Variables
SYSTEM_STATUS = 0
STATUS_TIMEOUT = 0
test_time_scales = [Client.KLINE_INTERVAL_15MINUTE, Client.KLINE_INTERVAL_1HOUR]
test_time_lengths_str = ["1 day", "1 week"]
test_time_df = pd.DataFrame({"scale":test_time_scales, "length":test_time_lengths_str})

logger = logging.getLogger('app')

mongocli = MongoUtils.MongoClient("localhost", 27017)

class MyFormatter(logging.Formatter):
    def format(self, record):
        record.message2 = record.args.get("message2")
        return super().format(record)

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
    formatter = logging.Formatter('[{}] [{}] [{}] [{}]'.format('%(asctime)s','%(name)21s','%(levelname)8s', '%(message)s'))
    
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
    logger.debug('Application started')
    pair_list = ["BTCUSDT","XRPUSDT","BTTUSDT"]

    # Phase 1: Perform pre-calculation tasks
    logger.info('pre-calculation phase started')
    tasks_pre_calc = ikarus.get_current_balance(), ikarus.get_data_dict(pair_list,test_time_df)
    balance, data_dict = await asyncio.gather(*tasks_pre_calc)
    logger.info("Balance: $ {}".format(balance['ref_balance'].sum()))

    # Phase 2: Perform calculation tasks
    logger.info('calculation phase started')
    analyzer, algorithm = Analyzer.Analyzer(), Algorithm.Algorithm()
    analysis_obj = await asyncio.create_task(analyzer.sample_analyzer(data_dict))
    trade_obj = await asyncio.create_task(algorithm.sample_algorithm(analysis_obj))
    if len(trade_obj):
        exec_status = await asyncio.create_task(ikarus.execute_decision(trade_obj))
        # TODO: Handle exec_status to do sth in case of failure (like sending notification)
        await mongocli.insert_many("live-trades",trade_obj)

    
    # Phase 3: Perform post-calculation tasks
    logger.info('post-calculation phase started')
    observation_obj = await observer.default_observer(balance,analysis_obj)
    await mongocli.insert("observations",observation_obj)   

    logger.debug('Application ended')
    return True


async def main(period):
    global SYSTEM_STATUS, STATUS_TIMEOUT

    client = await AsyncClient.create(api_key=cred_info['Binance']['Production']['PUBLIC-KEY'],
                                      api_secret=cred_info['Binance']['Production']['SECRET-KEY'])

    # bm = BinanceSocketManager(client)
    ikarus = Ikarus.Ikarus(client)

    telbot = Notification.TelegramBot(cred_info['Telegram']['Token'], cred_info['Telegram']['ChatId'])
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

        except Exception as e:
            if STATUS_TIMEOUT != 1:
                logger.error(str(e))
                STATUS_TIMEOUT = 1
                #telbot.send('Exception: STATUS_TIMEOUT')

    await client.close_connection()

if __name__ == "__main__":
    setup_logger()
    observer = Observer.Observer()

    logger.info("---------------------------------------------------------")
    logger.info("------------------- Engine Restarted --------------------")
    logger.info("---------------------------------------------------------")
    period = 5
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(period))
    print("Completed")