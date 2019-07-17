import subprocess
import pathlib
from collections import OrderedDict
from skimage.filters import threshold_mean
from skimage.measure import regionprops, label
from skimage.segmentation import clear_border
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
import json
import time


class SrtRfu16:
    def __init__(self):
        self.temp_li = ['Low Temp', 'High Temp']
        self.grid_cent = None
        self.row_name = list('ABCD')
        self.col_name = range(1, 5)
        self.version = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD']).decode('utf-8').strip()

    def get_region_li(self, im_labeled, im_gray):
        region_li = []
        for region in regionprops(im_labeled, intensity_image=im_gray):
            region_li.append((region.area, region))
        sorted_region_li = sorted(
            region_li, key=lambda tup: tup[0], reverse=True)
        return [region for area, region in sorted_region_li]

    def get_grid_center(self):
        self.grid_cent = {}
        for well, pts in self.grid.items():
            cent_y = int((pts[3] + pts[1])/2)
            cent_x = int((pts[2] + pts[0])/2)
            self.grid_cent[well] = (cent_y, cent_x)

    def create_circular_mask(self, h, w, center, radius):
        Y, X = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((X - center[0])**2 + (Y - center[1])**2)

        mask = dist_from_center <= radius
        return mask

    def calculate_rfu(self, im):
        "calculate RFU by image"
        im_sum = im.sum(axis=2)
        h, w, _ = im.shape

        region_sum_dict = {}
        for well, cent in self.grid_cent.items():
            tt = time.process_time()
            mask = self.create_circular_mask(h, w, cent, 100)
            print('create_circular_mask time: ', time.process_time()-tt)
            tt = time.process_time()
            masked_img = im_sum.copy()
            masked_img[~mask] = 0
            region_sum_dict[well] = masked_img.sum()
            print('after create_circular_mask time: ', time.process_time()-tt)

        return region_sum_dict

    def open_im(self, im_path):
        "open images. Designed for adding image rotation for 96well"
        im = np.array(Image.open(im_path))
        return im

    def label_image(self, im_path):
        im_cropped = self.open_im(im_path)

        im_gray = im_cropped.sum(axis=2)
        cleared = clear_border(im_gray)
        thresh = threshold_mean(cleared)
        threshed_im = cleared > thresh
        return label(threshed_im), im_gray

    def set_grid(self, ref_path, is_outf=False):
        "get grid by camera from the last cycle"
        im_path = pathlib.Path(ref_path)
        self.grid = self.set_grid_single(im_path)
        self.get_grid_center()
        if is_outf:
            grid_json = json.dumps(self.grid_cent)
            with open("{}/grid.json".format(im_path.parent), "w") as f:
                json.dump(grid_json, f)

    def set_grid_single(self, im_f):
        im_labeled, im_gray = self.label_image(im_f)
        region_li = self.get_region_li(im_labeled, im_gray)
        well_box = region_li[0].bbox
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

    def mp_rfu(self, im_path):
        _path = pathlib.Path(im_path)
        tt = time.process_time()
        self.set_grid_json(_path)
        print('set_grid_json time: ', time.process_time()-tt)
        tt = time.process_time()
        im = self.open_im(_path)
        print('open_im time: ', time.process_time()-tt)
        tt = time.process_time()
        _rfu = self.calculate_rfu(im)
        print('calculate_rfu time: ', time.process_time()-tt)
        return _rfu

    def set_grid_json(self, im_path):
        if not isinstance(self.grid_cent, dict):
            try:
                with open('{}/grid.json'.format(im_path.parent), 'r') as f:
                    self.grid_cent = json.load(f)
            except FileNotFoundError:
                print('grid json is not found')
                raise
