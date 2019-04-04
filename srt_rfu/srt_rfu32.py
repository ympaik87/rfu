import pathlib
import skimage
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib.pyplot as plt


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
        self.row_name = {'main': list('ABCD'), 'sub': list('EFGH')}

    def calculate_rfu(self, im_labeled, im_gray):
        "calculate RFU by image"
        pass

    def get_region_dic(self, im_labeled, im_gray):
        region_dic = {}
        for region in skimage.measure.regionprops(
                im_labeled, intensity_image=im_gray):
            region_dic[region.area] = region
        return region_dic

    def label_image(self, im_path):
        im = np.array(Image.open(im_path))
        im_cropped = im[self.x_range, self.y_range]

        im_gray = im_cropped.sum(axis=2)
        thresh = skimage.filters.threshold_otsu(im_gray)
        threshed_im = im_gray > thresh

        bw = skimage.morphology.closing(
            threshed_im, skimage.morphology.disk(3))
        bw2 = skimage.morphology.opening(bw, skimage.morphology.disk(3))
        cleared = skimage.segmentation.clear_border(bw2)
        return skimage.measure.label(cleared), im_gray

    def set_grid(self, cycle_last=44):
        "get grid by camera from the last cycle"
        self.grid = {'main': {}, 'sub': {}}
        grid_keys = ['main', 'sub']
        main_grid_im_path = self.exp_path/'main/{}_0_f.jpg'.format(cycle_last)
        sub_grid_im_path = self.exp_path/'sub/{}_0_f.jpg'.format(cycle_last)
        for idx, im_path in enumerate([main_grid_im_path, sub_grid_im_path]):
            im_labeled, im_gray = self.label_image(im_path)
            region_dic = self.get_region_dic(im_labeled, im_gray)
            areas_li = list(region_dic.keys()).sort(reverse=True)
            bbox_key_li = ['minr', 'minc', 'maxr', 'maxc']
            bbox_dic = {}
            for key in bbox_key_li:
                bbox_dic[key] = []
            for key in areas_li[:16]:
                region = region_dic[key]
                bbox_li = region.bbox
                for i, k in enumerate(bbox_key_li):
                    bbox_dic[k] = bbox_li[i]
            well_box = []
            for key in bbox_key_li[:2]:
                well_box.append(bbox_dic[key].sort()[0]-50)
            for key in bbox_key_li[2:]:
                well_box.append(bbox_dic[key].sort()[-1]+50)
            x_li = np.linspace(well_box[1], well_box[3], 5, endpoint=True)
            y_li = np.linspace(well_box[0], well_box[2], 5, endpoint=True)
            pts_x = []
            pts_y = []
            for x in x_li:
                for y in y_li:
                    pts_x.append(x)
                    pts_y.append(y)
            pts_li = list(zip(pts_x, pts_y))
            for ind in range(16):
                top_left_pt = pts_li[ind]
                bottom_right_pt = pts_li[ind+6]
                i, j = divmod(ind, 4)
                key = self.row_name[grid_keys[idx]][i] + str(j+1)
                self.grid[grid_keys[idx]][key] = [
                    top_left_pt[1], top_left_pt[0],
                    bottom_right_pt[1], bottom_right_pt[0]]

    def make_rfu_table(self):
        "concatenate rfu by camera, dye, temp, cycle"
        pass

    def get_datasheet(self):
        "save rfu table as xlsx for for DSP analysis"
        pass

    def get_onef_result(self, cam, tmp, dye, cycle):
        "save image processing result in image file (by cycle)"
        im_labeled, im_gray = self.process_image(im_path)
        image_label_overlay = skimage.color.label2rgb(
            im_labeled, bg_label=0, colors=self.colors_li)
