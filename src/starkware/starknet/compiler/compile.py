import argparse
import json
import sys
from typing import Dict, List, Optional, Tuple

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.assembler import assemble
from starkware.cairo.lang.compiler.cairo_compile import (
    cairo_compile_add_common_args,
    cairo_compile_common,
    compile_cairo_ex,
    get_codes,
    get_module_reader,
)
from starkware.cairo.lang.compiler.error_handling import LocationError
from starkware.cairo.lang.compiler.identifier_definition import FunctionDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierScope, MissingIdentifierError
from starkware.cairo.lang.compiler.module_reader import ModuleReader
from starkware.cairo.lang.compiler.preprocessor.pass_manager import PassManager
from starkware.cairo.lang.compiler.preprocessor.preprocessor import PreprocessedProgram
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.starknet.compiler.external_wrapper import (
    CONSTRUCTOR_DECORATOR,
    EXTERNAL_DECORATOR,
    L1_HANDLER_DECORATOR,
    VIEW_DECORATOR,
    WRAPPER_SCOPE,
)
from starkware.starknet.compiler.starknet_pass_manager import starknet_pass_manager
from starkware.starknet.compiler.starknet_preprocessor import StarknetPreprocessedProgram
from starkware.starknet.compiler.validation_utils import verify_account_contract
from starkware.starknet.public.abi import AbiType, get_selector_from_name
from starkware.starknet.services.api.contract_definition import (
    ContractDefinition,
    ContractEntryPoint,
    EntryPointType,
)


def get_entry_points(program: Program) -> Dict[str, ContractEntryPoint]:
    """
    Returns a mapping from entry point name to (selector, offset).
    """
    try:
        wrapper_scope = program.identifiers.get_scope(name=WRAPPER_SCOPE)
    except MissingIdentifierError:
        # If the WRAPPER_SCOPE is missing, there are no external functions.
        return {}

    return {
        func_name: ContractEntryPoint(
            selector=get_selector_from_name(func_name=func_name), offset=func_def.pc
        )
        for func_name, func_def in wrapper_scope.identifiers.items()
        if isinstance(func_def, FunctionDefinition)
    }


def get_entry_points_by_type(program: Program) -> Dict[EntryPointType, List[ContractEntryPoint]]:
    """
    Returns a mapping from entry point type to a list of entry points of that type.
    """
    try:
        wrapper_scope = program.identifiers.get_scope(name=WRAPPER_SCOPE)
    except MissingIdentifierError:
        # If the WRAPPER_SCOPE is missing, there are no external functions.
        return {entry_point_type: [] for entry_point_type in EntryPointType}

    return {
        EntryPointType.EXTERNAL: get_entry_points_by_decorators(
            wrapper_scope=wrapper_scope, decorators=(EXTERNAL_DECORATOR, VIEW_DECORATOR)
        ),
        EntryPointType.L1_HANDLER: get_entry_points_by_decorators(
            wrapper_scope=wrapper_scope, decorators=(L1_HANDLER_DECORATOR,)
        ),
        EntryPointType.CONSTRUCTOR: get_entry_points_by_decorators(
            wrapper_scope=wrapper_scope, decorators=(CONSTRUCTOR_DECORATOR,)
        ),
    }


def get_entry_points_by_decorators(
    wrapper_scope: IdentifierScope, decorators: Tuple[str, ...]
) -> List[ContractEntryPoint]:
    return sorted(
        [
            ContractEntryPoint(
                selector=get_selector_from_name(func_name=func_name), offset=func_def.pc
            )
            for func_name, func_def in wrapper_scope.identifiers.items()
            if isinstance(func_def, FunctionDefinition)
            and any(decorator in func_def.decorators for decorator in decorators)
        ],
        key=lambda entry_point: entry_point.selector,
    )


def get_abi(preprocessed: PreprocessedProgram) -> AbiType:
    assert isinstance(preprocessed, StarknetPreprocessedProgram)
    return preprocessed.abi


def compile_starknet_files(
    files,
    debug_info: bool = False,
    disable_hint_validation: bool = False,
    cairo_path: Optional[List[str]] = None,
) -> ContractDefinition:
    return compile_starknet_codes(
        codes=get_codes(files),
        debug_info=debug_info,
        disable_hint_validation=disable_hint_validation,
        cairo_path=cairo_path,
    )


def compile_starknet_codes(
    codes: List[Tuple[str, str]],
    debug_info: bool = False,
    disable_hint_validation: bool = False,
    cairo_path: Optional[List[str]] = None,
) -> ContractDefinition:
    if cairo_path is None:
        cairo_path = []
    module_reader = get_module_reader(cairo_path=cairo_path)

    pass_manager = starknet_pass_manager(
        prime=DEFAULT_PRIME,
        read_module=module_reader.read,
        disable_hint_validation=disable_hint_validation,
    )

    program, preprocessed = compile_cairo_ex(
        code=codes, debug_info=debug_info, pass_manager=pass_manager
    )

    # Dump and load program, so that it is converted to the canonical form.
    program = Program.load(data=program.dump())

    return ContractDefinition(
        program=program,
        entry_points_by_type=get_entry_points_by_type(program=program),
        abi=get_abi(preprocessed=preprocessed),
    )


def assemble_starknet_contract(
    preprocessed_program: StarknetPreprocessedProgram,
    main_scope: ScopedName,
    add_debug_info: bool,
    file_contents_for_debug_info: Dict[str, str],
) -> ContractDefinition:
    abi = get_abi(preprocessed=preprocessed_program)
    program = assemble(
        preprocessed_program,
        main_scope=main_scope,
        add_debug_info=add_debug_info,
        file_contents_for_debug_info=file_contents_for_debug_info,
    )

    return ContractDefinition(
        program=program,
        entry_points_by_type=get_entry_points_by_type(program=program),
        abi=abi,
    )


def main():
    parser = argparse.ArgumentParser(description="A tool to compile StarkNet contracts.")
    parser.add_argument("--abi", type=argparse.FileType("w"), help="Output the contract's ABI.")
    parser.add_argument(
        "--disable_hint_validation", action="store_true", help="Disable the hint validation."
    )
    parser.add_argument(
        "--account_contract", action="store_true", help="Compile as account contract."
    )

    def pass_manager_factory(args: argparse.Namespace, module_reader: ModuleReader) -> PassManager:
        return starknet_pass_manager(
            prime=args.prime,
            read_module=module_reader.read,
            disable_hint_validation=args.disable_hint_validation,
        )

    try:
        cairo_compile_add_common_args(parser)
        args = parser.parse_args()
        preprocessed = cairo_compile_common(
            args=args,
            pass_manager_factory=pass_manager_factory,
            assemble_func=assemble_starknet_contract,
        )
        abi = get_abi(preprocessed=preprocessed)
        verify_account_contract(contract_abi=abi, is_account_contract=args.account_contract)
        if args.abi is not None:
            json.dump(abi, args.abi, indent=4, sort_keys=True)
            args.abi.write("\n")
    except LocationError as err:
        print(err, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
