from srt_rfu.srt_rfu32 import SrtRfu32
import concurrent
import datetime
from tqdm import tqdm
import xlsxwriter
import pandas as pd
from collections import OrderedDict


class ExpRfu(SrtRfu32):
    def __init__(self, exp_path):
        super().__init__(exp_path)
        self.res_dir = self.exp_path/'DSP_datasheet_{}'.format(
            datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
        self.folder_li = [i for i in self.exp_path.glob('*') if i.is_dir()]
        self.cam, self.col_li, self.row_li = self.get_well_loc(is_single=True)

    def run_datasheet_loop(self):
        im_path_li = []
        self.res_dic = OrderedDict()
        for i, folder in enumerate(self.folder_li):
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
        region_dic = self.get_region_dic(im_labeled, im_gray)
        return im_rel_path, self.calculate_rfu(region_dic, self.cam)

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


def main(args):
    print(args)
    print('path', args.exp_path)
    _rfu = ExpRfu(args.exp_path)
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
    args = parser.parse_args()
    main(args)
