import json
import sys
import asyncio
from binance import AsyncClient
from .. import broker
import datetime
from itertools import chain
import itertools
from ..analyzers import Analyzer
from . import report_tools
from .report_writer import ImageWriter, DatabaseWriter, MarkdownWriter


async def main():

    client = await AsyncClient.create(api_key=cred_info['Binance']['Test']['PUBLIC-KEY'],
                                    api_secret=cred_info['Binance']['Test']['SECRET-KEY'])
    bwrapper = broker.TestBinanceWrapper(client, config)
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



    # meta_data_pool x report_tools
    report_tool_coroutines = []
    for report_tool, report_config in config['report'].items():
        if not hasattr(report_tools, report_tool):
            continue

        indices = list(itertools.product(*[time_scale_pool, pair_pool, report_config['analyzers']]))
        indices = [[report_tool]+list(indice) for indice in indices]
        for _, timeframe, symbol, analyzer in indices:
            if analyzer in analysis_dict[symbol][timeframe].keys():
                handler = getattr(report_tools, report_tool)
                report_tool_coroutines.append(handler(data_dict[symbol][timeframe].index, analysis_dict[symbol][timeframe][analyzer]))

    # Get the statistics
    report_tool_results = list(await asyncio.gather(*report_tool_coroutines))

    # Write the statistics
    report_image_writer = ImageWriter('path')
    report_database_writer = DatabaseWriter()
    report_markdown_writer = MarkdownWriter()
    for indice, report_dict in zip(indices, report_tool_results):
        reporter, timeframe, symbol, analyzer = indice

        for writer_type in config['report'][reporter]['writers']:
            if writer_type == 'image':
                report_image_writer.write(indice,report_dict)
            elif writer_type == 'markdown':
                report_markdown_writer.write(indice,report_dict)
            elif writer_type == 'database':
                report_database_writer.write(indice,report_dict)
    pass

if __name__ == '__main__':
    print(sys.argv)
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

