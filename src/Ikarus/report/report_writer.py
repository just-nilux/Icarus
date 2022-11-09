from matplotlib import pyplot as plt
import os
import glob
import pandas as pd
import numpy as np
import shutil
import math
from mdutils.mdutils import MdUtils
from mdutils import Html

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import AxesGrid

import mplfinance as mpf

def get_reporter_name(indice):
    
    if type(indice[0]) == str:
        return indice[0]
    elif type(indice[0][0]) == str:
        return indice[0][0]
    else:
        return None

def evaluate_min_max_limits(df):
    if type(df) == pd.DataFrame:
        values = df.values
    else:
        values = df

    if (values<=1).all():
        if (values>=0).all():
            return 0, 1
        elif (values>=-1).all():
            return -1, 1
    else:
        return values.min(), values.max()


def evaluate_value_fontsize(shape):
    if shape[1]*shape[0] < 100:
        return 12
    else:
        return 4


def evaluate_figsize(shape):
    if shape[1]*shape[0] < 50: limit = 12
    else: limit = 16

    if shape[1] >  shape[0]:
        ratio = int(shape[1] / shape[0])
        x = limit
        y = int(limit / ratio)
    else:
        ratio = int(shape[0] / shape[1])
        x = int(limit / ratio)
        y = limit

    return x, y

def evaluate_filename(reporter, indice):

    # Check if there are multiple symbols or timeframes
    symbol = indice[0][0]
    timeframe = indice[0][1]

    if len(indice) > 1:
        for ind in indice[1:]:
            if ind[0] != symbol:
                symbol = '<symbol>'
            
            if ind[1] != timeframe:
                timeframe = '<timeframe>'
                
        filename = '{}_{}_{}'.format(reporter,symbol,timeframe)
    else:
        symbol, timeframe, analyzer = indice[0]
        filename = '{}_{}_{}'.format(reporter, symbol, timeframe)

    return filename


def evaluate_target_path(report_folder, filename):
    filename.replace('<', '').replace('>', '')
    target_path = '{}/{}'.format(report_folder, filename.replace('<', '').replace('>', ''))
    return target_path


class ImageWriter():
    def __init__(self, report_folder) -> None:
        super().__init__()
        self.report_folder = report_folder

    def candlestick_plot(self, indice, report_data, **kwargs):
        if type(report_data) == dict:
            df = pd.DataFrame(data=report_data)
        elif type(report_data) == pd.DataFrame:
            df = report_data

        symbol, timeframe = indice[0]
        filename = '{}_{}_{}'.format(kwargs['reporter'],symbol,timeframe)
        target_path = '{}/{}'.format(self.report_folder,filename)

        # Creating Subplots
        mpf.plot(df,
                type="candle", 
                title = filename,  
                style="binance", 
                volume=True, 
                figsize=(16, 10),
                returnfig=False,
                show_nontrading=False,
                datetime_format='%Y-%m-%d',
                tight_layout=True
            )

        # Formatting Date    
        #ax[1].xaxis.set_major_locator(mdates.DayLocator())
        #ax[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d')) # Does not working somehow
        #ax[1].tick_params(labelsize=1)
        #plt.gcf().autofmt_xdate()
    
        plt.savefig(target_path)
        plt.close()
        print(f'File saved: {target_path}')


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
        plt.close()
        print(f'File saved: {target_path}')


    def table_plot(self, indice, report_data, **kwargs):
        if type(report_data) == dict:
            df = pd.DataFrame(data=report_data)
        elif type(report_data) == pd.DataFrame:
            df = report_data
        
        symbol, timeframe, analyzer = indice[0]
        filename = '{}_{}_{}_{}'.format(kwargs['reporter'],timeframe,symbol,analyzer)
        target_path = '{}/{}'.format(self.report_folder,filename)

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
        plt.close()
        print(f'File saved: {target_path}')


    def heatmap_plot(self, indice, report_data, **kwargs):
        filename = evaluate_filename(kwargs['reporter'], indice)
        target_path = evaluate_target_path(self.report_folder,filename)

        if type(report_data) == dict:
            df = pd.DataFrame(data=report_data)
        elif type(report_data) == pd.DataFrame:
            df = report_data

        x_labels, y_labels = df.columns.to_list(), df.index.to_list()
        fig, ax = plt.subplots(figsize=evaluate_figsize(df.shape))

        #title = get_reporter_name(indice)
        #title = kwargs.get('reporter','heatmap_plot')

        fig.suptitle(filename, fontsize=24)

        ax.xaxis.tick_top()
        ax.set_xticks(np.arange(len(x_labels)), x_labels, rotation=90)
        ax.set_yticks(np.arange(len(y_labels)), y_labels)

        vmin, vmax = evaluate_min_max_limits(df)
        im = ax.imshow(df.values, cmap='coolwarm', vmin=vmin, vmax=vmax)
        fig.colorbar(im)

        fontsize = evaluate_value_fontsize(df.shape)

        for i in range(df.values.shape[0]):
            for j in range(df.values.shape[1]):
                #if not math.isnan(matrice[0, 0]):
                text = ax.text(j, i, "%.2f" % df.values[i, j],
                            ha="center", va="center", color="black", fontsize=fontsize)

        #target_path = '{}/{}.png'.format(self.report_folder,title.replace(' ', '_'))

        # shitcode
        footnote = f"""
        Configuration: {kwargs}
        """

        plt.figtext(0, 0, footnote, ha="left", fontsize=8)
        plt.tight_layout()
        plt.savefig(target_path, bbox_inches='tight') # dpi=300
        plt.close()
        print(f'File saved: {target_path}')


    def heatmap_multiplot(self, indice, report_data, **kwargs):
        filename = evaluate_filename(kwargs['reporter'], indice)
        target_path = evaluate_target_path(self.report_folder,filename)

        sub_matrices = []

        if type(report_data) == dict:
            #x_labels = list(report_data.keys())
            #y_labels = [""]
            #sub_matrices = [pd.DataFrame(data=datum).values for datum in report_data.values()]
            pass
        else:
            return

        for key, report_datum in report_data.items():
            tabular_df = pd.DataFrame(data=report_datum)
            sub_matrices.append(tabular_df.values)

        x_labels, y_labels, sub_x_labels, sub_y_labels = [""], list(report_data.keys()), tabular_df.columns.to_list(), tabular_df.index.to_list()

        fig = plt.figure(figsize=evaluate_figsize((len(sub_x_labels)*len(x_labels),len(sub_y_labels)*len(y_labels))))
        fig.suptitle(filename, fontsize=24)

        grid = AxesGrid(fig, 111,
                        nrows_ncols=(len(y_labels), len(x_labels)),
                        axes_pad=0.05,
                        share_all=True,
                        label_mode="L",
                        cbar_location="right",
                        cbar_mode="single",
                        )

        for idx, (matrice, ax) in enumerate(zip(sub_matrices,grid)):
            fontsize = evaluate_value_fontsize(matrice.shape)
            if idx < len(x_labels):
                ax2 = ax.secondary_xaxis('top')
                ax2.tick_params(axis='x')
                ax2.set_xticks(np.arange(len(sub_x_labels)), sub_x_labels, minor=False, fontsize=fontsize)
                ax2.set_xlabel(x_labels[idx], fontsize=fontsize)

            else:
                ax.set_xticks([])

            if True: #idx % len(y_labels) == 0:
                ax.set_ylabel(y_labels[idx], fontsize=fontsize)
                #ax.set(ylabel=y_labels[idx % len(y_labels)])

            vmin, vmax = evaluate_min_max_limits(matrice)
            ax.set_yticks(np.arange(len(sub_y_labels)), sub_y_labels, fontsize=fontsize)
            im = ax.imshow(matrice, cmap='coolwarm' ,vmin=vmin, vmax=vmax)

            for i in range(matrice.shape[0]):
                for j in range(matrice.shape[1]):
                    if not math.isnan(matrice[0, 0]):
                        text = ax.text(j, i, "%.2f" % matrice[i, j],
                                    ha="center", va="center", color="black", fontsize=fontsize)
        grid.cbar_axes[0].colorbar(im)


        # shitcode
        footnote = f"""
        Configuration: {kwargs}
        """

        plt.figtext(0, 0, footnote, ha="left", fontsize=8)
        plt.tight_layout()
        plt.savefig(target_path, bbox_inches='tight')
        plt.close()
        print(f'File saved: {target_path}')

    def double_sided_histogram_plot(self, indice, df, **kwargs):
        symbol, timeframe, analyzer = indice[0]

        filename = '{}_{}_{}'.format(kwargs['reporter'],symbol,timeframe)
        target_path = '{}/{}'.format(self.report_folder,filename)

        fig = plt.figure(figsize=(16,8))
        ax = plt.subplot(111)
        ax.bar(df.index, df.iloc[:,0].values, width=0.05, color='g')
        ax.bar(df.index, df.iloc[:,1].values, width=0.05, color='r')
        #ax.xaxis.set_major_locator(mdates.DayLocator())
        #ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        plt.gcf().autofmt_xdate()

        # Set title
        fig.suptitle(filename, fontsize=24)

        # shitcode
        footnote = f"""
        Configuration: {kwargs}
        """
        y_tick_step = 0.01
        plt.yticks(np.arange(round(df.iloc[:,1].min(), 2)-y_tick_step, df.iloc[:,0].max(), y_tick_step))
        plt.grid(linewidth=1)
        plt.figtext(0.5, 0, footnote, ha="center", fontsize=12)
        #plt.tight_layout()

        plt.savefig(target_path, bbox_inches='tight')
        plt.close()
        print(f'File saved: {target_path}')


    def double_sided_occurence_plot(self, indice, df, **kwargs):

        symbol, timeframe, analyzer = indice[0]
        filename = '{}_{}_{}'.format(kwargs['reporter'],symbol,timeframe)
        target_path = '{}/{}'.format(self.report_folder,filename)

        fig = plt.figure(figsize=(16,8))
        ax = plt.subplot(111)
        
        ax.bar(df.index, df['pos_change'].values, width=0.001, color='g', alpha=0.5)
        ax.bar(df.index, df['neg_change'].values, width=0.001, color='r', alpha=0.5)

        # Set title
        fig.suptitle(filename, fontsize=24)

        # shitcode
        footnote = f"""
        Configuration: {kwargs}
        """
        x_tick_step = 0.01
        plt.xticks(np.arange(round(df.index.min(), 2)-x_tick_step, df.index.max(), x_tick_step), rotation=45)
        plt.grid(linewidth=1)
        plt.figtext(0.5, 0, footnote, ha="center", fontsize=12)
        #plt.tight_layout()

        plt.savefig(target_path)
        plt.close()
        print(f'File saved: {target_path}')


    def line_plot(self, indice, df, **kwargs):

        x_labels, y_labels = df.columns.to_list(), df.index.to_list()
        fig, ax = plt.subplots(figsize=(12,12))

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


    def markdown_table(self, indice, report_data, **kwargs):

        if type(report_data) == dict:
            df = pd.DataFrame(data=report_data)
        elif type(report_data) == pd.DataFrame:
            df = report_data

        symbol, timeframe, analyzer = indice[0]
        title = '{}_{}_{}_{}'.format(kwargs.get('reporter',''),timeframe,symbol,analyzer)

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