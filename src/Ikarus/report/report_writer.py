from fileinput import filename
from matplotlib import pyplot as plt
import os
import glob
import pandas as pd
import numpy as np
import shutil

from mdutils.mdutils import MdUtils
from mdutils import Html

import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import AxesGrid

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
    def __init__(self, mongo_client, report_folder='reports') -> None:
        self.mongo_client = mongo_client
        self.report_folder = report_folder
        pass

    def create_report_folder(self):
        if not os.path.exists(self.report_folder):
            os.makedirs(self.report_folder)

    async def database(self, indice, report_dict):
        document = {
            'folder_name': os.path.basename(str(self.report_folder)),
            'timeframe': indice[1],
            'pair': indice[2],
            'analyzer': indice[3],
            'data': report_dict
        }
        await self.mongo_client.do_insert_one(indice[0],document)
        #await mongocli.do_insert_one("observer", initial_observation_item)

class GridSearchWriter():
    def __init__(self, report_folder='reports') -> None:
        self.report_folder = report_folder
        pass

    async def heatmap_w_sub_matrices(self, indice, query_results):
        #(self, sub_matrices, labels, title, footnote):

        sub_matrices = []
        for query_result in query_results:
            for mongo_dict in query_result:
                _,x,y = mongo_dict['folder_name'].split('_')
                mongo_dict['validation_threshold'] = x
                mongo_dict['timeperiod'] = y
            
            df = pd.DataFrame(query_result)
            tabular_df = pd.DataFrame(np.nan,index=df['timeperiod'].unique(), columns=df['validation_threshold'].unique())

            for result in query_result:
                if 'ppc' in result.keys():
                    tabular_df[result['validation_threshold']][result['timeperiod']] = result['ppc']

            sub_matrices.append(tabular_df.values)

        #########
        #plot_custom(sub_matrices, market_regimes, analyzers, tabular_df.columns.to_list(), tabular_df.index.to_list())
        # TODO: NEXT Find a way to get following variables to here:
        # market_regimes, analyzers
        x_labels, y_labels, sub_x_labels, sub_y_labels = tabular_df.columns.to_list()
        fig = plt.figure(figsize=(18,10))
        fig.suptitle(title, fontsize=24)

        grid = AxesGrid(fig, 111,
                        nrows_ncols=(len(y_labels), len(x_labels)),
                        axes_pad=0.05,
                        share_all=True,
                        label_mode="L",
                        cbar_location="right",
                        cbar_mode="single",
                        )

        for idx, (matrice, ax) in enumerate(zip(sub_matrices,grid)):
            if idx < len(x_labels):
                ax2 = ax.secondary_xaxis('top')
                ax2.tick_params(axis='x')
                ax2.set_xticks(np.arange(len(sub_x_labels)), sub_x_labels, minor=False)
                ax2.set_xlabel(x_labels[idx])

            else:
                ax.set_xticks([])

            if idx % len(y_labels) == 0:
                ax.set_ylabel(y_labels[idx % len(y_labels)])

            ax.set_yticks(np.arange(len(sub_y_labels)), sub_y_labels)
            im = ax.imshow(matrice, vmin=0, vmax=100)

        grid.cbar_axes[0].colorbar(im)

        #for cax in grid.cbar_axes:
        #    cax.toggle_label(False)
        #reporter, timeframe, symbol, analyzer = indice
        #filename = '{}_{}_{}_{}'.format(reporter,timeframe,symbol,analyzer)
        target_path = '{}/{}.png'.format(self.report_folder,title)
        plt.figtext(0.1, 0.1, footnote, ha="left", fontsize=12)
        plt.savefig(target_path, bbox_inches='tight')


class ReportWriter(ImageWriter, MarkdownWriter, DatabaseWriter, GridSearchWriter):
    def __init__(self, report_folder='', mongo_client=None) -> None:
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