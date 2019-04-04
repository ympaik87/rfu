import argparse
import pathlib
import skimage
import numpy as np
import pandas as pd
from PIL import Image
import matplotlib.pyplot as plt


class SrtRfu:
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

    def calculate_rfu(self, im_labeled, im_gray):
        "calculate RFU by image"
        region_dic = {}
        for region in skimage.measure.regionprops(
                im_labeled, intensity_image=im_gray):
            region_dic[region.area] = region

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

    def set_grid(self):
        "get grid by camera from the last cycle"
        self.grid = {'main': {}, 'sub': {}}

    def make_rfu_table(self):
        "concatenate rfu by camera, dye, temp, cycle"
        pass

    def get_datasheet(self):
        "save rfu table as xlsx for for DSP analysis"
        pass

    def get_detection_result(self, cam, tmp, dye, cycle):
        "save image processing result in image file (by cycle)"
        im_labeled, im_gray = self.process_image(im_path)
        image_label_overlay = skimage.color.label2rgb(
            im_labeled, bg_label=0, colors=self.colors_li)


def main(args):
    print(args)
    print('path', args.path)
    print('except col', args.except_col)
    print('except row', args.except_row)
    # _rfu = SrtRfu(args.path)
    # _rfu.get_datasheet()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert image results from SRT to RFU formatted'
        'for DSP analysis')
    parser.add_argument('--version', action='version', version='0.0.1')
    parser.add_argument(
        'path', help='Path of the experiment directory, which contains result'
        'images. If there are spaces within the path, add quotation marks.')
    # parser.add_argument('-', '--except_col')
    parser.add_argument('-c', '--except_col')
    parser.add_argument('-r', '--except_row')
    args = parser.parse_args()
    main(args)
