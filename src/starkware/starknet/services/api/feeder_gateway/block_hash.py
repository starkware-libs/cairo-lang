import asyncio
import functools
from typing import Callable, Iterable, List, Sequence

from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.cairo.lang.vm.crypto import pedersen_hash
from starkware.python.utils import from_bytes, safe_zip, to_bytes
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starkware_utils.commitment_tree.patricia_tree.patricia_tree import PatriciaTree
from starkware.storage.dict_storage import DictStorage
from starkware.storage.storage import FactFetchingContext
from starkware.storage.storage_utils import SimpleLeafFact


async def calculate_block_hash(
    general_config: StarknetGeneralConfig,
    parent_hash: int,
    block_number: int,
    global_state_root: bytes,
    block_timestamp: int,
    tx_hashes: Sequence[int],
    tx_signatures: Sequence[List[int]],
    event_hashes: Sequence[int],
    hash_function: Callable[[int, int], int] = pedersen_hash,
) -> int:
    """
    Calculates the block hash in the StarkNet network.
    The block hash is a hash chain of the following information:
        1. Parent block hash.
        2. Block number.
        3. New global state root.
        4. Sequencer address.
        5. Block timestamp.
        6. Number of transactions.
        7. A commitment on the transactions.
        8. Number of events.
        9. A commitment on the events.
        10. Protocol version (not implemented yet).
        11. Extra data (not implemented yet).
    Each hash chain computation begins with 0 as initialization and ends with its length appended.
    The length is appended in order to avoid collisions of the following kind:
    H([x,y,z]) = h(h(x,y),z) = H([w, z]) where w = h(x,y).
    """
    def bytes_hash_function(x: bytes, y: bytes) -> bytes:
        return to_bytes(hash_function(from_bytes(x), from_bytes(y)))

    ffc = FactFetchingContext(storage=DictStorage(), hash_func=bytes_hash_function)

    # Include signatures in transaction hashes on a separate thread (due to it being CPU-intensive).
    calculate_tx_hashes = functools.partial(
        calculate_tx_hashes_with_signatures,
        tx_hashes=tx_hashes,
        tx_signatures=tx_signatures,
        hash_function=hash_function,
    )
    tx_final_hashes = await asyncio.get_event_loop().run_in_executor(None, calculate_tx_hashes)

    # Calculate transaction commitment.
    tx_commitment = await calculate_patricia_root(
        leaves=tx_final_hashes,
        height=general_config.tx_commitment_tree_height,
        ffc=ffc,
    )

    event_commitment = await calculate_patricia_root(
        leaves=event_hashes, height=general_config.event_commitment_tree_height, ffc=ffc
    )

    return compute_hash_on_elements(
        data=[
            block_number,
            from_bytes(global_state_root),
            general_config.sequencer_address,
            block_timestamp,
            len(tx_hashes),  # Number of transactions.
            tx_commitment,  # Transaction commitment.
            len(event_hashes),  # Number of events.
            event_commitment,  # Event commitment.
            0,  # Protocol version.
            0,  # Extra data.
            # Must be last for future optimization; that way we can separate the calculation of all
            # the other fields, which depend on the block itself, from the parent block hash,
            # as the hash is calculated in the following order: H([x,y,z]) = h(h(x,y),z).
            parent_hash,
        ],
        hash_func=hash_function,
    )


def calculate_tx_hashes_with_signatures(
    tx_hashes: Iterable[int],
    tx_signatures: Iterable[List[int]],
    hash_function: Callable[[int, int], int],
) -> Iterable[int]:
    return (
        calculate_single_tx_hash_with_signature(
            tx_hash=tx_hash, tx_signature=tx_signature, hash_function=hash_function
        )
        for (tx_hash, tx_signature) in safe_zip(tx_hashes, tx_signatures)
    )


def calculate_single_tx_hash_with_signature(
    tx_hash: int,
    tx_signature: List[int],
    hash_function: Callable[[int, int], int],
) -> int:
    """
    Hashes the signature with the given transaction hash, to get a hash that takes into account the
    entire transaction, as the original hash does not include the signature.
    """
    signature_hash = compute_hash_on_elements(data=tx_signature, hash_func=hash_function)
    return hash_function(tx_hash, signature_hash)


async def calculate_patricia_root(
    leaves: Iterable[int], height: int, ffc: FactFetchingContext
) -> int:
    """
    Calculates and returns the patricia root whose (leftmost) leaves are given.
    """
    empty_tree = await PatriciaTree.empty_tree(
        ffc=ffc, height=height, leaf_fact=SimpleLeafFact.empty()
    )
    modifications = [(index, SimpleLeafFact(value=value)) for index, value in enumerate(leaves)]
    final_tree = await empty_tree.update(ffc=ffc, modifications=modifications)

    return from_bytes(final_tree.root)


def calculate_event_hash(
    from_address: int,
    keys: List[int],
    data: List[int],
    hash_function: Callable[[int, int], int] = pedersen_hash,
) -> int:
    """
    Calculates and returns the hash of an event, given its separate fields.
    I.e., H(from_address, H(keys), H(data)), where each hash chain computation begins
    with 0 as initialization and ends with its length appended.
    """
    keys_hash = compute_hash_on_elements(data=keys, hash_func=hash_function)
    data_hash = compute_hash_on_elements(data=data, hash_func=hash_function)
    return compute_hash_on_elements(
        data=[from_address, keys_hash, data_hash], hash_func=hash_function
    )
