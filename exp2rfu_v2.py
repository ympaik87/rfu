from exp2rfu import ExpRfu
import concurrent
from tqdm import tqdm
import pandas as pd
from collections import OrderedDict


class ExpRfu2(ExpRfu):
    def __init__(self, exp_path):
        super().__init__(exp_path)

    def run_datasheet_loop(self):
        im_path_li = []
        self.res_dic = OrderedDict()
        self.res_dic[self.exp_path.name] = {}
        for i, folder in enumerate(self.folder_li):
            if folder.name in self.ch_dict.keys():
                ch = self.ch_dict[folder.name]
                for im_f in folder.glob('*.jpg'):
                    im_path_li.append(im_f.relative_to(self.exp_path))
                    self.res_dic[self.exp_path.name][ch] = []

        with concurrent.futures.ProcessPoolExecutor() as executor:
            res_tup_li = list(
                tqdm(executor.map(self.mp_rfu, im_path_li),
                     total=len(im_path_li), desc='RFU table progress'))

        for rel_path, dic in res_tup_li:
            fname = rel_path.stem
            self.res_dic[self.exp_path.name][self.ch_dict[
                rel_path.parent.name]].append(pd.Series(dic, name=fname))


def main(args):
    print(args)
    print('path', args.exp_path)
    _rfu = ExpRfu2(args.exp_path)
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
