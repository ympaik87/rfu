import argparse
import subprocess
from srt_rfu.srt_rfu32 import SrtRfu32


def main(args):
    print(args)
    print('path', args.exp_path)
    print('except col', args.exempt_col)
    print('except row', args.exempt_row)
    if args.tc:
        print('TC', args.tc)
        tc = int(args.tc)
    else:
        tc = 45
    _rfu = SrtRfu32(args.exp_path)
    if args.is_onefile:
        print('is onefile', args.temp, args.dye, args.cycle, args.well)
        _rfu.get_onef_result(
            args.temp, args.dye, args.cycle, args.well, tc=tc)
    else:
        _rfu.get_datasheet(tc)


if __name__ == '__main__':
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
    parser.add_argument('-c', '--exempt_col')
    parser.add_argument('-r', '--exempt_row')
    parser.add_argument('-t', '--tc', help='add total cycle. default is 45')
    subparsers = parser.add_subparsers(
        title='onefile', dest='is_onefile',
        description='get image processing result from a file')
    parser_onef = subparsers.add_parser('i')
    parser_onef.add_argument('temp', choices=['low', 'high'])
    parser_onef.add_argument('dye', choices=['f', 'h', 'c', 'q6', 'q7'])
    parser_onef.add_argument('cycle')
    well_li = [x+z+str(y+1) for x in list(
        'ABCDabcd') for y in range(8) for z in ['', '0']]
    parser_onef.add_argument('well', choices=well_li)
    args = parser.parse_args()
    main(args)
