from srt_rfu.srt_rfu16 import SrtRfu16
from srt_rfu.heat_map import heatmap, annotate_heatmap
import pathlib
import xlsxwriter
import matplotlib.pyplot as plt
from matplotlib import patches, colors
from collections import OrderedDict
import time
import datetime
from itertools import product
import concurrent.futures
from tqdm import tqdm
import pandas as pd
import numpy as np


class SrtRfu16Dev(SrtRfu16):
    def __init__(self, folder_path, dye_exempt=None):
        super().__init__()
        self.cam_path = pathlib.Path(folder_path)
        self.exp_path = self.cam_path.parent
        self.colors_li = [plt.cm.get_cmap('hsv', 30)(i) for i in range(30)]
        self.temp_li = ['Low Temp', 'High Temp']
        self.cam_key = 'main'
        self.datetime = datetime.datetime.now().strftime('-%y%m%d_%H%M%S')
        self.get_dye_dict(dye_exempt)
        
    def get_dye_dict(self, dye_exempt):
        dye_init = OrderedDict([
            ('f', 'FAM'),
            ('h', 'HEX'),
            ('c', 'Cal Red 610'),
            ('q6', 'Quasar 670'),
            ('q7', 'Quasar 705'),
        ])
        if dye_exempt:
            for dye in dye_exempt:
                del dye_init[dye]
            self.ch_dict = dye_init
        else:
            self.ch_dict = dye_init
    
    def make_rfu_table(self, tc=45, progress_txt='RFU table progress'):
        "concatenate rfu by camera, dye, temp, cycle"
        print('Start creating RFU datatable')
        t = time.time()
        total_num = len(self.temp_li)*len(self.ch_dict)*tc

        paramlist = list(product(range(len(self.temp_li)), self.ch_dict.keys(),
                                 range(tc)))
        with concurrent.futures.ProcessPoolExecutor() as executor:
            res_tup_li = list(
                tqdm(executor.map(self.to_mp_rfu, paramlist),
                     total=len(paramlist), desc=progress_txt))
        res_dic = dict(res_tup_li)

        self.rfu_dict = {}
        for ind, temp in enumerate(self.temp_li):
            self.rfu_dict[temp] = {}
            for dye_abb, dye in self.ch_dict.items():
                _dic = OrderedDict()
                for cycle in range(tc):
                    key = str((ind, dye_abb, cycle))
                    _dic[cycle+1] = res_dic[key]
                self.rfu_dict[temp][dye] = pd.DataFrame(_dic).T
        print('\nFinish creating RFU table in {} sec.'.format(time.time()-t))
    
    def to_mp_rfu(self, paramlist):
        im_path = str(self.cam_path/'{}_{}_{}.jpg'.format(
            paramlist[2], paramlist[0], paramlist[1]))
        _rfu = self.mp_rfu(im_path, is_outf=False)
        return str(paramlist), _rfu
        
    def make_end_point_results(self, path):
        suffix = ' {} -  End Point Results.xlsx'.format(self.version)
        well_li = [
            x+'0'+str(y) for x in self.row_name for y in range(
                self.col_name[0], self.col_name[-1])][::-1]
        with xlsxwriter.Workbook(
                str(path/(self.exp_path.name+suffix))) as writer:
            ws = writer.add_worksheet()
            ws.write(0, 1, 'Well')
            ws.write(0, 3, 'Content')
            for i, well in enumerate(well_li):
                ws.write(i+1, 1, well)
                ws.write(i+1, 3, 'Unkn')

    def get_datasheet(self, tc=45):
        "save rfu table as xlsx for DSP analysis"
        suffix = ' {} -  Quantitation Amplification Results.xlsx'.format(
            self.version)
        qs_li = ['QuantStep1', 'QuantStep2']
        self.make_rfu_table(tc=tc)
        res_dir = self.exp_path/('DSP_datasheet' + self.datetime)
        res_dir.mkdir()
        for ind, temp in enumerate(self.temp_li):
            qs_path = res_dir/qs_li[ind]
            qs_path.mkdir()
            with pd.ExcelWriter(
                    str(qs_path/(self.exp_path.name+suffix))) as writer:
                for dye in self.ch_dict.values():
                    df = self.rfu_dict[temp][dye]
                    df = df.reset_index().rename(columns={'index': 'Cycle'})
                    df.to_excel(writer, sheet_name=dye)
            self.make_end_point_results(qs_path)
        
    def get_ref_im(self, im_path):
        ref_path = im_path.parent/'ref.jpg'
        return self.open_im(ref_path)
        
    def plot_grid(self, ax):
        for pts in self.grid.values():
            ax.scatter(pts[1], pts[0], c='g')
            ax.scatter(pts[3], pts[2], c='g')
            cent_y = int((pts[3] + pts[1])/2)
            cent_x = int((pts[2] + pts[0])/2)
            ax.scatter(cent_y, cent_x, c='r')
            circ = patches.Circle((cent_y, cent_x), radius=100, color='r',
                                  fill=False, linewidth=1)
            ax.add_patch(circ)
            
    def plot_rfu_table(self, rfu_dic, ax):
        table_cell = []
        for r in self.row_name:
            _li = []
            for c in self.col_name:
                try:
                    _li.append(round(rfu_dic[r+str(c)], 2))
                except KeyError:
                    _li.append('')
            table_cell.append(_li)
        table = ax.table(cellText=table_cell, colLabels=self.col_name,
                         rowLabels=self.row_name, loc='center')
        table.auto_set_column_width(list(range(4)))
        ax.axis('off')
        ax.axis('auto')
        return table_cell
        
    def plot_rfu_heatmap(self, table_cell, ax):
        cell_np = np.array(table_cell)
        data_rt_mean = np.true_divide(cell_np, np.mean(cell_np))
        boundary = [0, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 2]
        norm = colors.BoundaryNorm(boundary, 7)
        im, cbar = heatmap(data_rt_mean, self.row_name, self.col_name, ax=ax,
                           cmap=plt.get_cmap('coolwarm', 7), norm=norm,
                           cbarlabel='RFU divided by mean')
        annotate_heatmap(im, textcolors=['black', 'black'])
        
    def get_single_result(self, im_path_in):
        im_path = pathlib.Path(im_path_in)
        title = 'Single Picture Result of {} - (Version {})'.format(
            im_path.name, self.version)
        outf_path = im_path.parents[1]/(
            'Single_Result_{}-{}'.format(self.version, im_path.stem) +
            self.datetime + '.jpg')

        rfu_dict = self.mp_rfu(im_path_in, is_outf=False)
        fig, ax = plt.subplots(2, 3, figsize=(18, 12), constrained_layout=True)
        ax[0, 0].imshow(self.open_im(im_path))
        ax[0, 0].set_title('Original')

        _, im_gray = self.label_image(im_path)
        ax[0, 1].imshow(im_gray)
        ax[0, 1].set_title('Gray')
        
        ref_im = self.get_ref_im(im_path)
        ax[1, 0].imshow(ref_im)
        self.plot_grid(ax[1, 0])
        ax[1, 0].set_title('Reference')
        
        ax[1, 1].imshow(im_gray)
        self.plot_grid(ax[1, 1])
        ax[1, 1].set_title('Processed Result')
        
        table_cell = self.plot_rfu_table(rfu_dict, ax[0, 2])
        ax[0, 2].set_title(title)
        
        self.plot_rfu_heatmap(table_cell, ax[1, 2])
        plt.savefig(str(outf_path))
        print(rfu_dict)
