import argparse
import sys

from starkware.cairo.lang.compiler.parser import parse_file
from starkware.cairo.lang.version import __version__


def main():
    parser = argparse.ArgumentParser(
        description='A tool to automatically format Cairo code.')
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('files', metavar='file', type=str, nargs='+', help='File names')
    action = parser.add_mutually_exclusive_group(required=False)
    action.add_argument('-i', dest='inplace', action='store_true', help='Edit files inplace.')
    action.add_argument('-c', dest='check', action='store_true', help='Check files\' formats.')

    args = parser.parse_args()
    return_code = 0

    for path in args.files:
        old_content = open(path).read() if path != '-' else sys.stdin.read()
        try:
            new_content = parse_file(
                old_content, filename='<input>' if path == '-' else path).format()
        except Exception as exc:
            print(exc, file=sys.stderr)
            return 2

        if args.inplace:
            assert path != '-', 'Using "-i" together with "-" is not supported.'
            open(path, 'w').write(new_content)
        elif args.check:
            assert path != '-', 'Using "-c" together with "-" is not supported.'
            if old_content != new_content:
                print(f'File "{path}" is incorrectly formatted.', file=sys.stderr)
                return_code = 1
        else:
            print(new_content, end='')

    return return_code


if __name__ == '__main__':
    sys.exit(main())
