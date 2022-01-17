import dataclasses
import itertools
import json
import os
from typing import Callable, List

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.structs import CairoStructFactory, CairoStructProxy
from starkware.cairo.lang.builtins.hash.hash_builtin_runner import HashBuiltinRunner
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.cairo.lang.compiler.identifier_definition import ConstDefinition
from starkware.cairo.lang.compiler.identifier_manager import IdentifierManager
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.vm.crypto import pedersen_hash
from starkware.python.utils import from_bytes
from starkware.starknet.public.abi import starknet_keccak
from starkware.starknet.services.api.contract_definition import ContractDefinition, EntryPointType

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "contracts.cairo")


def load_program() -> Program:
    return compile_cairo_files(
        [CAIRO_FILE],
        prime=DEFAULT_PRIME,
        main_scope=ScopedName.from_string("starkware.starknet.core.os.contracts"),
    )


def compute_contract_hash(
    contract_definition: ContractDefinition, hash_func: Callable[[int, int], int] = pedersen_hash
) -> int:
    program = load_program()
    contract_definition_struct = get_contract_definition_struct(
        identifiers=program.identifiers, contract_definition=contract_definition
    )
    runner = CairoFunctionRunner(program)

    hash_builtin = HashBuiltinRunner(
        name="custom_hasher", included=True, ratio=32, hash_func=hash_func
    )
    runner.builtin_runners["hash_builtin"] = hash_builtin
    hash_builtin.initialize_segments(runner)

    runner.run(
        "starkware.starknet.core.os.contracts.contract_hash",
        hash_ptr=hash_builtin.base,
        contract_definition=contract_definition_struct,
        use_full_name=True,
        verify_secure=False,
    )
    _, contract_hash = runner.get_return_values(2)
    return contract_hash


def compute_hinted_contract_definition_hash(contract_definition: ContractDefinition) -> int:
    """
    Computes the hash of the contract definition, including hints.
    """
    dumped_program = Program.Schema().dump(
        obj=dataclasses.replace(contract_definition.program, debug_info=None)
    )
    if len(dumped_program["attributes"]) == 0:
        # Remove attributes field from raw dictionary, for hash backward compatibility of
        # contracts deployed prior to adding this feature.
        del dumped_program["attributes"]

    input_to_hash = dict(program=dumped_program, abi=contract_definition.abi)
    return starknet_keccak(data=json.dumps(input_to_hash, sort_keys=True).encode())


def get_contract_entry_points(
    structs: CairoStructProxy,
    contract_definition: ContractDefinition,
    entry_point_type: EntryPointType,
) -> List[CairoStructProxy]:
    # Check validity of entry points.
    program_length = len(contract_definition.program.data)
    entry_points = contract_definition.entry_points_by_type[entry_point_type]
    for entry_point in entry_points:
        assert (
            0 <= entry_point.offset < program_length
        ), f"Invalid entry point offset {entry_point.offset}, len(program_data)={program_length}."

    return [
        structs.ContractEntryPoint(selector=entry_point.selector, offset=entry_point.offset)
        for entry_point in entry_points
    ]


def get_contract_definition_struct(
    identifiers: IdentifierManager, contract_definition: ContractDefinition
) -> CairoStructProxy:
    """
    Returns the serialization of a contract as a list of field elements.
    """
    structs = CairoStructFactory(
        identifiers=identifiers,
        additional_imports=[
            "starkware.starknet.core.os.contracts.ContractDefinition",
            "starkware.starknet.core.os.contracts.ContractEntryPoint",
        ],
    ).structs

    API_VERSION_IDENT = identifiers.get_by_full_name(
        ScopedName.from_string("starkware.starknet.core.os.contracts.API_VERSION")
    )
    assert isinstance(API_VERSION_IDENT, ConstDefinition)

    external_functions, l1_handlers, constructors = (
        get_contract_entry_points(
            structs=structs,
            contract_definition=contract_definition,
            entry_point_type=entry_point_type,
        )
        for entry_point_type in (
            EntryPointType.EXTERNAL,
            EntryPointType.L1_HANDLER,
            EntryPointType.CONSTRUCTOR,
        )
    )
    flat_external_functions, flat_l1_handlers, flat_constructors = (
        list(itertools.chain.from_iterable(entry_points))
        for entry_points in (external_functions, l1_handlers, constructors)
    )

    builtin_list = contract_definition.program.builtins
    return structs.ContractDefinition(
        api_version=API_VERSION_IDENT.value,
        n_external_functions=len(external_functions),
        external_functions=flat_external_functions,
        n_l1_handlers=len(l1_handlers),
        l1_handlers=flat_l1_handlers,
        n_constructors=len(constructors),
        constructors=flat_constructors,
        n_builtins=len(builtin_list),
        builtin_list=[from_bytes(builtin.encode("ascii")) for builtin in builtin_list],
        hinted_contract_definition_hash=compute_hinted_contract_definition_hash(
            contract_definition=contract_definition
        ),
        bytecode_length=len(contract_definition.program.data),
        bytecode_ptr=contract_definition.program.data,
    )
