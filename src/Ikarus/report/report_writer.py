from fileinput import filename
from matplotlib import pyplot as plt
import os
import glob
import pandas as pd
import numpy as np
import shutil
import math
from mdutils.mdutils import MdUtils
from mdutils import Html

import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import AxesGrid


def get_reporter_name(indice):
    if type(indice[0]) == str:
        return indice[0]
    elif type(indice[0][0]) == str:
        return indice[0][0]
    else:
        return None


class ImageWriter():
    def __init__(self, report_folder) -> None:
        super().__init__()
        self.report_folder = report_folder

    def box_plot(self, indice, report_dict, **kwargs):
        symbol, timeframe, analyzer = indice[0]
        filename = '{}_{}_{}_{}'.format(kwargs['reporter'],timeframe,symbol,analyzer)
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

    def table_plot(self, indice, report_dict, **kwargs):
        symbol, timeframe, analyzer = indice[0]
        filename = '{}_{}_{}_{}'.format(kwargs['reporter'],timeframe,symbol,analyzer)
        target_path = '{}/{}'.format(self.report_folder,filename)

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
        plt.savefig(target_path, bbox_inches='tight')


    def heatmap_plot(self, indice, df, **kwargs):

        x_labels, y_labels = df.columns.to_list(), df.index.to_list()
        fig, ax = plt.subplots(figsize=(12,12))

        #title = get_reporter_name(indice)
        title = kwargs.get('reporter','heatmap_plot')

        fig.suptitle(title, fontsize=24)

        ax.xaxis.tick_top()
        ax.set_xticks(np.arange(len(x_labels)), x_labels, rotation=90)
        ax.set_yticks(np.arange(len(y_labels)), y_labels)

        im = ax.imshow(df.values, cmap='coolwarm', vmin=-1, vmax=1)
        fig.colorbar(im)

        # NOTE: Shitty code
        if df.values.size < 100:
            fontsize = 12
        else:
            fontsize = 4

        for i in range(df.values.shape[0]):
            for j in range(df.values.shape[1]):
                #if not math.isnan(matrice[0, 0]):
                text = ax.text(j, i, "%.2f" % df.values[i, j],
                            ha="center", va="center", color="black", fontsize=fontsize)

        #target_path = '{}/{}.png'.format(self.report_folder,title.replace(' ', '_'))
        target_path = '{}/{}.png'.format(self.report_folder,title)

        # shitcode
        footnote = f"""
        Configuration: {kwargs}
        """

        plt.figtext(0, 0, footnote, ha="left", fontsize=12)
        plt.tight_layout()
        plt.savefig(target_path, bbox_inches='tight', dpi=300)
        print(f'File saved: {target_path}')




class MarkdownWriter():
    def __init__(self, report_folder) -> None:
        self.report_folder = report_folder
        self.md_file = MdUtils(file_name=f'{self.report_folder}/report.md', title='Report')
        pass

    def add_images(self):
        png_file_names = [os.path.basename(png_file) for png_file in glob.glob(f'{self.report_folder}/*.png')]
        self.md_file.new_header(1, "Plots")
        #<img src="../../../../configs/research/aroon_classifies_market/reports_grid_search/PPC_Accuracy.png" /> 
        self.report_folder.split('configs')
        for png_file_name in png_file_names:
            self.md_file.write(png_file_name, color='yellow', bold_italics_code='b')
            self.md_file.new_paragraph(Html.image(path=png_file_name))
            self.md_file.write(" \n\n")


    def markdown_table(self, indice, report_dict, **kwargs):
        timeframe, symbol, analyzer = indice[0]
        title = '{}_{}_{}_{}'.format(kwargs.get('reporter',''),timeframe,symbol,analyzer)
        df = pd.DataFrame(data=report_dict)
        self.md_file.write(title, color='yellow', bold_italics_code='b')
        self.md_file.write('\n' + df.to_markdown() + '\n\n')
        pass

class DatabaseWriter():
    def __init__(self, mongo_client, report_folder='reports') -> None:
        self.mongo_client = mongo_client
        self.report_folder = report_folder
        pass

    def create_report_folder(self):
        if not os.path.exists(self.report_folder):
            os.makedirs(self.report_folder)

    async def database(self, indice, report_dict, **kwargs):
        symbol, timeframe, analyzer = indice[0]
        document = {
            'folder_name': os.path.basename(str(self.report_folder)),
            'timeframe': timeframe,
            'pair': symbol,
            'analyzer': analyzer,
            'data': report_dict
        }
        await self.mongo_client.do_insert_one(kwargs['reporter'], document)
        #await mongocli.do_insert_one("observer", initial_observation_item)

class GridSearchWriter():
    def __init__(self, report_folder='reports') -> None:
        self.report_folder = report_folder
        pass

    async def heatmap_w_sub_matrices_plot(self, indice, query_results, **kwargs):
        # shitcode
        sub_matrices = []
        analyzers = list()
        market_regimes = list()
        for query_result in query_results:
            for mongo_dict in query_result:
                _,x,y = mongo_dict['folder_name'].split('_')
                mongo_dict['validation_threshold'] = x
                mongo_dict['timeperiod'] = y

                if mongo_dict['analyzer'] not in analyzers: analyzers.append(mongo_dict['analyzer'])
                if mongo_dict['market_regime'] not in market_regimes: market_regimes.append(mongo_dict['market_regime'])

                #analyzers.add(mongo_dict.get('analyzer'))
                #market_regimes.add(mongo_dict.get('market_regime'))

            
            df = pd.DataFrame(query_result)
            tabular_df = pd.DataFrame(np.nan,index=df['timeperiod'].unique(), columns=df['validation_threshold'].unique())

            for result in query_result:
                if 'value' in result.keys():
                    tabular_df[result['validation_threshold']][result['timeperiod']] = result['value']

            sub_matrices.append(tabular_df.values)

        max_limit, min_limit = 0, 0
        for matrice in sub_matrices:
            max_index = np.unravel_index(matrice.argmax(), matrice.shape)
            min_index = np.unravel_index(matrice.argmin(), matrice.shape)
            if max_limit < matrice[max_index]: max_limit = matrice[max_index]
            if min_limit > matrice[min_index]: min_limit = matrice[min_index]

        #########
        #plot_custom(sub_matrices, market_regimes, analyzers, tabular_df.columns.to_list(), tabular_df.index.to_list())
        x_labels, y_labels, sub_x_labels, sub_y_labels = list(market_regimes), list(analyzers), tabular_df.columns.to_list(), tabular_df.index.to_list()
        fig = plt.figure(figsize=(18,10))

        #title = f"{indice[0]}-{kwargs.get('pair','pair')}-{kwargs.get('timeframe','timeframe')}" # Name of the reporter
        #title = '-'.join([str(idc) for idc in indice])
        title = kwargs.get('reporter','heatmap_w_sub_matrices_plot')


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
                ax.set_ylabel(y_labels[int(idx / len(y_labels))])
                #ax.set(ylabel=y_labels[idx % len(y_labels)])


            ax.set_yticks(np.arange(len(sub_y_labels)), sub_y_labels)
            im = ax.imshow(matrice, cmap='YlGn' ,vmin=min_limit, vmax=max_limit)

            for i in range(matrice.shape[0]):
                for j in range(matrice.shape[1]):
                    if not math.isnan(matrice[0, 0]):
                        text = ax.text(j, i, "%.2f" % matrice[i, j],
                                    ha="center", va="center", color="black")

        grid.cbar_axes[0].colorbar(im)

        #for cax in grid.cbar_axes:
        #    cax.toggle_label(False)
        #reporter, timeframe, symbol, analyzer = indice
        #filename = '{}_{}_{}_{}'.format(reporter,timeframe,symbol,analyzer)
        target_path = '{}/{}.png'.format(self.report_folder,title.replace(' ', '_'))

        # shitcode
        footnote = f"""
        Format: (market_regime x analyzer) x (validation_threshold x timeperiod)
        Configuration: {kwargs}
        """

        plt.figtext(0.1, 0.1, footnote, ha="left", fontsize=12)
        plt.savefig(target_path, bbox_inches='tight')
        print(f'File saved: {target_path}')


class ReportWriter(ImageWriter, MarkdownWriter, DatabaseWriter, GridSearchWriter):
    def __init__(self, report_folder='', mongo_client=None, **kwargs) -> None:
        self.report_folder = report_folder
        self.clean_report_folder()
        self.create_report_folder()
        self.md_file = MdUtils(file_name=f'{self.report_folder}/report.md', title='Markdown File Example')
        self.mongo_client = mongo_client
        self.kwargs = kwargs

    def create_report_folder(self):
        if not os.path.exists(self.report_folder):
            os.makedirs(self.report_folder)


    def clean_report_folder(self):
        if os.path.exists(self.report_folder):
            shutil.rmtree(self.report_folder)