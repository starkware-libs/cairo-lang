import json
import os
from typing import Callable

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
from starkware.starknet.public.abi import starknet_keccak
from starkware.starknet.services.api.contract_definition import ContractDefinition, EntryPointType
from starkware.storage.storage import HASH_BYTES

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "contracts.cairo")


def load_program() -> Program:
    return compile_cairo_files(
        [CAIRO_FILE],
        prime=DEFAULT_PRIME,
        main_scope=ScopedName.from_string("starkware.starknet.core.os.contracts"),
    )


def compute_contract_hash(
    contract_definition: ContractDefinition, hash_func: Callable[[int, int], int] = pedersen_hash
) -> bytes:
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
    return contract_hash.to_bytes(HASH_BYTES, "big")


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

    # Check validity of endpoints.
    program_len = len(contract_definition.program.data)
    for entry_points in contract_definition.entry_points_by_type.values():
        for entry_point in entry_points:
            assert (
                0 <= entry_point.offset < program_len
            ), f"Invalid entry point offset {entry_point.offset}, len(program_data)={program_len}."

    builtin_list = contract_definition.program.builtins

    API_VERSION_IDENT = identifiers.get_by_full_name(
        ScopedName.from_string("starkware.starknet.core.os.contracts.API_VERSION")
    )

    external_functions = contract_definition.entry_points_by_type[EntryPointType.EXTERNAL]
    l1_handlers = contract_definition.entry_points_by_type[EntryPointType.L1_HANDLER]
    assert isinstance(API_VERSION_IDENT, ConstDefinition)
    return structs.ContractDefinition(
        api_version=API_VERSION_IDENT.value,
        n_external_functions=len(external_functions),
        external_functions=sum(
            [
                structs.ContractEntryPoint(selector=entry_point.selector, offset=entry_point.offset)
                for entry_point in external_functions
            ],
            (),
        ),
        n_l1_handlers=len(l1_handlers),
        l1_handlers=sum(
            [
                structs.ContractEntryPoint(selector=entry_point.selector, offset=entry_point.offset)
                for entry_point in l1_handlers
            ],
            (),
        ),
        n_builtins=len(builtin_list),
        builtin_list=[int.from_bytes(builtin.encode("ascii"), "big") for builtin in builtin_list],
        hinted_contract_definition_hash=starknet_keccak(
            json.dumps(
                {
                    "program": Program.Schema().dump(obj=contract_definition.program),
                    "abi": contract_definition.abi,
                },
                sort_keys=True,
            ).encode()
        ),
        bytecode_length=len(contract_definition.program.data),
        bytecode_ptr=contract_definition.program.data,
    )
