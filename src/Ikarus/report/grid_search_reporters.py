from copy import deepcopy
import sys
import json
import itertools
import os
import ast
import argparse


def write_to_config_file(config_dict, filename="/config.json"):
    config_file_path = os.path.dirname(str(sys.argv[1])) + filename
    f = open(config_file_path,'w')
    json.dump(config_dict, f,  indent=4)
    f.close()
    return config_file_path

    
def replace_all(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j)
    return text


def generate_queries(reporter_config):
    grid_configs = list(itertools.product(*reporter_config['parameters'].values()))

    queries = []
    for grid_config in grid_configs:
        query = deepcopy(reporter_config['query_template'])
        for key_idx, key in enumerate(reporter_config['parameters'].keys()):
            query = ast.literal_eval(str(query).replace(key, grid_config[key_idx]))
        queries.append(query)
    return queries


def generate_indices(reporter_config):
    grid_configs = list(itertools.product(*reporter_config['parameters'].values()))

    queries = []
    for grid_config in grid_configs:
        query = deepcopy(reporter_config['indice_template'])
        for key_idx, key in enumerate(reporter_config['parameters'].keys()):
            query = ast.literal_eval(str(query).replace(key, grid_config[key_idx]))
        queries.append(query)
    return queries


def grid_search():
    parameters = list(config['grid_search_reporters']['grid'].keys())
    grid_values = list(config['grid_search_reporters']['grid'].values())

    grid_configs = list(itertools.product(*grid_values))

    # First loop is for generating the reporter items but not filling its query templates
    reporter_instances = []
    for grid_config in grid_configs:
        replace_rule = {}
        for param, rep_value in zip(parameters, grid_config):
            replace_rule[param] = rep_value

        for reporter_config in config['grid_search_reporters']['reporters']:    
            replaced_text = replace_all(str(reporter_config), replace_rule)
            reporter_instance = ast.literal_eval(replaced_text)
            reporter_instances.append(reporter_instance)

    # Second loop is for generating the queries for reporters
    config_report = []
    for reporter_instance in reporter_instances:
        reporter = {}
        if 'query_template' in reporter_instance:
            reporter['source'] = reporter_instance['source']
            reporter['reporter'] = reporter_instance['reporter']
            reporter['collection'] = reporter_instance['collection']
            reporter['queries'] = generate_queries(reporter_instance)
            reporter['writers'] = reporter_instance['writers']
            config_report.append(reporter)
        
        elif 'indice_template' in reporter_instance:
            reporter['source'] = reporter_instance['source']
            reporter['reporter'] = reporter_instance['reporter']
            reporter['indices'] = generate_indices(reporter_instance)
            reporter['writers'] = reporter_instance['writers']
            config_report.append(reporter)

    return config_report



    for config_idx, grid_config in enumerate(grid_configs):
        # Edit config file
        for analyzer_name in config['grid_search']['analyzers']:

            for idx in range(len(parameters)):
                config['analysis'][analyzer_name][parameters[idx]] = grid_config[idx]
        
        folder_suffix = '_'.join([str(gc) for gc in grid_config])
        
        config['report_folder_name'] = f'reports_{folder_suffix}'

        # Do not clean the db between different configs
        if config_idx != 0:
            config['mongodb']['clean'] = False

        write_to_config_file(config)
        
        #print('\033[32m' + f'[{config_idx+1}/{len(grid_configs)}] : {config["report_folder_name"]}\033[90m')
        #os.system('cd C:\\Users\\bilko\\PycharmProjects\\trade-bot')
        #os.system(f'python -m src.Ikarus.report.generate_report  {str(sys.argv[1])}')


if __name__ == '__main__':
    f = open(str(sys.argv[1]),'r')
    config = json.load(f)
    
    with open(config['credential_file'], 'r') as cred_file:
        cred_info = json.load(cred_file)

    generated_config_report = grid_search()
    config['mongodb']['clean'] = False
    config['report'] = generated_config_report
    config['report_folder_name'] = f'reports_grid_search_reporters'
    config_file_path = write_to_config_file(config, '/config_grid_search_reporters.json')

    print('\033[32m' + f'[1/1] : {config["report_folder_name"]}\033[90m')
    os.system('cd C:\\Users\\bilko\\PycharmProjects\\trade-bot')
    os.system(f'python -m src.Ikarus.report.generate_report  {config_file_path}')

    
