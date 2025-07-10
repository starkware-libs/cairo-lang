import contextlib
from contextvars import ContextVar
from enum import Enum, auto
from typing import Any, Optional, Tuple

import cachetools

from starkware.starknet.public.abi import starknet_keccak

CLASS_VERSION_PREFIX = "CONTRACT_CLASS_V"


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


def hash_abi(abi: str) -> int:
    return starknet_keccak(data=bytes(abi, encoding="UTF-8"))
