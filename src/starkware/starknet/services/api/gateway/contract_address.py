from typing import Callable, Sequence

from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.cairo.lang.vm.crypto import pedersen_hash
from starkware.python.utils import from_bytes
from starkware.starknet.core.os.contract_hash import compute_contract_hash
from starkware.starknet.services.api.contract_definition import ContractDefinition

CONTRACT_ADDRESS_PREFIX = from_bytes(b"STARKNET_CONTRACT_ADDRESS")


def calculate_contract_address(
    salt: int,
    contract_definition: ContractDefinition,
    constructor_calldata: Sequence[int],
    caller_address: int,
    hash_function: Callable[[int, int], int] = pedersen_hash,
) -> int:
    """
    Calculates the contract address in the starkNet network - a unique identifier of the contract.
    The contract address is a hash chain of the following information:
        1. Prefix.
        2. Caller address.
        3. Salt.
        4. Contract hash.
    """
    contract_hash = compute_contract_hash(
        contract_definition=contract_definition, hash_func=hash_function
    )
    return calculate_contract_address_from_hash(
        salt=salt,
        contract_hash=contract_hash,
        constructor_calldata=constructor_calldata,
        caller_address=caller_address,
        hash_function=hash_function,
    )


def calculate_contract_address_from_hash(
    salt: int,
    contract_hash: int,
    constructor_calldata: Sequence[int],
    caller_address: int,
    hash_function: Callable[[int, int], int] = pedersen_hash,
) -> int:
    """
    Same as calculate_contract_address(), except that it gets contract_hash instead of
    contract_definition.
    """
    constructor_calldata_hash = compute_hash_on_elements(
        data=constructor_calldata, hash_func=hash_function
    )
    return compute_hash_on_elements(
        data=[
            CONTRACT_ADDRESS_PREFIX,
            caller_address,
            salt,
            contract_hash,
            constructor_calldata_hash,
        ],
        hash_func=hash_function,
    )
