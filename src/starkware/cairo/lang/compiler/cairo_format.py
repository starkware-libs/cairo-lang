import argparse
import sys
from typing import Callable

from starkware.cairo.lang.compiler.ast.formatting_utils import set_one_item_per_line
from starkware.cairo.lang.compiler.ast.module import CairoFile
from starkware.cairo.lang.compiler.parser import parse_file
from starkware.cairo.lang.version import __version__


def cairo_format_common(cairo_parser: Callable[[str, str], CairoFile], description: str):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("files", metavar="file", type=str, nargs="+", help="File names")
    parser.add_argument(
        "--one_item_per_line",
        action="store_true",
        default=True,
        help=(
            "Put each list item (e.g., function arguments) in a separate line, "
            "if the list doesn't fit into a single line."
        ),
    )
    parser.add_argument(
        "--no_one_item_per_line",
        dest="one_item_per_line",
        action="store_false",
        help="Don't use one per line formatting (see --one_item_per_line).",
    )
    action = parser.add_mutually_exclusive_group(required=False)
    action.add_argument("-i", dest="inplace", action="store_true", help="Edit files inplace.")
    action.add_argument("-c", dest="check", action="store_true", help="Check files' formats.")

    args = parser.parse_args()

    return_code = 0

    with set_one_item_per_line(args.one_item_per_line):
        for path in args.files:
            if path == "-":
                old_content = sys.stdin.read()
                filename = "<input>"
            else:
                old_content = open(path).read()
                filename = path
            try:
                new_content = cairo_parser(old_content, filename).format()
            except Exception as exc:
                print(exc, file=sys.stderr)
                return 2

            if args.inplace:
                assert path != "-", 'Using "-i" together with "-" is not supported.'
                open(path, "w").write(new_content)
            elif args.check:
                assert path != "-", 'Using "-c" together with "-" is not supported.'
                if old_content != new_content:
                    print(f'File "{path}" is incorrectly formatted.', file=sys.stderr)
                    return_code = 1
            else:
                print(new_content, end="")

    return return_code


def main():
    cairo_parser = lambda code, filename: parse_file(code=code, filename=filename)

    return cairo_format_common(
        cairo_parser=cairo_parser, description="A tool to automatically format Cairo code."
    )


if __name__ == "__main__":
    sys.exit(main())
