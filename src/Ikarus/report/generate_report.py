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
from .report_writer import ReportWriter, GridSearchWriter


def replace_all(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j)
    return text


def get_reporter_name(indice):
    if type(indice[0]) == str:
        return indice[0]
    elif type(indice[0][0]) == str:
        return indice[0][0]
    else:
        return None


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
    pair_pool = list(chain(*pair_pool))

    meta_data_pool = list(itertools.product(time_scale_pool, pair_pool))

    data_dict = await bwrapper.download_all_data(meta_data_pool, start_timestamp, end_timestamp)
    analyzer = Analyzer(config)
    analysis_dict = await analyzer.analyze(data_dict)

    # Indice format: ()
    report_tool_coroutines = []
    indices = []
    for report_tool, report_config in config['report'].items():
        # NOTE: This section is commented out due to the effect of grid_search.py on reporter generation. 
        #if not hasattr(report_tools, report_tool):
        #    continue

        #indice_data = [time_scale_pool, pair_pool]
        if 'analyzers' in report_config:
            indice_data = [time_scale_pool, pair_pool]
            indice_data.append(report_config['analyzers'])
            primal_indices = list(itertools.product(*indice_data))
            indices.extend([[report_tool]+list(indice) for indice in primal_indices])

        elif 'indices' in report_config:
            indices.append([[report_tool]+list(indice) for indice in report_config['indices']])

        elif 'queries' in report_config:
            indices.append([report_tool])

        elif 'indice_template' in report_config:
            # NOTE: For now indice_template value looks meaningless
            indice_data = [pair_pool, time_scale_pool]
            indice_data.append(list(config['analysis'].keys()))
            primal_indices = list(itertools.product(*indice_data))
            indices.append([[report_tool]+list(indice) for indice in primal_indices])


    for indice in indices:
        #timeframe, symbol, analyzer
        reporter_name = get_reporter_name(indice)
        report_config = config['report'].get(reporter_name) # The first indice is always the name of the reporter
        source = report_config.get('source', 'analyzer')
        

        if source == 'database':
            if 'indices' in report_config.keys():
                pass
            elif 'analyzers' in report_config.keys():
                report_tool_coroutines.append(mongo_utils.do_find_report(mongo_client, report_tool, {'pair':symbol,'timeframe':timeframe,'analyzer':analyzer}))
            elif 'queries' in report_config.keys():
                report_tool_coroutines.append(mongo_utils.do_aggregate_multi_query(mongo_client, report_config.get('collection', report_config), report_config['queries']))

        elif source == 'analyzer':
            if 'indice_template' in report_config.keys():
                handler = getattr(report_tools, report_tool)
                analysis_data = [analysis_dict[reporter_indice[1]][reporter_indice[2]][reporter_indice[3]] for reporter_indice in indice]
                report_tool_coroutines.append(handler(indice, analysis_data)) # Use indices as the index

            elif 'indices' in report_config.keys():
                handler = getattr(report_tools, report_tool)
                analysis_data = [analysis_dict[reporter_indice[1]][reporter_indice[2]][reporter_indice[3]] for reporter_indice in indice]
                report_tool_coroutines.append(handler(report_config['indices'], analysis_data)) # Use indices as the index

            elif 'analyzers' in report_config.keys():
                report_tool, timeframe, symbol, analyzer = indice
                #if analyzer not in analysis_dict[symbol][timeframe].keys():
                #    raise Exception(f'Analyzer not found in analysis_dict: {analyzer}')

                handler = getattr(report_tools, report_tool)
                report_tool_coroutines.append(handler(data_dict[symbol][timeframe].index, analysis_dict[symbol][timeframe][analyzer]))

    # Get the statistics
    report_tool_results = list(await asyncio.gather(*report_tool_coroutines))

    # Write the statistics
    
    report_folder = os.path.dirname(str(sys.argv[1])) + '/' + config.get('report_folder_name', 'reports')
    report_writer = ReportWriter(report_folder, mongo_client)
    async_writers = []
    for indice, report_dict in zip(indices, report_tool_results):
        #reporter, timeframe, symbol, analyzer = indice
        reporter_name = get_reporter_name(indice)

        for writer_type in config['report'][reporter_name].get('writers', []): #shitcode
            if hasattr(report_writer, writer_type):
                kwargs = {}
                if 'plot' in writer_type: 
                    #shitcode
                    # NOTE: Non standart way of providing data
                    kwargs = {
                        'start_time': config['backtest']['start_time'],
                        'end_time': config['backtest']['end_time']
                        #'pair': indice[2],
                        #'timeframe': indice[1]
                    }

                if attr := getattr(report_writer, writer_type)(indice,report_dict,**kwargs):
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

