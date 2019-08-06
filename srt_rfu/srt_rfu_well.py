from collections import OrderedDict
import pathlib
import json
from .srt_rfu16 import SrtRfu16


class SrtRfuWell(SrtRfu16):
    def __init__(self):
        super().__init__()
        self.well_name = [
            [x+str(y) for y in range(1, 5) for x in list('ABCD')],
            [x+str(y) for y in range(1, 5) for x in list('EFGH')],
            [x+str(y) for y in range(5, 9) for x in list('ABCD')],
            [x+str(y) for y in range(5, 9) for x in list('EFGH')],
            [x+str(y) for y in range(9, 13) for x in list('ABCD')],
            [x+str(y) for y in range(9, 13) for x in list('EFGH')],
        ]

    def mp_rfu(self, im_path, is_outf=True):
        _rfu = super().mp_rfu(im_path, is_outf=is_outf)
        _path = pathlib.Path(im_path)
        im_name = _path.stem
        _, step, cycle, cam_ind, ch = im_name.split('_')
        if cam_ind != '0':
            rfu_adj = {}
            for well, val in _rfu.items():
                well_ind = self.well_name[0].index(well)
                rfu_adj[self.well_name[int(cam_ind)][well_ind]] = val
            if is_outf:
                self.export_json(_path, rfu_adj)
            return rfu_adj
        else:
            if is_outf:
                self.export_json(_path, _rfu)
            return _rfu

    def export_json(self, _path, rfu_dic):
        with open("{}/{}.json".format(_path.parent, _path.stem), "w") as f:
                json.dump(rfu_dic, f)
