from fileinput import filename
from matplotlib import pyplot as plt
import os
import glob
import pandas as pd
import numpy as np
import shutil

from mdutils.mdutils import MdUtils
from mdutils import Html

class ImageWriter():
    def __init__(self, report_folder) -> None:
        super().__init__()
        self.report_folder = report_folder

    def box_plot(self, indice, report_dict):
        reporter, timeframe, symbol, analyzer = indice
        filename = '{}_{}_{}_{}'.format(reporter,timeframe,symbol,analyzer)
        target_path = '{}/{}'.format(self.report_folder,filename)

        fig, ax = plt.subplots()

        ax.set_title(filename)

        bplot = ax.boxplot(report_dict.values(), patch_artist=True)
        plt.grid(True)
        ax.set_xticklabels(report_dict.keys())

        colors = ['pink', 'lightblue', 'lightgreen']

        for patch, color in zip(bplot['boxes'], colors):
            patch.set_facecolor(color)
        plt.savefig(target_path, bbox_inches='tight')

    def table_plot(self, indice, report_dict):
        reporter, timeframe, symbol, analyzer = indice
        filename = '{}-{}-{}-{}'.format(reporter,timeframe,symbol,analyzer)
        report_path = '{}/{}'.format(self.report_folder,filename)

        df = pd.DataFrame(data=report_dict)
        # print(df.to_markdown()) # TODO: How to automate dumping this table
        rcolors = plt.cm.BuPu(np.full(len(df.index), 0.1))
        ccolors = plt.cm.BuPu(np.full(len(df.columns), 0.1))
        fig, ax = plt.subplots() 
        ax.set_axis_off() 
        table = ax.table( 
            cellText = df.values,  
            rowLabels = df.index,  
            colLabels = df.columns, 
            rowColours =rcolors,  
            colColours =ccolors, 
            cellLoc ='center',  
            loc ='upper left')
        ax.set_title(filename, fontweight ="bold")
        plt.tight_layout()
        plt.savefig(report_path, bbox_inches='tight')


class MarkdownWriter():
    def __init__(self, report_folder) -> None:
        self.report_folder = report_folder
        self.md_file = MdUtils(file_name=f'{self.report_folder}/report.md', title='Report')
        pass

    def add_images(self):
        png_file_names = [os.path.basename(png_file) for png_file in glob.glob(f'{self.report_folder}/*.png')]
        self.md_file.new_header(1, "Plots")
        for png_file_name in png_file_names:
            self.md_file.write(png_file_name, color='yellow', bold_italics_code='b')
            self.md_file.new_paragraph(Html.image(path=png_file_name))
            self.md_file.write(" \n\n")


    def markdown_table(self, indice, report_dict):
        reporter, timeframe, symbol, analyzer = indice
        title = '{}_{}_{}_{}'.format(reporter,timeframe,symbol,analyzer)
        df = pd.DataFrame(data=report_dict)
        self.md_file.write(title, color='yellow', bold_italics_code='b')
        self.md_file.write('\n' + df.to_markdown() + '\n\n')
        pass

class DatabaseWriter():
    # TODO: Find a way to overright existing content or check if this mechanism needed
    def __init__(self, mongo_client) -> None:
        self.mongo_client = mongo_client
        pass

    def create_report_folder(self):
        if not os.path.exists(self.report_folder):
            os.makedirs(self.report_folder)

    async def database(self, indice, report_dict):
        document = {
            'timeframe': indice[1],
            'pair': indice[2],
            'analyzer': indice[3],
            'data': report_dict
        }
        await self.mongo_client.do_insert_one(indice[0],document)
        #await mongocli.do_insert_one("observer", initial_observation_item)


class ReportWriter(ImageWriter, MarkdownWriter, DatabaseWriter):
    def __init__(self, report_folder, mongo_client) -> None:
        self.report_folder = report_folder
        self.clean_report_folder()
        self.create_report_folder()
        self.md_file = MdUtils(file_name=f'{self.report_folder}/report.md', title='Markdown File Example')
        
        self.mongo_client = mongo_client


    def create_report_folder(self):
        if not os.path.exists(self.report_folder):
            os.makedirs(self.report_folder)


    def clean_report_folder(self):
        if os.path.exists(self.report_folder):
            shutil.rmtree(self.report_folder)