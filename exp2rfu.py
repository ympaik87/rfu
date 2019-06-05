from srt_rfu.srt_rfu32 import SrtRfu32
import concurrent
import datetime
from tqdm import tqdm
import xlsxwriter
import pandas as pd
import numpy as np
from collections import OrderedDict
from skimage.filters import threshold_mean
from skimage.morphology import closing, opening, disk, erosion
from skimage.segmentation import clear_border
from skimage.measure import label
from matplotlib import patches


class ExpRfu(SrtRfu32):
    def __init__(self, exp_path):
        super().__init__(exp_path)
        self.x_range = slice(500, 2100)
        self.y_range = slice(500, 2000)
        self.well_area_max = (self.y_range.stop - self.y_range.start) * (
            self.x_range.stop - self.x_range.start) * 0.2

        self.res_dir = self.exp_path/'DSP_datasheet_{}'.format(
            datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
        self.folder_li = [i for i in self.exp_path.glob('*') if i.is_dir()]
        self.cam, self.col_li, self.row_li = self.get_well_loc(is_single=True)

    def run_datasheet_loop(self):
        im_path_li = []
        self.res_dic = OrderedDict()
        for folder in self.folder_li:
            self.res_dic[folder.name] = {}
            for im_f in folder.glob('*.jpg'):
                if im_f.name.split('_')[0].lower() in self.ch_dict.keys():
                    im_path_li.append(im_f.relative_to(self.exp_path))
                for ch in self.ch_dict.values():
                    self.res_dic[folder.name][ch] = []
        with concurrent.futures.ProcessPoolExecutor() as executor:
            res_tup_li = list(
                tqdm(executor.map(self.mp_rfu, im_path_li),
                     total=len(im_path_li), desc='RFU table progress'))

        for rel_path, dic in res_tup_li:
            f_name = rel_path.stem.split('_')
            self.res_dic[rel_path.parent.name][self.ch_dict[
                f_name[0].lower()]].append(pd.Series(dic, name=f_name[1]))

    def mp_rfu(self, im_rel_path):
        im_path = self.exp_path/im_rel_path
        self.grid = {}
        self.grid[self.cam] = self.set_grid_single(im_path)

        im_labeled, im_gray = self.label_image(im_path)
        return im_rel_path, self.calculate_rfu(im_gray, self.cam)

    def make_end_point_results(self, folder_name):
        fname = '{}_{} -  End Point Results.xlsx'.format(
            folder_name, self.version)
        well_li = [
            x+'0'+str(y) for x in self.row_name for y in range(
                self.col_name[0][0], self.col_name[1][-1])][::-1]
        with xlsxwriter.Workbook(str(self.res_dir/fname)) as writer:
            ws = writer.add_worksheet()
            ws.write(0, 1, 'Well')
            ws.write(0, 3, 'Content')
            for i, well in enumerate(well_li):
                ws.write(i+1, 1, well)
                ws.write(i+1, 3, 'Unkn')

    def get_datasheet(self):
        "save rfu table as xlsx for DSP analysis"
        self.run_datasheet_loop()
        self.res_dir.mkdir()
        for folder_name, dic1 in self.res_dic.items():
            self.make_end_point_results(folder_name)
            fname = '{}_{} -  Quantitation Amplification Results.xlsx'.format(
                folder_name, self.version)
            with pd.ExcelWriter(str(self.res_dir/fname)) as writer:
                for dye, region_dic_li in dic1.items():
                    df = pd.concat(region_dic_li, axis=1).T
                    df.to_excel(writer, sheet_name=dye)

    def label_image(self, im_path):
        im_cropped = self.open_im(im_path)

        im_gray = im_cropped.sum(axis=2)
        thresh = 0.1
        threshed_im = im_gray > thresh
        return label(threshed_im), im_gray
    
    def set_grid_single(self, im_path, idx=0):
        well_box = [50, 200, 1300, 1500]
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
            well = self.get_well_name4grid(i, j, idx)
            grid[well] = [top_left_pt[1], top_left_pt[0],
                          bottom_right_pt[1], bottom_right_pt[0]]
        return grid

    def calculate_rfu(self, im_in, cam, ax=None):
        "calculate RFU by image"
        region_sum_dict = {}
        for key, grid_coord in self.grid[cam].items():
            x_range = slice(int(grid_coord[1]), int(grid_coord[3]))
            y_range = slice(int(grid_coord[0]), int(grid_coord[2]))
            region_sum_dict[key] = im_in[y_range, x_range].sum()
        return region_sum_dict
    
    def get_single_result(self):
        "save image processing result in image file (by cycle)"
        cam, col_li, row_li = self.get_well_loc(is_single=True)
        self.grid = {}
        self.grid[cam] = self.set_grid_single(self.exp_path)

        outf_path = self.exp_path.parent.parent/(
            'Single_Result_{}-{}_{}'.format(
                self.version, self.exp_path.parent.name, self.exp_path.stem) +
                datetime.datetime.now().strftime('-%y%m%d_%H%M%S') + '.jpg')

        title = 'Single Picture Result of {} - (Version {})'.format(
            self.exp_path.name, self.version)

        self.plot_processing_result(self.exp_path, cam, col_li, row_li,
                                    outf_path, title)


def main(args):
    print(args)
    print('path', args.exp_path)
    _rfu = ExpRfu(args.exp_path)
    if args.is_onefile == 's':
        print('is single file')
        _rfu.get_single_result()
    else:
        _rfu.get_datasheet()


if __name__ == '__main__':
    import argparse
    import subprocess
    parser = argparse.ArgumentParser(
        description='Convert image results from SRT to RFU formatted'
        'for DSP analysis')
    version = subprocess.check_output(
        ['git', 'rev-parse', '--short', 'HEAD']).decode('utf-8').strip()
    parser.add_argument('-v', '--version', action='version', version=version)
    parser.add_argument(
        'exp_path', help='Path of the experiment directory, '
        'which contains main and sub folders for result images. '
        'If there are spaces within the path, add quotation marks.')
    subparsers = parser.add_subparsers(
        title='onefile', dest='is_onefile',
        description='get image processing result from a file')
    parser_single = subparsers.add_parser('s')
    args = parser.parse_args()
    main(args)
