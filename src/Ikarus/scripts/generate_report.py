import json
import sys
import os
import asyncio
from binance import AsyncClient
from .. import broker
import datetime
from itertools import chain
import itertools
from ..analyzers import Analyzer
from .. import mongo_utils
from . import report_tools
from .report_writer import ReportWriter


async def main():

    client = await AsyncClient.create(api_key=cred_info['Binance']['Test']['PUBLIC-KEY'],
                                    api_secret=cred_info['Binance']['Test']['SECRET-KEY'])
    bwrapper = broker.TestBinanceWrapper(client, config)
    mongo_client = mongo_utils.MongoClient(db='reports', **config['mongodb'])
    start_time = datetime.datetime.strptime(config['backtest']['start_time'], "%Y-%m-%d %H:%M:%S")
    start_timestamp = int(datetime.datetime.timestamp(start_time))*1000
    end_time = datetime.datetime.strptime(config['backtest']['end_time'], "%Y-%m-%d %H:%M:%S")
    end_timestamp = int(datetime.datetime.timestamp(end_time))*1000

    # Create pools for pair-scales
    time_scale_pool = []
    pair_pool = []
    for strategy in config['strategy'].values():
        time_scale_pool.append(strategy['time_scales'])
        pair_pool.append(strategy['pairs'])

    time_scale_pool = list(set(chain(*time_scale_pool)))
    pair_pool = list(set(chain(*pair_pool)))

    meta_data_pool = list(itertools.product(time_scale_pool, pair_pool))

    data_dict = await bwrapper.download_all_data(meta_data_pool, start_timestamp, end_timestamp)
    analyzer = Analyzer(config)
    analysis_dict = await analyzer.analyze(data_dict)

    # Indice format: ()
    report_tool_coroutines = []
    indices = []
    for report_tool, report_config in config['report'].items():
        if not hasattr(report_tools, report_tool):
            continue

        primal_indices = list(itertools.product(*[time_scale_pool, pair_pool, report_config['analyzers']]))
        indices.extend([[report_tool]+list(indice) for indice in primal_indices])

        for timeframe, symbol, analyzer in primal_indices:
            source = report_config.get('source', 'analyzer')
            
            if source == 'database':
                # aggregate([{"$match":{'pair':'ETHUSDT','timeframe':'1d','analyzer':'market_class_fractal_aroon'}}, {"$project": {"data": "$data"}}])
                report_tool_coroutines.append(mongo_utils.do_find_report(mongo_client, report_tool, {'pair':symbol,'timeframe':timeframe,'analyzer':analyzer}))
            
            elif source == 'analyzer' and (analyzer in analysis_dict[symbol][timeframe].keys()):
                handler = getattr(report_tools, report_tool)
                report_tool_coroutines.append(handler(data_dict[symbol][timeframe].index, analysis_dict[symbol][timeframe][analyzer]))

    # Get the statistics
    report_tool_results = list(await asyncio.gather(*report_tool_coroutines))

    # Write the statistics
    report_writer = ReportWriter(os.path.dirname(str(sys.argv[1])), mongo_client)
    async_writers = []
    for indice, report_dict in zip(indices, report_tool_results):
        reporter, timeframe, symbol, analyzer = indice

        for writer_type in config['report'][reporter]['writers']:
            if hasattr(report_writer, writer_type):
                if attr := getattr(report_writer, writer_type)(indice,report_dict):
                    async_writers.append(attr)

    await asyncio.gather(*async_writers)
    report_writer.add_images()

    report_writer.md_file.create_md_file()
    pass

if __name__ == '__main__':
    print(sys.argv)
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

