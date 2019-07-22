from srt_rfu.srt_rfu16 import SrtRfu16
import pathlib
import matplotlib.pyplot as plt
from collections import OrderedDict
import time
from itertools import product
import concurrent.futures
from tqdm import tqdm
import pandas as pd


class SrtRfu16Dev(SrtRfu16):
    def __init__(self, exp_path, dye_exempt=None):
        super().__init__()
        self.exp_path = pathlib.Path(exp_path)
        self.colors_li = [plt.cm.get_cmap('hsv', 30)(i) for i in range(30)]
        self.temp_li = ['Low Temp', 'High Temp']
        self.cam_key = 'main'
        
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
                tqdm(executor.map(self.to_mp_rfu, paramlist),
                     total=len(paramlist), desc=progress_txt))
        res_dic = dict(res_tup_li)

        self.rfu_dict = {}
        for ind, temp in enumerate(self.temp_li):
            self.rfu_dict[temp] = {}
            for dye_abb, dye in self.ch_dict.items():
                _dic2 = OrderedDict()
                for cycle in range(tc):
                    _dic = OrderedDict()
                    for cam in self.cam_keys:
                        key = str((ind, dye_abb, cycle, cam))
                        _dic.update(res_dic[key])
                        prog += 1
                    _dic2[cycle+1] = _dic
                self.rfu_dict[temp][dye] = pd.DataFrame(_dic2).T
        print('\nFinish creating RFU table in {} sec.'.format(time.time()-t))
    
    def to_mp_rfu(self, paramlist):
        im_path = str(self.exp_path/'{}/{}_{}_{}.jpg'.format(
            self.cam_key, paramlist[2], paramlist[0], paramlist[1]))
        self.mp_rfu(im_path, is_outf=False)
