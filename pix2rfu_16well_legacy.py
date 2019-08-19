import argparse
import subprocess
from srt_rfu.srt_rfu16_legacy import SrtRfu16Leg


def main(args):
    print(args)
    print('path', args.exp_path)
    if args.tc:
        print('TC', args.tc)
        tc = int(args.tc)
    else:
        tc = 45
    _rfu = SrtRfu16Leg(args.exp_path, args.dye_exempt)
    if args.is_onefile == 's':
        print('is single file')
        _rfu.get_single_result(args.exp_path)
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
    parser.add_argument('-d', '--dye_exempt', nargs='+',
                        choices=['f', 'h', 'c', 'q6', 'q7'],
                        help='notify missing dye')
    parser.add_argument('-t', '--tc', help='add total cycle. default is 45')
    subparsers = parser.add_subparsers(
        title='onefile', dest='is_onefile',
        description='get image processing result from a file')
    parser_single = subparsers.add_parser('s')
    args = parser.parse_args()
    main(args)
