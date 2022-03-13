import argparse
import json
import os
import sys
import time
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple, Type, Union

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.assembler import assemble
from starkware.cairo.lang.compiler.constants import LIBS_DIR_ENVVAR, MAIN_SCOPE, START_FILE_NAME
from starkware.cairo.lang.compiler.error_handling import LocationError
from starkware.cairo.lang.compiler.identifier_manager import IdentifierError
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition
from starkware.cairo.lang.compiler.module_reader import ModuleReader
from starkware.cairo.lang.compiler.preprocessor.auxiliary_info_collector import (
    AuxiliaryInfoCollector,
)
from starkware.cairo.lang.compiler.preprocessor.default_pass_manager import default_pass_manager
from starkware.cairo.lang.compiler.preprocessor.pass_manager import PassManager
from starkware.cairo.lang.compiler.preprocessor.preprocess_codes import preprocess_codes
from starkware.cairo.lang.compiler.preprocessor.preprocessor import PreprocessedProgram
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.version import __version__


def cairo_compile_add_common_args(parser: argparse.ArgumentParser):
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("files", metavar="file", type=str, nargs="+", help="File names")
    parser.add_argument(
        "--prime", type=int, default=DEFAULT_PRIME, help="The size of the finite field."
    )
    parser.add_argument(
        "--cairo_path",
        type=str,
        default="",
        help=(
            'A list of directories, separated by ":" to resolve import paths. '
            "The full list will consist of directories defined by this argument, followed by "
            f"the environment variable {LIBS_DIR_ENVVAR}, the working directory and the standard "
            "library path."
        ),
    )
    parser.add_argument(
        "--preprocess",
        action="store_true",
        help="Stop after the preprocessor step and output the preprocessed program.",
    )
    parser.add_argument(
        "--output", type=argparse.FileType("w"), help="The output file name (default: stdout)."
    )
    parser.add_argument(
        "--no_debug_info",
        dest="debug_info",
        action="store_false",
        help="Include debug information.",
    )
    parser.add_argument(
        "--debug_info_with_source",
        action="store_true",
        help="Include debug information with a copy of the source code.",
    )
    parser.add_argument(
        "--cairo_dependencies",
        type=str,
        help="Output a list of the Cairo source files used during the compilation as a CMake file.",
    )
    parser.add_argument(
        "--no_opt_unused_functions",
        dest="opt_unused_functions",
        action="store_false",
        default=True,
        help="Disables unused function optimization.",
    )


def cairo_compile_common(
    args: argparse.Namespace,
    pass_manager_factory: Callable[[argparse.Namespace, ModuleReader], PassManager],
    assemble_func: Callable,
) -> PreprocessedProgram:
    """
    Common code for CLI Cairo compilation.

    Arguments:
    args - Parsed arguments.
    pass_manager_factory - A pass manager factory.
    assemble_func - a function that converts a preprocessed program to the final output,
        the return value should be a Marshmallow dataclass.
    """

    start_time = time.time()
    debug_info = args.debug_info or args.debug_info_with_source

    try:
        codes = get_codes(args.files)
        out = args.output if args.output is not None else sys.stdout

        cairo_path: List[str] = list(
            filter(None, args.cairo_path.split(":") + os.getenv(LIBS_DIR_ENVVAR, "").split(":"))
        )
        module_reader = get_module_reader(cairo_path=cairo_path)

        pass_manager = pass_manager_factory(args, module_reader)

        start_codes = []
        file_contents_for_debug_info = {}
        if getattr(args, "proof_mode", False):
            start_codes = [(get_start_code(), START_FILE_NAME)]
            file_contents_for_debug_info[START_FILE_NAME] = start_codes[0][0]

        preprocessed = preprocess_codes(
            codes=codes,
            pass_manager=pass_manager,
            main_scope=MAIN_SCOPE,
            start_codes=start_codes,
        )

        if args.preprocess:
            print(preprocessed.format(with_locations=debug_info), end="", file=out)
        else:
            if args.debug_info_with_source:
                for source_file in module_reader.source_files | set(args.files):
                    file_contents_for_debug_info[source_file] = open(source_file).read()

            assembled_program = assemble_func(
                preprocessed,
                main_scope=MAIN_SCOPE,
                add_debug_info=debug_info,
                file_contents_for_debug_info=file_contents_for_debug_info,
            )

            json.dump(
                assembled_program.Schema().dump(assembled_program), out, indent=4, sort_keys=True
            )
            # Print a new line at the end.
            print(file=out)

        return preprocessed
    finally:
        if args.cairo_dependencies:
            generate_cairo_dependencies_file(
                args.cairo_dependencies, module_reader.source_files | set(args.files), start_time
            )


def get_module_reader(cairo_path: List[str]) -> ModuleReader:
    starkware_src = os.path.join(os.path.dirname(__file__), "../../../..")
    cairo_path = [
        os.path.abspath(path)
        for path in cairo_path + [os.curdir, starkware_src]
        if path is not None and os.path.isdir(path)
    ]

    return ModuleReader(paths=cairo_path, cairo_suffix=".cairo")


def get_codes(file_names: List[str]) -> List[Tuple[str, str]]:
    """
    Returns a list of pairs (file_content, file_name).
    """
    codes = (open(path).read() if path != "-" else sys.stdin.read() for path in file_names)
    codes_with_filenames = list(zip(codes, file_names))

    return codes_with_filenames


def compile_cairo_files(
    files: List[str],
    prime: Optional[int] = None,
    cairo_path: List[str] = [],
    debug_info: bool = False,
    pass_manager: Optional[PassManager] = None,
    main_scope: Optional[ScopedName] = None,
) -> Program:
    """
    Compiles a list of files (provided by their names).
    Note that cairo_path is ignored when reading the input files,
    it is only used when importing modules.
    """
    return compile_cairo(
        code=get_codes(files),
        prime=prime,
        cairo_path=cairo_path,
        debug_info=debug_info,
        pass_manager=pass_manager,
        main_scope=main_scope,
    )


def compile_cairo_ex(
    code: Union[str, Sequence[Tuple[str, str]]],
    prime: Optional[int] = None,
    cairo_path: List[str] = [],
    debug_info: bool = False,
    pass_manager: Optional[PassManager] = None,
    add_start: bool = False,
    main_scope: Optional[ScopedName] = None,
    auxiliary_info_cls: Optional[Type[AuxiliaryInfoCollector]] = None,
) -> Tuple[Program, PreprocessedProgram]:
    """
    Same as compile_cairo, but returns the preprocessed program as well.
    """
    file_contents_for_debug_info = {}

    if isinstance(code, str):
        codes_with_filenames = [(code, "")]
    if isinstance(code, list):
        codes_with_filenames = code

    start_codes = []
    if add_start:
        start_codes = [(get_start_code(), START_FILE_NAME)]
        file_contents_for_debug_info[START_FILE_NAME] = start_codes[0][0]

    if pass_manager is None:
        assert prime is not None, "Exactly one of prime and pass_manager must be given."
        module_reader = get_module_reader(cairo_path)
        pass_manager = default_pass_manager(
            prime=prime, read_module=module_reader.read, auxiliary_info_cls=auxiliary_info_cls
        )
    else:
        assert prime is None, "Exactly one of prime and pass_manager must be given."
        assert len(cairo_path) == 0, "cairo_path cannot be specified where pass_manager is used."

    if main_scope is None:
        main_scope = MAIN_SCOPE
    preprocessed_program = preprocess_codes(
        codes=codes_with_filenames,
        pass_manager=pass_manager,
        main_scope=main_scope,
        start_codes=start_codes,
    )
    program = cairo_assemble_program(
        preprocessed_program,
        main_scope=main_scope,
        add_debug_info=debug_info,
        file_contents_for_debug_info=file_contents_for_debug_info,
    )

    return program, preprocessed_program


def compile_cairo(
    code: Union[str, Sequence[Tuple[str, str]]],
    prime: Optional[int] = None,
    cairo_path: List[str] = [],
    debug_info: bool = False,
    pass_manager: Optional[PassManager] = None,
    add_start: bool = False,
    main_scope: Optional[ScopedName] = None,
) -> Program:
    """
    Compiles a single code represented by a string, or a list codes.
    The codes in the list are joined with file names, used for indicative
    compilation errors.
    Returns the program.
    """
    program, _ = compile_cairo_ex(
        code=code,
        prime=prime,
        cairo_path=cairo_path,
        debug_info=debug_info,
        pass_manager=pass_manager,
        add_start=add_start,
        main_scope=main_scope,
    )
    return program


def check_main_args(program: Program):
    """
    Makes sure that for every builtin included in the program an appropriate ptr was passed as an
    argument to main() and is subsequently returned.
    """
    expected_builtin_ptrs = [f"{builtin_name}_ptr" for builtin_name in program.builtins]

    try:
        implicit_args = list(
            get_struct_definition(
                struct_name=ScopedName.from_string("__main__.main.ImplicitArgs"),
                identifier_manager=program.identifiers,
            ).members
        )
    except IdentifierError:
        return

    try:
        main_args = implicit_args + list(
            get_struct_definition(
                struct_name=ScopedName.from_string("__main__.main.Args"),
                identifier_manager=program.identifiers,
            ).members
        )
    except IdentifierError:
        pass
    else:
        assert main_args == expected_builtin_ptrs, (
            "Expected main to contain the following arguments (in this order): "
            f"{expected_builtin_ptrs}. Found: {main_args}."
        )

    try:
        main_returns = implicit_args + list(
            get_struct_definition(
                struct_name=ScopedName.from_string("__main__.main.Return"),
                identifier_manager=program.identifiers,
            ).members
        )
    except IdentifierError:
        pass
    else:
        assert main_returns == expected_builtin_ptrs, (
            "Expected main to return the following values (in this order): "
            f"{expected_builtin_ptrs}. Found: {main_returns}."
        )


def get_start_code():
    """
    Returns a piece of code that will be executed first. This code calls the main() function and
    after main() returns, goes into an infinite loop.
    """
    return """\
__start__:
ap += main.Args.SIZE + main.ImplicitArgs.SIZE
call main

__end__:
jmp rel 0
"""


def generate_cairo_dependencies_file(dependencies_path: str, files: Set[str], start_time):
    # Generate Cairo dependencies.
    res = ""
    res += "SET (DEPENDENCIES\n"
    for filename in sorted(files):
        res += filename + "\n"
    res += ")\n"

    try:
        if open(dependencies_path).read() == res:
            # File is already up to date.
            return
    except FileNotFoundError:
        pass

    with open(dependencies_path, "w") as dependencies_file:
        dependencies_file.write(res)

    # Change the modification time of the file to make sure it is older than the generated
    # files.
    os.utime(dependencies_path, (start_time, start_time))


def cairo_assemble_program(
    preprocessed_program: PreprocessedProgram,
    main_scope: ScopedName,
    add_debug_info: bool,
    file_contents_for_debug_info: Dict[str, str],
) -> Program:
    program = assemble(
        preprocessed_program,
        main_scope=main_scope,
        add_debug_info=add_debug_info,
        file_contents_for_debug_info=file_contents_for_debug_info,
    )
    check_main_args(program)
    return program


def main():
    parser = argparse.ArgumentParser(description="A tool to compile Cairo code.")
    parser.add_argument(
        "--proof_mode",
        action="store_true",
        default=False,
        help="Add instructions to call main() at the beginning of the program. This should be used "
        "if the program is proven directly (without the bootloader).",
    )
    parser.add_argument(
        "--no_proof_mode",
        dest="proof_mode",
        action="store_false",
        help="Disable proof mode (see --proof_mode).",
    )

    def pass_manager_factory(args: argparse.Namespace, module_reader: ModuleReader) -> PassManager:
        return default_pass_manager(
            prime=args.prime,
            read_module=module_reader.read,
            opt_unused_functions=args.opt_unused_functions,
        )

    try:
        cairo_compile_add_common_args(parser)
        args = parser.parse_args()
        cairo_compile_common(
            args=args,
            pass_manager_factory=pass_manager_factory,
            assemble_func=cairo_assemble_program,
        )
    except LocationError as err:
        print(err, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
