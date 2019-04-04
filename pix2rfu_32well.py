import argparse
# from srt_rfu.srt_rfu32 import SrtRfu32


def main(args):
    print(args)
    print('path', args.exp_path)
    print('except col', args.except_col)
    print('except row', args.except_row)
    if args.is_onefile:
        print('is onefile')
    # _rfu = SrtRfu32(args.path)
    # _rfu.get_datasheet()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert image results from SRT to RFU formatted'
        'for DSP analysis')
    parser.add_argument('--version', action='version', version='0.0.1')
    parser.add_argument(
        'exp_path', help='Path of the experiment directory, '
        'which contains main and sub folders for result images. '
        'If there are spaces within the path, add quotation marks.')
    # parser.add_argument('-', '--except_col')
    parser.add_argument('-c', '--except_col')
    parser.add_argument('-r', '--except_row')
    subparsers = parser.add_subparsers(
        title='onefile', dest='is_onefile',
        description='get image processing result from a file')
    parser_onef = subparsers.add_parser('i')
    parser_onef.add_argument('cam', choices=['main', 'sub'])
    parser_onef.add_argument('temp', choices=['low', 'high'])
    parser_onef.add_argument('dye', choices=['f', 'h', 'c', 'q6', 'q7'])
    parser_onef.add_argument('cycle')
    args = parser.parse_args()
    main(args)
