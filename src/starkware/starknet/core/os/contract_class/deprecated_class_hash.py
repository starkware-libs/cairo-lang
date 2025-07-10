import dataclasses
import json
from typing import Callable, Dict, List

from starkware.cairo.common.hash_state import HashState
from starkware.cairo.common.structs import CairoStructProxy
from starkware.cairo.lang.compiler.ast.cairo_types import add_backward_compatibility_space
from starkware.cairo.lang.vm.crypto import pedersen_hash
from starkware.python.utils import from_bytes
from starkware.starknet.core.os.contract_class.utils import ClassHashType, class_hash_cache_ctx_var
from starkware.starknet.public.abi import starknet_keccak
from starkware.starknet.services.api.contract_class.contract_class import (
    CompiledClassEntryPoint,
    DeprecatedCompiledClass,
    EntryPointType,
)


def compute_deprecated_class_hash(
    contract_class: DeprecatedCompiledClass, hash_func: Callable[[int, int], int] = pedersen_hash
) -> int:
    cache = class_hash_cache_ctx_var.get()
    if cache is None:
        return compute_deprecated_class_hash_inner(
            contract_class=contract_class, hash_func=hash_func
        )

    contract_class_bytes = contract_class.dumps(sort_keys=True).encode()
    key = (
        ClassHashType.DEPRECATED_COMPILED_CLASS,
        (starknet_keccak(data=contract_class_bytes), hash_func),
    )

    if key not in cache:
        cache[key] = compute_deprecated_class_hash_inner(
            contract_class=contract_class, hash_func=hash_func
        )

    return cache[key]


def compute_deprecated_class_hash_inner(
    contract_class: DeprecatedCompiledClass, hash_func: Callable[[int, int], int]
) -> int:
    deprecated_compiled_class_version = 0
    flat_entry_point_lists = py_get_flat_entry_points(contract_class=contract_class)
    external_entry_points, l1_handlers, ctor_entry_points = (
        flat_entry_point_lists[EntryPointType.EXTERNAL],
        flat_entry_point_lists[EntryPointType.L1_HANDLER],
        flat_entry_point_lists[EntryPointType.CONSTRUCTOR],
    )
    builtins = get_builtins_as_integers(contract_class=contract_class)
    hinted_class_hash = compute_deprecated_hinted_class_hash(contract_class=contract_class)
    bytecode = contract_class.program.data

    hash_state = HashState.init(hash_func=hash_func)
    hash_state.update_single(value=deprecated_compiled_class_version)
    hash_state.update_with_hashchain(values=external_entry_points)
    hash_state.update_with_hashchain(values=l1_handlers)
    hash_state.update_with_hashchain(values=ctor_entry_points)
    hash_state.update_with_hashchain(values=builtins)
    hash_state.update_single(value=hinted_class_hash)
    hash_state.update_with_hashchain(values=bytecode)
    return hash_state.finalize()


def compute_deprecated_hinted_class_hash(contract_class: DeprecatedCompiledClass) -> int:
    """
    Computes the hash of the contract class, including hints.
    """
    program_without_debug_info = dataclasses.replace(contract_class.program, debug_info=None)

    # If compiler_version is not present, this was compiled with a compiler before version 0.10.0.
    # Use "(a : felt)" syntax instead of "(a: felt)" so that the class hash will be the same.
    with add_backward_compatibility_space(contract_class.program.compiler_version is None):
        dumped_program = program_without_debug_info.dump()

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


def get_builtins_as_integers(contract_class: DeprecatedCompiledClass) -> List[int]:
    return [from_bytes(builtin.encode("ascii")) for builtin in contract_class.program.builtins]


def py_get_contract_entry_points(
    contract_class: DeprecatedCompiledClass,
    entry_point_type: EntryPointType,
) -> List[CompiledClassEntryPoint]:
    # Check validity of entry points.
    program_length = len(contract_class.program.data)
    entry_points = contract_class.entry_points_by_type[entry_point_type]
    for entry_point in entry_points:
        assert (
            0 <= entry_point.offset < program_length
        ), f"Invalid entry point offset {entry_point.offset}, len(program_data)={program_length}."
    return entry_points


def py_get_flat_entry_points(
    contract_class: DeprecatedCompiledClass,
) -> Dict[EntryPointType, List[int]]:
    external_functions, l1_handlers, constructors = (
        py_get_contract_entry_points(
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
        [x for entry_point in entry_points for x in (entry_point.selector, entry_point.offset)]
        for entry_points in (external_functions, l1_handlers, constructors)
    )
    return {
        EntryPointType.EXTERNAL: flat_external_functions,
        EntryPointType.L1_HANDLER: flat_l1_handlers,
        EntryPointType.CONSTRUCTOR: flat_constructors,
    }


def get_contract_entry_points(
    structs: CairoStructProxy,
    contract_class: DeprecatedCompiledClass,
    entry_point_type: EntryPointType,
) -> List[CairoStructProxy]:
    entry_points = py_get_contract_entry_points(
        contract_class=contract_class, entry_point_type=entry_point_type
    )

    return [
        structs.DeprecatedContractEntryPoint(
            selector=entry_point.selector, offset=entry_point.offset
        )
        for entry_point in entry_points
    ]
