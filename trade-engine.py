import asyncio
from binance import Client, AsyncClient, BinanceSocketManager
from datetime import datetime, timedelta
import json
from Ikarus import Ikarus, Algorithm, Notification, Analyzer, Observer
import logging
from logging.handlers import TimedRotatingFileHandler


credential_file = r'./test_credentials.json'
with open(credential_file, 'r') as cred_file:
    cred_info = json.load(cred_file)

# Global Variables
SYSTEM_STATUS = 0
STATUS_TIMEOUT = 0
logger = logging.getLogger('app')

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
    formatter = logging.Formatter('[{}] [{}] [{}] [{}]'.format('%(asctime)s','%(name)20s','%(levelname)8s', '%(message)s'))
    
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
    tasks_pre_calc = ikarus.get_current_balance(), ikarus.get_data_dict(pair_list)
    balance, data_dict = await asyncio.gather(*tasks_pre_calc)
    logger.info("Balance: $ {}".format(balance['ref_balance'].sum()))

    # Phase 2: Perform calculation tasks
    logger.info('calculation phase started')
    analyzer, algorithm = Analyzer.Analyzer(), Algorithm.Algorithm()
    analysis_objs = await asyncio.create_task(analyzer.sample_analyzer(data_dict))
    trade_objs = await asyncio.create_task(algorithm.default_algorithm(analysis_objs))
    exec_status = await asyncio.create_task(ikarus.execute_decision(trade_objs))
    
    # Phase 3: Perform post-calculation tasks
        
    # TODO: exec_status needs to be checked and required actions needs to be taken
    logger.info('post-calculation phase started')
    observer = Observer.Observer()
    observation_obj = await observer.default_observer(balance,analysis_objs)
    tasks_post_calc = ikarus.update_db({"trade":trade_objs, "observation": observation_obj}), ikarus.monitor_account()

    a, b = await asyncio.gather(*tasks_post_calc)

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
    logger.info("---------------------------------------------------------")
    logger.info("------------------- Engine Restarted --------------------")
    logger.info("---------------------------------------------------------")
    period = 5
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(period))
    print("Completed")