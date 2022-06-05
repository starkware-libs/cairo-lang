import contextlib
import dataclasses
import itertools
import json
import os
from contextvars import ContextVar
from functools import lru_cache
from typing import Callable, List, Optional

import cachetools

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
from starkware.starknet.services.api.contract_class import ContractClass, EntryPointType

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "contracts.cairo")

class_hash_cache_ctx_var: ContextVar[Optional[cachetools.LRUCache]] = ContextVar(
    "class_hash_cache", default=None
)


@contextlib.contextmanager
def set_class_hash_cache(cache: cachetools.LRUCache):
    """
    Sets a cache to be used by compute_class_hash().
    """
    assert class_hash_cache_ctx_var.get() is None, "Cannot replace an existing class_hash_cache."

    token = class_hash_cache_ctx_var.set(cache)
    try:
        yield
    finally:
        class_hash_cache_ctx_var.reset(token)


@lru_cache()
def load_program() -> Program:
    return compile_cairo_files(
        [CAIRO_FILE],
        prime=DEFAULT_PRIME,
        main_scope=ScopedName.from_string("starkware.starknet.core.os.contracts"),
    )


def compute_class_hash(
    contract_class: ContractClass, hash_func: Callable[[int, int], int] = pedersen_hash
) -> int:
    cache = class_hash_cache_ctx_var.get()
    if cache is None:
        return compute_class_hash_inner(contract_class=contract_class, hash_func=hash_func)

    contract_class_bytes = contract_class.dumps(sort_keys=True).encode()
    key = (starknet_keccak(data=contract_class_bytes), hash_func)

    if key not in cache:
        cache[key] = compute_class_hash_inner(contract_class=contract_class, hash_func=hash_func)

    return cache[key]


def compute_class_hash_inner(
    contract_class: ContractClass, hash_func: Callable[[int, int], int]
) -> int:
    program = load_program()
    contract_class_struct = get_contract_class_struct(
        identifiers=program.identifiers, contract_class=contract_class
    )
    runner = CairoFunctionRunner(program)

    hash_builtin = HashBuiltinRunner(
        name="custom_hasher", included=True, ratio=32, hash_func=hash_func
    )
    runner.builtin_runners["hash_builtin"] = hash_builtin
    hash_builtin.initialize_segments(runner)

    runner.run(
        "starkware.starknet.core.os.contracts.class_hash",
        hash_ptr=hash_builtin.base,
        contract_class=contract_class_struct,
        use_full_name=True,
        verify_secure=False,
    )
    _, class_hash = runner.get_return_values(2)
    return class_hash


def compute_hinted_class_hash(contract_class: ContractClass) -> int:
    """
    Computes the hash of the contract class, including hints.
    """
    dumped_program = dataclasses.replace(contract_class.program, debug_info=None).dump()
    if len(dumped_program["attributes"]) == 0:
        # Remove attributes field from raw dictionary, for hash backward compatibility of
        # contracts deployed prior to adding this feature.
        del dumped_program["attributes"]
    else:
        # Remove accessible_scopes and flow_tracking_data fields from raw dictionary, for hash
        # backward compatibility of contracts deployed prior to adding this feature.
        for attr in dumped_program["attributes"]:
            if len(attr["accessible_scopes"]) == 0:
                del attr["accessible_scopes"]
            if attr["flow_tracking_data"] is None:
                del attr["flow_tracking_data"]

    input_to_hash = dict(program=dumped_program, abi=contract_class.abi)
    return starknet_keccak(data=json.dumps(input_to_hash, sort_keys=True).encode())


def get_contract_entry_points(
    structs: CairoStructProxy,
    contract_class: ContractClass,
    entry_point_type: EntryPointType,
) -> List[CairoStructProxy]:
    # Check validity of entry points.
    program_length = len(contract_class.program.data)
    entry_points = contract_class.entry_points_by_type[entry_point_type]
    for entry_point in entry_points:
        assert (
            0 <= entry_point.offset < program_length
        ), f"Invalid entry point offset {entry_point.offset}, len(program_data)={program_length}."

    return [
        structs.ContractEntryPoint(selector=entry_point.selector, offset=entry_point.offset)
        for entry_point in entry_points
    ]


def get_contract_class_struct(
    identifiers: IdentifierManager, contract_class: ContractClass
) -> CairoStructProxy:
    """
    Returns the serialization of a contract as a list of field elements.
    """
    structs = CairoStructFactory(
        identifiers=identifiers,
        additional_imports=[
            "starkware.starknet.core.os.contracts.ContractClass",
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
            contract_class=contract_class,
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

    builtin_list = contract_class.program.builtins
    return structs.ContractClass(
        api_version=API_VERSION_IDENT.value,
        n_external_functions=len(external_functions),
        external_functions=flat_external_functions,
        n_l1_handlers=len(l1_handlers),
        l1_handlers=flat_l1_handlers,
        n_constructors=len(constructors),
        constructors=flat_constructors,
        n_builtins=len(builtin_list),
        builtin_list=[from_bytes(builtin.encode("ascii")) for builtin in builtin_list],
        hinted_class_hash=compute_hinted_class_hash(contract_class=contract_class),
        bytecode_length=len(contract_class.program.data),
        bytecode_ptr=contract_class.program.data,
    )
