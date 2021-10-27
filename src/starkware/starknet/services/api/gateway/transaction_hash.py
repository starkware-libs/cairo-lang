from typing import Callable, Sequence

from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.cairo.lang.vm.crypto import pedersen_hash
from starkware.python.utils import from_bytes
from starkware.starknet.definitions.transaction_type import TransactionType


def get_tx_hash_prefix(tx_type: TransactionType) -> int:
    """
    Returns a prefix that depends on the transaction type.
    The prefix is used for the tx_hash computation.
    """
    return from_bytes(
        {
            TransactionType.DEPLOY: b"deploy",
            TransactionType.INVOKE_FUNCTION: b"invoke",
        }[tx_type]
    )


def calculate_transaction_hash(
    tx_type: TransactionType,
    contract_address: int,
    entry_point_selector: int,
    calldata: Sequence[int],
    chain_id: int,
    hash_function: Callable[[int, int], int] = pedersen_hash,
) -> int:
    """
    Calculates the transaction hash in the StarkNet network - a unique identifier of the
    transaction.
    The transaction hash is a hash chain of the following information:
        1. A prefix that depends on the transaction type.
        2. Contract address.
        3. Entry point selector.
        4. A hash chain of the calldata.
        5. The network's chain ID.
    Each hash chain computation begins with 0 as initialization and ends with its length appended.
    The length is appended in order to avoid collisions of the following kind:
    H([x,y,z]) = h(h(x,y),z) = H([w, z]) where w = h(x,y).
    """
    tx_hash_prefix = get_tx_hash_prefix(tx_type=tx_type)
    calldata_hash = compute_hash_on_elements(data=calldata, hash_func=hash_function)
    return compute_hash_on_elements(
        data=[tx_hash_prefix, contract_address, entry_point_selector, calldata_hash, chain_id],
        hash_func=hash_function,
    )
