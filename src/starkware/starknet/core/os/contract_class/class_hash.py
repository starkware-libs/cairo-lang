import contextlib
from contextvars import ContextVar
from enum import Enum, auto
from typing import Any, Optional, Tuple

import cachetools

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.starknet.core.os.contract_class.contract_class import (
    get_contract_class_struct,
    load_contract_class_cairo_program,
)
from starkware.starknet.public.abi import starknet_keccak
from starkware.starknet.services.api.contract_class.contract_class import ContractClass


class ClassHashType(Enum):
    CONTRACT_CLASS = 0
    COMPILED_CLASS = auto()
    DEPRECATED_COMPILED_CLASS = auto()


ClassHashCacheKeyType = Tuple[ClassHashType, Any]

class_hash_cache_ctx_var: ContextVar[
    Optional[cachetools.LRUCache[ClassHashCacheKeyType, int]]
] = ContextVar("class_hash_cache", default=None)


@contextlib.contextmanager
def set_class_hash_cache(cache: cachetools.LRUCache[ClassHashCacheKeyType, int]):
    """
    Sets a cache to be used by compute_class_hash().
    """
    assert class_hash_cache_ctx_var.get() is None, "Cannot replace an existing class_hash_cache."

    token = class_hash_cache_ctx_var.set(cache)
    try:
        yield
    finally:
        class_hash_cache_ctx_var.reset(token)


def compute_class_hash(contract_class: ContractClass) -> int:
    cache = class_hash_cache_ctx_var.get()
    if cache is None:
        return _compute_class_hash_inner(contract_class=contract_class)

    contract_class_bytes = contract_class.dumps(sort_keys=True).encode()
    key = (ClassHashType.CONTRACT_CLASS, starknet_keccak(data=contract_class_bytes))

    if key not in cache:
        cache[key] = _compute_class_hash_inner(contract_class=contract_class)

    return cache[key]


def _compute_class_hash_inner(contract_class: ContractClass) -> int:
    program = load_contract_class_cairo_program()
    contract_class_struct = get_contract_class_struct(
        identifiers=program.identifiers, contract_class=contract_class
    )
    runner = CairoFunctionRunner(program=program)

    runner.run(
        "starkware.starknet.core.os.contract_class.contract_class.class_hash",
        poseidon_ptr=runner.poseidon_builtin.base,
        contract_class=contract_class_struct,
        use_full_name=True,
        verify_secure=False,
    )
    _, class_hash = runner.get_return_values(2)
    return class_hash
