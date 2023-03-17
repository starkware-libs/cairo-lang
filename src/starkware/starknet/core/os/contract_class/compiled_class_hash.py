from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.starknet.core.os.contract_class.compiled_class_hash_utils import (
    get_compiled_class_struct,
    load_compiled_class_cairo_program,
)
from starkware.starknet.core.os.contract_class.utils import ClassHashType, class_hash_cache_ctx_var
from starkware.starknet.public.abi import starknet_keccak
from starkware.starknet.services.api.contract_class.contract_class import CompiledClass


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


def _compute_compiled_class_hash_inner(compiled_class: CompiledClass) -> int:
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
    _, class_hash = runner.get_return_values(2)
    return class_hash
