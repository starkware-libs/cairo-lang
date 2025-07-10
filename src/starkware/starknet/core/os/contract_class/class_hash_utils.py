from typing import List, NamedTuple

from starkware.cairo.lang.vm.crypto import poseidon_hash_many
from starkware.python.utils import from_bytes
from starkware.starknet.core.os.contract_class.utils import CLASS_VERSION_PREFIX, hash_abi
from starkware.starknet.public.abi import ADDR_BOUND
from starkware.starknet.services.api.contract_class.contract_class import (
    ContractClass,
    ContractEntryPoint,
    EntryPointType,
)


class ContractClassComponentHashes(NamedTuple):
    """
    Holds the hashes of the contract class components, to be used for calculating the final hash.
    Note: the order of the struct member must not be changed since it determines the hash order.
    """

    contract_class_version: int
    external_functions_hash: int
    l1_handlers_hash: int
    constructors_hash: int
    abi_hash: int
    sierra_program_hash: int


def compute_hash_on_entry_points(entry_points: List[ContractEntryPoint]) -> int:
    """
    Computes hash on a list of given entry points.
    """
    flat_entry_points = [
        value
        for entry_point in entry_points
        for value in [entry_point.selector, entry_point.function_idx]
    ]
    return poseidon_hash_many(flat_entry_points)


def py_compute_class_hash(contract_class: ContractClass) -> int:
    # Compute hashes on each component separately.
    contract_class_component_hashes = py_hash_class_components(contract_class=contract_class)
    # Compute total hash by hashing each component on top of the previous one.
    return py_finalize_class_hash(contract_class_component_hashes=contract_class_component_hashes)


def py_hash_class_components(contract_class: ContractClass) -> ContractClassComponentHashes:
    return ContractClassComponentHashes(
        contract_class_version=from_bytes(
            (CLASS_VERSION_PREFIX + contract_class.contract_class_version).encode("ascii")
        ),
        external_functions_hash=compute_hash_on_entry_points(
            entry_points=contract_class.entry_points_by_type[EntryPointType.EXTERNAL]
        ),
        l1_handlers_hash=compute_hash_on_entry_points(
            entry_points=contract_class.entry_points_by_type[EntryPointType.L1_HANDLER]
        ),
        constructors_hash=compute_hash_on_entry_points(
            entry_points=contract_class.entry_points_by_type[EntryPointType.CONSTRUCTOR]
        ),
        abi_hash=hash_abi(abi=contract_class.abi),
        sierra_program_hash=poseidon_hash_many(contract_class.sierra_program),
    )


def py_finalize_class_hash(contract_class_component_hashes: ContractClassComponentHashes) -> int:
    hash_res = poseidon_hash_many(list(contract_class_component_hashes))
    return hash_res % ADDR_BOUND
