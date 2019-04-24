from srt_rfu.srt_rfu32 import SrtRfu32
from PIL import Image
import numpy as np
import pandas as pd
import xlsxwriter
import datetime
import pathlib
from skimage.transform import rotate


class SrtRfu32F(SrtRfu32):
    def __init__(self, exp_path):
        super().__init__(exp_path)
        self.row_name = list('EFGH')
        self.col_name = [range(1, 5), range(5, 9)]
        self.cam_keys = ['front_left', 'front_right']

    def open_im(self, im_path):
        im = np.array(Image.open(im_path))
        return rotate(im[self.y_range, self.x_range], 180)


class SrtRfu32B(SrtRfu32):
    def __init__(self, exp_path):
        super().__init__(exp_path)
        self.row_name = list('ABCD')
        self.col_name = [range(1, 5), range(5, 9)]
        self.cam_keys = ['back_left', 'back_right']


class SrtRfu32S(SrtRfu32):
    def __init__(self, exp_path):
        super().__init__(exp_path)
        self.row_name = [list('ABCD'), list('EFGH')]
        self.col_name = range(9, 13)
        self.cam_keys = ['side_front', 'side_back']

    def open_im(self, im_path):
        im = np.array(Image.open(im_path))
        return rotate(im[self.y_range, self.x_range], 90)

    def get_well_name4grid(self, i, j, idx):
        return self.row_name[idx][j] + str(self.col_name[i])


class SrtRfu96:
    def __init__(self, exp_path, dye_exempt=None):
        self.exp_path = pathlib.Path(exp_path)
        self.rfu_front = SrtRfu32F(self.exp_path, dye_exempt)
        self.rfu_back = SrtRfu32B(self.exp_path, dye_exempt)
        self.rfu_side = SrtRfu32S(self.exp_path, dye_exempt)
        self.row_name = self.rfu_back.row_name + self.rfu_front.row_name
        self.col_name = [*self.rfu_back.col_name[0],
                         *self.rfu_back.col_name[1],
                         *self.rfu_side.col_name]

    def concat_rfu_table(self, tc=45):
        front_dic = self.rfu_front.make_rfu_table(
            tc=tc, progress_txt='front progress')
        back_dic = self.rfu_back.make_rfu_table(
            tc=tc, progress_txt='back progress')
        side_dic = self.rfu_side.make_rfu_table(
            tc=tc, progress_txt='side progress')

        self.rfu_dict = {}
        for temp in self.rfu_back.temp_li:
            self.rfu_dict[temp] = {}
            for dye in self.rfu_back.ch_dict.values():
                df_f = front_dic[temp][dye]
                df_b = back_dic[temp][dye]
                df_s = side_dic[temp][dye]
                self.rfu_dict[temp][dye] = df_f.append(df_b).join(df_s)

    def make_end_point_results(self, path):
        suffix = ' {} -  End Point Results.xlsx'.format(self.rfu_back.version)
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
            self.rfu_back.version)
        qs_li = ['QuantStep60', 'QuantStep72']
        self.concat_rfu_table(tc=tc)
        res_dir = self.exp_path/'DSP_datasheet'
        if res_dir.exists():
            res_dir = self.exp_path/(
                'DSP_datasheet' + datetime.datetime.now().strftime(
                    '_%y%m%d_%H%M%S'))
        res_dir.mkdir()
        for ind, temp in enumerate(self.rfu_back.temp_li):
            qs_path = res_dir/qs_li[ind]
            qs_path.mkdir()
            with pd.ExcelWriter(
                    str(qs_path/(self.exp_path.name+suffix))) as writer:
                for dye in self.rfu_back.ch_dict.values():
                    df = self.rfu_dict[temp][dye]
                    df = df.reset_index().rename(columns={'index': 'Cycle'})
                    df.to_excel(writer, sheet_name=dye)
            self.make_end_point_results(qs_path)

    def get_onef_result(self, tmp, dye, cycle, well, tc=45):
        col = int(well[-1])
        row = well[0]
        if col in [*self.rfu_back.col_name[0], *self.rfu_back.col_name[1]]:
            if row in self.rfu_back.row_name:
                self.rfu_back.get_onef_result(tmp, dye, cycle, well, tc)
            else:
                self.rfu_front.get_onef_result(tmp, dye, cycle, well, tc)
        else:
            self.rfu_side.get_onef_result(tmp, dye, cycle, well, tc)

    def get_single_result(self):
        self.rfu_back.get_single_result()
