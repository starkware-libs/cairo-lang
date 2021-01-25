import argparse
import json
import os
import sys
import time
from typing import List, Sequence, Set, Tuple, Type, Union

from starkware.cairo.lang.compiler.assembler import assemble
from starkware.cairo.lang.compiler.constants import LIBS_DIR_ENVVAR, MAIN_SCOPE, START_FILE_NAME
from starkware.cairo.lang.compiler.error_handling import LocationError
from starkware.cairo.lang.compiler.identifier_manager import IdentifierError
from starkware.cairo.lang.compiler.identifier_utils import get_struct_members
from starkware.cairo.lang.compiler.module_reader import ModuleReader
from starkware.cairo.lang.compiler.preprocessor.preprocessor import Preprocessor, preprocess_codes
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.version import __version__

DEFAULT_PRIME = 2**251 + 17 * 2**192 + 1


def main():
    start_time = time.time()

    parser = argparse.ArgumentParser(description='A tool to compile Cairo code.')
    parser.add_argument('-v', '--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('files', metavar='file', type=str, nargs='+', help='File names')
    parser.add_argument(
        '--prime', type=int, default=DEFAULT_PRIME, help='The size of the finite field.')
    parser.add_argument(
        '--cairo_path', type=str, default='',
        help=(
            'A list of directories, separated by ":" to resolve import paths. '
            'The full list will consist of directories defined by this argument, followed by '
            f'the environment variable {LIBS_DIR_ENVVAR}, the working directory and the standard '
            'library path.'))
    parser.add_argument(
        '--preprocess', action='store_true',
        help='Stop after the preprocessor step and output the preprocessed program.')
    parser.add_argument(
        '--output', type=argparse.FileType('w'), help='The output file name (default: stdout).')
    parser.add_argument(
        '--no_debug_info', dest='debug_info', action='store_false',
        help='Include debug information.')
    parser.add_argument(
        '--debug_info_with_source', action='store_true',
        help='Include debug information with a copy of the source code.')
    parser.add_argument(
        '--simple', action='store_true',
        help='Compile the program without adding additional code. '
        'In particular, program starts at the __start__ label, instead of the main() function.')
    parser.add_argument(
        '--cairo_dependencies', type=str,
        help='Output a list of the Cairo source files used during the compilation as a CMake file.')

    args = parser.parse_args()
    debug_info = args.debug_info or args.debug_info_with_source

    source_files = set()
    erred: bool = False
    try:
        codes = get_codes(args.files)
        if not args.simple:
            codes = add_start_code(codes)
        out = args.output if args.output is not None else sys.stdout

        cairo_path = list(filter(
            None, args.cairo_path.split(':') + os.getenv(LIBS_DIR_ENVVAR, '').split(':')))

        if args.preprocess:
            module_reader = get_module_reader(cairo_path)
            preprocessed = preprocess_codes(codes, args.prime, module_reader.read, MAIN_SCOPE)
            source_files = module_reader.source_files
            print(preprocessed.format(), end='', file=out)
        else:
            program, source_files = compile_cairo_extended(
                codes, args.prime, cairo_path, debug_info, simple=args.simple)
            if args.debug_info_with_source:
                for source_file in source_files | set(args.files):
                    program.debug_info.file_contents[source_file] = open(source_file).read()
            json.dump(Program.Schema().dump(program), out, indent=4, sort_keys=True)
            # Print a new line at the end.
            print(file=out)

    except LocationError as err:
        print(err, file=sys.stderr)
        erred = True

    if args.cairo_dependencies:
        generate_cairo_dependencies_file(
            args.cairo_dependencies, source_files | set(args.files), start_time)

    return 1 if erred else 0


def get_module_reader(cairo_path: List[str]) -> ModuleReader:
    starkware_src = os.path.join(os.path.dirname(__file__), '../../../..')
    cairo_path = [
        os.path.abspath(path)
        for path in cairo_path + [os.curdir, starkware_src]
        if path is not None and os.path.isdir(path)]

    return ModuleReader(paths=cairo_path, cairo_suffix='.cairo')


def get_codes(file_names: List[str]) -> List[Tuple[str, str]]:
    """
    Returns a list of pairs (file_content, file_name).
    """
    codes = (open(path).read() if path != '-' else sys.stdin.read() for path in file_names)
    codes_with_filenames = list(zip(codes, file_names))

    return codes_with_filenames


def add_start_code(codes_with_filenames: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    return [(get_start_code(), START_FILE_NAME)] + codes_with_filenames


def compile_cairo_files(
        files: List[str], prime: int,
        cairo_path: List[str] = [], debug_info: bool = False,
        preprocessor_cls: Type[Preprocessor] = Preprocessor) -> Program:
    """
    Compiles a list of files (provided by their names).
    Note that cairo_path is ignored when reading the input files,
    it is only used when importing modules.
    """
    return compile_cairo(get_codes(files), prime, cairo_path, debug_info, preprocessor_cls)


def compile_cairo(
        code: Union[str, Sequence[Tuple[str, str]]], prime: int,
        cairo_path: List[str] = [], debug_info: bool = False,
        preprocessor_cls: Type[Preprocessor] = Preprocessor,
        add_start: bool = False) -> Program:
    """
    Compiles a single code represented by a string, or a list codes.
    The codes in the list are joined with file names, used for indicative
    compilation errors.
    """
    return compile_cairo_extended(
        code=code, prime=prime, cairo_path=cairo_path, debug_info=debug_info,
        preprocessor_cls=preprocessor_cls, add_start=add_start)[0]


def compile_cairo_extended(
        code: Union[str, Sequence[Tuple[str, str]]], prime: int,
        cairo_path: List[str] = [], debug_info: bool = False,
        preprocessor_cls: Type[Preprocessor] = Preprocessor,
        add_start: bool = False, simple: bool = False) -> Tuple[Program, Set[str]]:
    """
    Same as compile_cairo(), except that imported Cairo modules are returned.
    """
    file_contents_for_debug_info = {}

    if isinstance(code, str):
        codes_with_filenames = [(code, '')]
    if isinstance(code, list):
        codes_with_filenames = code

    if add_start:
        codes_with_filenames = add_start_code(codes_with_filenames)

    # Add the start code to the debug info if exists.
    if START_FILE_NAME == codes_with_filenames[0][1]:
        file_contents_for_debug_info[START_FILE_NAME] = codes_with_filenames[0][0]

    module_reader = get_module_reader(cairo_path)
    preprocessed_program = preprocess_codes(
        codes_with_filenames, prime, module_reader.read, MAIN_SCOPE, preprocessor_cls)

    program = assemble(
        preprocessed_program, main_scope=MAIN_SCOPE, add_debug_info=debug_info,
        file_contents_for_debug_info=file_contents_for_debug_info)

    if not simple:
        check_main_args(program)

    return program, module_reader.source_files


def check_main_args(program: Program):
    """
    Makes sure that for every builtin included in the program an appropriate ptr was passed as an
    argument to main() and is subsequently returned.
    """
    expected_builtin_ptrs = [f'{builtin_name}_ptr' for builtin_name in program.builtins]
    try:
        main_args = list(get_struct_members(
            struct_name=ScopedName.from_string('__main__.main.Args'),
            identifier_manager=program.identifiers))
    except IdentifierError:
        pass
    else:
        assert main_args == expected_builtin_ptrs, \
            'Expected main to contain the following arguments (in this order): ' \
            f'{expected_builtin_ptrs}. Found: {main_args}.'

    try:
        main_returns = list(get_struct_members(
            struct_name=ScopedName.from_string('__main__.main.Return'),
            identifier_manager=program.identifiers))
    except IdentifierError:
        pass
    else:
        assert main_returns == expected_builtin_ptrs, \
            'Expected main to return the following values (in this order): ' \
            f'{expected_builtin_ptrs}. Found: {main_returns}.'


def get_start_code():
    """
    Returns a piece of code that will be executed first. This code calls the main() function and
    after main() returns, goes into an infinite loop.
    """
    return """\
__start__:
call main

__end__:
jmp rel 0
"""


def generate_cairo_dependencies_file(dependencies_path: str, files: Set[str], start_time):
    # Generate Cairo dependencies.
    res = ''
    res += 'SET (DEPENDENCIES\n'
    for filename in sorted(files):
        res += filename + '\n'
    res += ')\n'

    try:
        if open(dependencies_path).read() == res:
            # File is already up to date.
            return
    except FileNotFoundError:
        pass

    with open(dependencies_path, 'w') as dependencies_file:
        dependencies_file.write(res)

    # Change the modification time of the file to make sure it is older than the generated
    # files.
    os.utime(dependencies_path, (start_time, start_time))


if __name__ == '__main__':
    sys.exit(main())
