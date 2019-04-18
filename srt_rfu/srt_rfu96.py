from srt_rfu.srt_rfu32 import SrtRfu32
from PIL import Image
import numpy as np


class SrtRfu32F(SrtRfu32):
    def __init__(self, exp_path):
        super().__init__(exp_path)
        self.row_name = list('ABCD')
        self.col_name = [range(1, 5), range(5, 9)]
        self.cam_keys = ['front_left', 'front_right']


class SrtRfu32B(SrtRfu32):
    def __init__(self, exp_path):
        super().__init__(exp_path)
        self.row_name = list('EFGH')
        self.col_name = [range(1, 5), range(5, 9)]
        self.cam_keys = ['back_left', 'back_right']

    def open_im(self, im_path):
        return np.array(Image.open(im_path))


class SrtRfu32S(SrtRfu32):
    def __init__(self, exp_path):
        super().__init__(exp_path)
        self.row_name = [list('ABCD'), list('EFGH')]
        self.col_name = range(9, 13)
        self.cam_keys = ['side_front', 'side_back']

    def open_im(self, im_path):
        return np.array(Image.open(im_path))

    def set_grid_single(self, im_path, idx=0):
        im_labeled, im_gray = self.label_image(im_path)
        region_dic = self.get_region_dic(im_labeled, im_gray)
        areas_li = sorted(list(region_dic.keys()), reverse=True)[:16]
        bbox_key_li = ['minr', 'minc', 'maxr', 'maxc']
        bbox_dic = {}
        for key in bbox_key_li:
            bbox_dic[key] = []
        for key2 in areas_li:
            region = region_dic[key2]
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
            well = self.row_name[idx][j] + str(self.col_name[i])
            grid[well] = [top_left_pt[1], top_left_pt[0],
                          bottom_right_pt[1], bottom_right_pt[0]]
        return grid


class SrtRfu96:
    def __init__(self, exp_path):
        self.exp_path = exp_path
        self.rfu_front = SrtRfu32F(self.exp_path)
        self.rfu_back = SrtRfu32B(self.exp_path)
        self.rfu_side = SrtRfu32S(self.exp_path)

    def concat_rfu_table(self):
        front_dic = self.rfu_front.make_rfu_table()
        back_dic = self.rfu_back.make_rfu_table()
        side_dic = self.rfu_side.make_rfu_table()
