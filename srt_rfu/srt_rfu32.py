import pathlib
import xlsxwriter
import datetime
from skimage.filters import threshold_otsu
from skimage.measure import regionprops, label
from skimage.morphology import closing, opening, disk
from skimage.segmentation import clear_border
from skimage.color import label2rgb
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib.pyplot as plt
from matplotlib import patches


class SrtRfu32:
    def __init__(self, exp_path):
        self.exp_path = pathlib.Path(exp_path)
        self.temp_li = ['Low Temp', 'High Temp']
        self.x_range = slice(500, 1800)
        self.y_range = slice(500, 1800)
        self.colors_li = [plt.cm.get_cmap('hsv', 30)(i) for i in range(30)]
        self.ch_dict = {
            'c': 'Cal Red 610',
            'f': 'FAM',
            'q6': 'Quasar 670',
            'q7': 'Quasar 705',
            'h': 'HEX'
        }
        self.row_name = list('ABCD')
        self.cam_keys = ['main', 'sub']

    def get_region_dic(self, im_labeled, im_gray):
        region_dic = {}
        for region in regionprops(im_labeled, intensity_image=im_gray):
            region_dic[region.area] = region
        return region_dic

    def get_grid_loc(self, x, y, cam):
        well_location_dict = self.grid[cam]
        for well in well_location_dict.keys():
            y_min, x_min, y_max, x_max = well_location_dict[well]
            if y_min < y < y_max and x_min < x < x_max:
                return well
        return None

    def get_well_name(self, x, y, pts_center, cam):
        well_location_dict = self.grid[cam]
        for well in well_location_dict.keys():
            y_min, x_min, y_max, x_max = well_location_dict[well]
            if y_min < y < y_max and x_min < x < x_max:
                radius = (x_max-x_min)/2 - 50
                pts_given = np.array([x, y])
                distance = np.linalg.norm(pts_given-pts_center)
                if distance < radius:
                    return well, radius
        return None

    def calculate_rfu(self, region_dic, cam, ax=None):
        "calculate RFU by image"
        region_sum_dict = {}
        for key in self.grid[cam].keys():
            region_sum_dict[key] = 0
        areas_li = list(region_dic.keys()).sort(reverse=True)
        center_at_cycle = {}
        circle_li = []
        for area in areas_li:
            region_obj = region_dic[area]
            y, x = region_obj.centroid
            grid = self.get_grid_loc(x, y, cam)
            if grid is None:
                continue

            if grid not in center_at_cycle.keys():
                center = [x, y]
                center_at_cycle[grid] = center
                if ax:
                    well, rad = self.get_well_name(x, y, center, cam)
                    circle_li.append(patches.Circle(
                        center, radius=rad, color='r', fill=False,
                        linewidth=1))
            else:
                center = center_at_cycle[grid]
            well, rad = self.get_well_name(x, y, center, cam)

            if well is not None:
                region_sum_dict[well] += region_obj.intensity_image.sum()
                if ax:
                    ax.plot(x, y, color='white', marker='*')
                    ax.text(x, y, well, color='gray')
            elif ax:
                ax.plot(x, y, color='b', marker='x')
        if ax:
            for circle in circle_li:
                ax.add_artist(circle)
        return region_sum_dict

    def label_image(self, im_path):
        im = np.array(Image.open(im_path))
        im_cropped = im[self.x_range, self.y_range]

        im_gray = im_cropped.sum(axis=2)
        thresh = threshold_otsu(im_gray)
        threshed_im = im_gray > thresh

        bw = closing(threshed_im, disk(3))
        bw2 = opening(bw, disk(3))
        cleared = clear_border(bw2)
        return label(cleared), im_gray

    def set_grid(self, tc=44):
        "get grid by camera from the last cycle"
        self.grid = {'main': {}, 'sub': {}}
        main_grid_im_path = self.exp_path/'{}/{}_0_f.jpg'.format(
            self.cam_keys[0], tc)
        sub_grid_im_path = self.exp_path/'{}/{}_0_f.jpg'.format(
            self.cam_keys[1], tc)
        for idx, im_path in enumerate([main_grid_im_path, sub_grid_im_path]):
            self.set_grid_single(im_path, idx)

    def set_grid_single(self, im_path, idx):
        im_labeled, im_gray = self.label_image(im_path)
        region_dic = self.get_region_dic(im_labeled, im_gray)
        areas_li = list(region_dic.keys()).sort(reverse=True)
        bbox_key_li = ['minr', 'minc', 'maxr', 'maxc']
        bbox_dic = {}
        for key in bbox_key_li:
            bbox_dic[key] = []
        for key2 in areas_li[:16]:
            region = region_dic[key2]
            bbox_li = region.bbox
            for i, k in enumerate(bbox_key_li):
                bbox_dic[k] = bbox_li[i]
        well_box = []
        for key3 in bbox_key_li[:2]:
            well_box.append(bbox_dic[key3].sort()[0]-50)
        for key4 in bbox_key_li[2:]:
            well_box.append(bbox_dic[key4].sort()[-1]+50)
        x_li = np.linspace(well_box[1], well_box[3], 5, endpoint=True)
        y_li = np.linspace(well_box[0], well_box[2], 5, endpoint=True)
        pts_li = [(x, y) for x in x_li for y in y_li]
        for ind in range(16):
            top_left_pt = pts_li[ind]
            bottom_right_pt = pts_li[ind+6]
            i, j = divmod(ind, 4)
            key5 = self.row_name[i] + str(j+1+idx*4)
            self.grid[self.cam_keys[idx]][key5] = [
                top_left_pt[1], top_left_pt[0],
                bottom_right_pt[1], bottom_right_pt[0]]

    def make_rfu_table(self, tc=44):
        "concatenate rfu by camera, dye, temp, cycle"
        self.rfu_dict = {}
        for ind, temp in enumerate(self.temp_li):
            self.rfu_dict[temp] = {}
            for dye_abb, dye in self.ch_dict.items():
                _dic2 = {}
                for cycle in range(tc):
                    _dic = {}
                    for cam in self.cam_keys:
                        im_path = self.exp_path/'{}/{}_{}_{}.jpg'.format(
                            cam, cycle, ind, dye_abb)
                        im_labeled, im_gray = self.label_image(im_path)
                        region_dic = self.get_region_dic(im_labeled, im_gray)
                        _rfu = self.calculate_rfu(region_dic, cam)
                        _dic.update(_rfu)
                    _dic2[cycle+1] = _dic
                self.rfu_dict[temp][dye] = pd.DataFrame(_dic2).T

    def make_end_point_results(self, path):
        suffix = ' -  End Point Results.xlsx'
        well_li = [
            x+'0'+str(y+1) for x in list('ABCD') for y in range(8)][::-1]
        with xlsxwriter.Workbook(path/(self.exp_path.name+suffix)) as writer:
            ws = writer.add_worksheet()
            ws.write(0, 1, 'Well')
            for i, well in enumerate(well_li):
                ws.write(i+1, 1, well)

    def get_datasheet(self, tc=44):
        "save rfu table as xlsx for DSP analysis"
        suffix = ' -  Quantitation Amplification Results.xlsx'
        qs_li = ['QuantStep60', 'QuantStep72']
        self.set_grid(tc=tc)
        self.make_rfu_table(tc=tc)
        res_dir = self.exp_path/'DSP_datasheet'
        if res_dir.exists():
            res_dir = self.exp_path/(
                'DSP_datasheet' + datetime.datetime.now().strftime(
                    '_%Y%m%d_%H%M%S'))
        res_dir.mkdir()
        for ind, temp in enumerate(self.temp_li):
            qs_path = res_dir/qs_li[ind]
            with pd.ExcelWriter(qs_path/(self.exp_path.name+suffix)) as writer:
                for dye, df in self.rfu_dict[temp].items():
                    df.to_excel(writer, sheet_name=dye)
            self.make_end_point_results(qs_path)

    def get_onef_result(self, tmp, dye, cycle, well, tc=44):
        "save image processing result in image file (by cycle)"
        self.set_grid(tc=tc)
        if 'low' in tmp.lower():
            ind = 0
        else:
            ind = 1
        ind = self.temp_li.index(tmp)
        col = int(well[-1])
        if 0 <= col < 5:
            cam = self.cam_keys[0]
        else:
            cam = self.cam_keys[1]
        im_path = self.exp_path/'{}/{}_{}_{}.jpg'.format(
            cam, cycle, ind, dye)
        im_labeled, im_gray = self.label_image(im_path)
        image_label_overlay = label2rgb(
            im_labeled, bg_label=0, colors=self.colors_li)
        region_dic = self.get_region_dic(im_labeled, im_gray)

        fig, ax = plt.subplots(1, 3, figsize=(24, 12))
        ax[0, 0].imshow(im_gray)
        ax[0, 1].imshow(im_labeled)
        ax[0, 2].imshow(image_label_overlay)
        self.calculate_rfu(region_dic, cam, ax[0, 2])
        plt.tight_layout()
        plt.savefig(self.exp_path/'Processed_result_{}_{}_{}_{}.jpg'.format(
            cam, cycle, ind, dye))
