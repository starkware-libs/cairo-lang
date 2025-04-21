import functools
from typing import FrozenSet

from starkware.starknet.definitions.constants import get_versioned_constants_json


@functools.lru_cache()
def get_v1_bound_accounts_cairo0() -> FrozenSet[int]:
    hex_list = get_versioned_constants_json()["os_constants"]["v1_bound_accounts_cairo0"]
    return frozenset(int(x, 16) for x in hex_list)


@functools.lru_cache()
def get_v1_bound_accounts_cairo1() -> FrozenSet[int]:
    hex_list = get_versioned_constants_json()["os_constants"]["v1_bound_accounts_cairo1"]
    return frozenset(int(x, 16) for x in hex_list)


@functools.lru_cache()
def get_v1_bound_accounts_max_tip() -> int:
    hex_val = get_versioned_constants_json()["os_constants"]["v1_bound_accounts_max_tip"]
    assert hex_val.startswith("0x")
    return int(hex_val, 16)


@functools.lru_cache()
def get_data_gas_accounts() -> FrozenSet[int]:
    hex_list = get_versioned_constants_json()["os_constants"]["data_gas_accounts"]
    return frozenset(int(x, 16) for x in hex_list)
