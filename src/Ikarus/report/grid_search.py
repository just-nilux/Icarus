from copy import deepcopy
import sys
import json
import itertools
import os
import ast
import argparse


def write_to_config_file(config_dict, filename="/config.json"):
    f = open(os.path.dirname(str(sys.argv[1])) + filename,'w')
    json.dump(config_dict, f,  indent=4)
    f.close()


def generate_reporter_config():
    # Generate temporary report items
    config['mongodb']['clean'] = False
    config['report'] = {}
    for reporter_name, reporter_config in config['grid_search']['generate_report_item'].items():
        reporter = {}
        reporter['source'] = 'database'
        reporter['collection'] = reporter_config['collection']
        reporter['queries'] = generate_queries(reporter_config)
        reporter['writers'] = reporter_config['writers']
        config['report'][reporter_name] = reporter
    
    config['report_folder_name'] = f'reports_grid_search'
    write_to_config_file(config, '/config_generated.json')

    #print('\033[32m' + f'Auto-generated report items : {config["report_folder_name"]}\033[90m')
    #os.system('cd C:\\Users\\bilko\\PycharmProjects\\trade-bot')
    #os.system(f'python -m src.Ikarus.report.generate_report  {str(sys.argv[1])}')       
    

def grid_search():
    parameters = list(config['grid_search']['grid'].keys())
    grid_values = list(config['grid_search']['grid'].values())

    grid_configs = list(itertools.product(*grid_values))

    for config_idx, grid_config in enumerate(grid_configs):
        # Edit config file
        for analyzer_name in config['grid_search']['analyzers']:
            if analyzer_name not in config['analysis'].keys():
                continue

            for idx in range(len(parameters)):
                config['analysis'][analyzer_name][parameters[idx]] = grid_config[idx]
        
        folder_suffix = '_'.join([str(gc) for gc in grid_config])
        
        config['report_folder_name'] = f'reports_{folder_suffix}'

        # Do not clean the db between different configs
        if config_idx != 0:
            config['mongodb']['clean'] = False

        write_to_config_file(config)
        
        print('\033[32m' + f'[{config_idx+1}/{len(grid_configs)}] : {config["report_folder_name"]}\033[90m')
        os.system('cd C:\\Users\\bilko\\PycharmProjects\\trade-bot')
        os.system(f'python -m src.Ikarus.report.generate_report  {str(sys.argv[1])}')


def generate_queries(reporter_config):
    grid_configs = list(itertools.product(*reporter_config['parameters'].values()))

    queries = []
    for grid_config in grid_configs:
        query = deepcopy(reporter_config['query_template'])
        for key_idx, key in enumerate(reporter_config['parameters'].keys()):
            query = ast.literal_eval(str(query).replace(key, grid_config[key_idx]))
        queries.append(query)
    return queries


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('config_file')
    parser.add_argument('--generate-reporters', nargs="?", default=False)
    args = parser.parse_args()

    f = open(str(args.config_file),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)
    config_original = deepcopy(config)

    if not args.generate_reporters:
        grid_search()

    if config['grid_search'].get('generate_report_item',None):
        generate_reporter_config()

    # Rewrite the original back
    write_to_config_file(config_original)
