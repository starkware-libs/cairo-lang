from typing import List

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.lang.vm.crypto import poseidon_hash_many
from starkware.python.utils import as_non_optional, from_bytes
from starkware.starknet.core.os.contract_class.compiled_class_hash_utils import (
    get_compiled_class_struct,
    load_compiled_class_cairo_program,
)
from starkware.starknet.core.os.contract_class.utils import ClassHashType, class_hash_cache_ctx_var
from starkware.starknet.definitions import constants
from starkware.starknet.public.abi import starknet_keccak
from starkware.starknet.services.api.contract_class.contract_class import (
    CompiledClass,
    CompiledClassEntryPoint,
    EntryPointType,
)


def compute_compiled_class_hash(compiled_class: CompiledClass) -> int:
    """
    Computes the compiled class hash.
    """
    cache = class_hash_cache_ctx_var.get()
    if cache is None:
        return _compute_compiled_class_hash_inner(compiled_class=compiled_class)

    compiled_class_bytes = compiled_class.dumps(sort_keys=True).encode()
    key = (ClassHashType.COMPILED_CLASS, starknet_keccak(data=compiled_class_bytes))

    if key not in cache:
        cache[key] = _compute_compiled_class_hash_inner(compiled_class=compiled_class)

    return cache[key]


def compute_hash_on_entry_points(entry_points: List[CompiledClassEntryPoint]) -> int:
    """
    Computes hash on a list of given entry points.
    """
    entry_point_hash_elements: List[int] = []
    for entry_point in entry_points:
        builtins_hash = poseidon_hash_many(
            [
                from_bytes(builtin.encode("ascii"))
                for builtin in as_non_optional(entry_point.builtins)
            ]
        )
        entry_point_hash_elements.extend([entry_point.selector, entry_point.offset, builtins_hash])

    return poseidon_hash_many(entry_point_hash_elements)


def _compute_compiled_class_hash_inner(compiled_class: CompiledClass) -> int:
    # Compute hashes on each component separately.
    external_funcs_hash = compute_hash_on_entry_points(
        entry_points=compiled_class.entry_points_by_type[EntryPointType.EXTERNAL]
    )
    l1_handlers_hash = compute_hash_on_entry_points(
        entry_points=compiled_class.entry_points_by_type[EntryPointType.L1_HANDLER]
    )
    constructors_hash = compute_hash_on_entry_points(
        entry_points=compiled_class.entry_points_by_type[EntryPointType.CONSTRUCTOR]
    )
    bytecode_hash = poseidon_hash_many(compiled_class.bytecode)

    # Compute total hash by hashing each component on top of the previous one.
    return poseidon_hash_many(
        [
            constants.COMPILED_CLASS_VERSION,
            external_funcs_hash,
            l1_handlers_hash,
            constructors_hash,
            bytecode_hash,
        ]
    )


def run_compiled_class_hash(compiled_class: CompiledClass) -> CairoFunctionRunner:
    program = load_compiled_class_cairo_program()
    compiled_class_struct = get_compiled_class_struct(
        identifiers=program.identifiers, compiled_class=compiled_class
    )
    runner = CairoFunctionRunner(program=program)

    runner.run(
        "starkware.starknet.core.os.contract_class.compiled_class.compiled_class_hash",
        poseidon_ptr=runner.poseidon_builtin.base,
        compiled_class=compiled_class_struct,
        use_full_name=True,
        verify_secure=False,
    )
    return runner
