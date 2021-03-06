import subprocess
import concurrent.futures
from itertools import product
from tqdm import tqdm
import pathlib
import xlsxwriter
import datetime
import time
from collections import OrderedDict
from skimage.filters import threshold_mean
from skimage.measure import regionprops, label
from skimage.morphology import closing, opening, disk
from skimage.segmentation import clear_border
from skimage.color import label2rgb
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import patches
from srt_rfu.progress_bar import printProgressBar
from srt_rfu.heat_map import heatmap, annotate_heatmap


class SrtRfu16Leg:
    def __init__(self, exp_path, dye_exempt=None):
        self.exp_path = pathlib.Path(exp_path)
        self.temp_li = ['Low Temp', 'High Temp']
        self.y_range = slice(300, 1800)
        self.x_range = slice(500, 2100)
        self.well_area_max = (self.y_range.stop - self.y_range.start) * (
            self.x_range.stop - self.x_range.start) * 0.2
        self.colors_li = [plt.cm.get_cmap('hsv', 30)(i) for i in range(30)]
        self.row_name = list('ABCD')
        self.col_name = range(1, 5)
        self.version = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD']).decode('utf-8').strip()
        self.get_dye_dict(dye_exempt)

    def get_datetime(self):
        return datetime.datetime.now().strftime('-%y%m%d_%H%M%S')

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

    def get_region_li(self, im_labeled, im_gray):
        region_li = []
        for region in regionprops(im_labeled, intensity_image=im_gray):
            region_li.append((region.area, region))
        sorted_region_li = sorted(
            region_li, key=lambda tup: tup[0], reverse=True)
        return [region for area, region in sorted_region_li]

    def get_grid_loc(self, x, y):
        well_location_dict = self.grid
        for well in well_location_dict.keys():
            y_min, x_min, y_max, x_max = well_location_dict[well]
            if y_min < y < y_max and x_min < x < x_max:
                return well
        return None

    def get_well_name(self, x, y, pts_center):
        well_location_dict = self.grid
        for well in well_location_dict.keys():
            y_min, x_min, y_max, x_max = well_location_dict[well]
            if y_min < y < y_max and x_min < x < x_max:
                radius = (x_max-x_min)/2 - 50
                pts_given = np.array([x, y])
                distance = np.linalg.norm(pts_given-pts_center)
                if distance < radius:
                    return well, radius
        return None, None

    def plot_grid(self, ax):
        for pts in self.grid.values():
            ax.scatter(pts[1], pts[0], c='g')
            ax.scatter(pts[3], pts[2], c='g')

    def calculate_rfu(self, region_li, ax=None):
        "calculate RFU by image"
        region_sum_dict = {}
        for key in self.grid.keys():
            region_sum_dict[key] = 0
        center_at_cycle = {}
        circle_li = []
        for region_obj in region_li:
            if region_obj.area > self.well_area_max:
                continue
            y, x = region_obj.centroid
            grid = self.get_grid_loc(x, y)
            if grid is None:
                continue

            if grid not in center_at_cycle.keys():
                center = [x, y]
                center_at_cycle[grid] = center
                if ax:
                    well, rad = self.get_well_name(x, y, center)
                    circle_li.append(patches.Circle(
                        center, radius=rad, color='r', fill=False,
                        linewidth=1))
            else:
                center = center_at_cycle[grid]
            well, rad = self.get_well_name(x, y, center)

            if well is not None:
                region_sum_dict[well] += region_obj.intensity_image.sum()
                if ax:
                    ax.plot(x, y, color='white', marker='*')
                    ax.text(x, y, well, color='gray')
            elif ax:
                ax.plot(x, y, color='b', marker='x')
        if ax:
            self.plot_grid(ax)
            for circle in circle_li:
                ax.add_artist(circle)
        return region_sum_dict

    def open_im(self, im_path):
        "open images. Designed for adding image rotation for 96well"
        im = np.array(Image.open(im_path))
        return im[self.y_range, self.x_range]

    def label_image(self, im_path):
        im_cropped = self.open_im(im_path)

        im_gray = im_cropped.sum(axis=2)
        cleared = clear_border(im_gray)
        thresh = threshold_mean(cleared)
        threshed_im = cleared > thresh

        bw = opening(threshed_im, disk(11))
        bw2 = closing(bw, disk(3))
        return label(bw2), im_gray

    def set_grid(self, tc=45):
        "get grid by camera from the last cycle"
        self.grid = {}
        grid_im_path = self.exp_path/'/{}_0_{}.jpg'.format(
            tc-1, list(self.ch_dict.keys())[0])
        self.grid = self.set_grid_single(grid_im_path)

    def set_grid_single(self, im_path):
        im_labeled, im_gray = self.label_image(im_path)
        region_li = self.get_region_li(im_labeled, im_gray)
        bbox_key_li = ['minr', 'minc', 'maxr', 'maxc']
        bbox_dic = {}
        for key in bbox_key_li:
            bbox_dic[key] = []
        for region in region_li:
            bbox_li = region.bbox
            for i, k in enumerate(bbox_key_li):
                bbox_dic[k] += [bbox_li[i]]
        well_box = []
        for key3 in bbox_key_li[:2]:
            well_box.append(sorted(bbox_dic[key3])[0]-50)
        for key4 in bbox_key_li[2:]:
            well_box.append(sorted(bbox_dic[key4])[-1]+50)
        x_li = np.linspace(well_box[1], well_box[3], 5, endpoint=True)
        y_li = np.linspace(well_box[0], well_box[2], 5, endpoint=True)
        pts_li = [(x, y) for x in x_li for y in y_li]
        grid = {}
        for ind in range(19):
            i, j = divmod(ind, 5)
            if j == 4:
                continue
            top_left_pt = pts_li[ind]
            bottom_right_pt = pts_li[ind+6]
            well = self.get_well_name4grid(i, j)
            grid[well] = [top_left_pt[1], top_left_pt[0],
                          bottom_right_pt[1], bottom_right_pt[0]]
        return grid

    def get_well_name4grid(self, i, j):
        return self.row_name[j] + str(self.col_name[i])

    def make_rfu_table(self, tc=45, progress_txt='RFU table progress'):
        "concatenate rfu by camera, dye, temp, cycle"
        print('Start creating RFU datatable')
        t = time.time()
        total_num = len(self.temp_li)*len(self.ch_dict)*tc
        prog = 1

        paramlist = list(product(range(len(self.temp_li)), self.ch_dict.keys(),
                                 range(tc)))
        with concurrent.futures.ProcessPoolExecutor() as executor:
            res_tup_li = list(
                tqdm(executor.map(self.mp_rfu, paramlist),
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
                    prog += 1
                    printProgressBar(
                        prog, total_num, 'Data processing:', 'Complete')
                self.rfu_dict[temp][dye] = pd.DataFrame(_dic).T
        print('\nFinish creating RFU table in {} sec.'.format(time.time()-t))

    def mp_rfu(self, paramlist):
        im_path = self.exp_path/'{}_{}_{}.jpg'.format(
            paramlist[2], paramlist[0], paramlist[1])
        im_labeled, im_gray = self.label_image(im_path)
        region_li = self.get_region_li(im_labeled, im_gray)
        _rfu = self.calculate_rfu(region_li)
        return str(paramlist), _rfu

    def make_end_point_results(self, path):
        suffix = ' {} -  End Point Results.xlsx'.format(self.version)
        well_li = [
            x+'0'+str(y) for x in self.row_name for y in self.col_name][::-1]
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
        qs_li = ['QuantStep60', 'QuantStep72']
        self.set_grid(tc=tc)
        self.make_rfu_table(tc=tc)
        res_dir = self.exp_path/('DSP_datasheet' + self.get_datetime())
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

    def get_onef_result(self, tmp, dye, cycle, well, tc=45):
        "save image processing result in image file (by cycle)"
        self.set_grid(tc=tc)
        if 'low' in tmp.lower():
            ind = 0
        else:
            ind = 1
        col_li, row_li = self.get_well_loc(well)
        im_path = self.exp_path/'{}_{}_{}.jpg'.format(int(cycle)-1, ind, dye)

        outf_path = self.exp_path/(
            'Result_{}-{}_{}_{}'.format(self.version, int(cycle)-1, ind, dye) +
            self.get_datetime() + '.jpg')
        title = '{} - (Version {})'.format(im_path.name, self.version)

        self.plot_processing_result(im_path, self.col_li, self.row_li,
                                    outf_path, title)

    def get_single_result(self):
        "save image processing result in image file (by cycle)"
        self.grid = self.set_grid_single(self.exp_path)

        outf_path = self.exp_path.parent/(
            'Single_Result_{}-{}'.format(self.version, self.exp_path.stem) +
            self.get_datetime() + '.jpg')

        title = 'Single Picture Result of {} - (Version {})'.format(
            self.exp_path.name, self.version)

        self.plot_processing_result(self.exp_path, self.col_li, self.row_li,
                                    outf_path, title)

    def plot_processing_result(self, im_path, col_li, row_li, outf_path,
                               title):
        im_labeled, im_gray = self.label_image(im_path)
        image_label_overlay = label2rgb(
            im_labeled, bg_label=0, colors=self.colors_li)
        region_li = self.get_region_li(im_labeled, im_gray)

        fig, ax = plt.subplots(2, 3, figsize=(18, 12), constrained_layout=True)
        ax[0, 0].imshow(np.array(Image.open(im_path)))
        rect = patches.Rectangle(
            (self.x_range.start, self.y_range.start),
            self.x_range.stop-self.x_range.start,
            self.y_range.stop-self.y_range.start,
            edgecolor='r', facecolor='none')
        ax[0, 0].add_patch(rect)
        ax[0, 0].set_title('Original')
        ax[0, 1].imshow(im_gray)
        ax[0, 1].set_title('Gray')
        ax[1, 0].imshow(image_label_overlay)
        ax[1, 0].set_title('Labeled')
        ax[1, 1].imshow(image_label_overlay)
        region_sum_dict = self.calculate_rfu(region_li, ax[1, 1])
        ax[1, 1].set_title('Processed Result')

        table_cell = []
        for r in row_li:
            _li = []
            for c in col_li:
                try:
                    _li.append(round(region_sum_dict[r+str(c)], 2))
                except KeyError:
                    _li.append('')
            table_cell.append(_li)
        table = ax[0, 2].table(cellText=table_cell, colLabels=col_li,
                               rowLabels=row_li, loc='center')
        table.auto_set_column_width(list(range(4)))
        ax[0, 2].axis('off')
        ax[0, 2].axis('auto')
        ax[0, 2].set_title(title)

        cell_np = np.array(table_cell)
        data_rt_mean = np.true_divide(cell_np, np.mean(cell_np))
        boundary = [0, 0.5, 0.7, 0.9, 1.1, 1.3, 1.5, 2]
        norm = matplotlib.colors.BoundaryNorm(boundary, 7)
        im, cbar = heatmap(data_rt_mean, row_li, col_li, ax=ax[1, 2],
                           cmap=plt.get_cmap('coolwarm', 7), norm=norm,
                           cbarlabel='RFU divided by mean')
        annotate_heatmap(im, textcolors=['black', 'black'])
        plt.savefig(str(outf_path))
        print(region_sum_dict)
