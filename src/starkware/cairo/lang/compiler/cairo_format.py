import argparse
import sys
from typing import Callable, Optional

from starkware.cairo.lang.compiler.ast.formatting_utils import set_one_item_per_line
from starkware.cairo.lang.compiler.ast.module import CairoFile
from starkware.cairo.lang.compiler.parser import parse_file
from starkware.cairo.lang.version import __version__

ParserCallback = Callable[[str, str], CairoFile]


def cairo_format_arg_parser(description: str) -> argparse.ArgumentParser:
    arg_parser = argparse.ArgumentParser(description=description)
    arg_parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    arg_parser.add_argument("files", metavar="file", type=str, nargs="+", help="File names")
    arg_parser.add_argument(
        "--one_item_per_line",
        action="store_true",
        default=True,
        help=(
            "Put each list item (e.g., function arguments) in a separate line, "
            "if the list doesn't fit into a single line."
        ),
    )
    arg_parser.add_argument(
        "--no_one_item_per_line",
        dest="one_item_per_line",
        action="store_false",
        help="Don't use one per line formatting (see --one_item_per_line).",
    )
    action = arg_parser.add_mutually_exclusive_group(required=False)
    action.add_argument("-i", dest="inplace", action="store_true", help="Edit files inplace.")
    action.add_argument("-c", dest="check", action="store_true", help="Check files' formats.")

    return arg_parser


def cairo_format_common(
    args: argparse.Namespace,
    cairo_parser: ParserCallback,
    validate_parser: Optional[ParserCallback] = None,
):
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
                ast = cairo_parser(old_content, filename)
                new_content = ast.format()

                if validate_parser is not None:
                    # If validate_parser is given, re-parse the result and make sure it returns
                    # the same AST.
                    validated_content = validate_parser(new_content, filename).format()
                    assert new_content == validated_content, (
                        "Error: Formatting validation failed.\n"
                        f"Before validation:\n{new_content}\n\n\n"
                        f"After validation:\n{validated_content}"
                    )
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
    arg_parser = cairo_format_arg_parser(description="A tool to automatically format Cairo code.")
    args = arg_parser.parse_args()

    return cairo_format_common(args=args, cairo_parser=parse_file)


if __name__ == "__main__":
    sys.exit(main())
