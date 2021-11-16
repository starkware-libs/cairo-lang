from typing import Callable, List, Sequence

from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.cairo.lang.vm.crypto import get_async_hash_function, pedersen_hash
from starkware.python.utils import from_bytes, safe_zip
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starkware_utils.commitment_tree.patricia_tree.patricia_tree import PatriciaTree
from starkware.storage.dict_storage import DictStorage
from starkware.storage.storage import FactFetchingContext
from starkware.storage.storage_utils import LeafFact


async def calculate_block_hash(
    general_config: StarknetGeneralConfig,
    parent_hash: int,
    block_number: int,
    global_state_root: bytes,
    tx_hashes: Sequence[int],
    tx_signatures: Sequence[List[int]],
    hash_function: Callable[[int, int], int] = pedersen_hash,
) -> int:
    """
    Calculates the block hash in the StarkNet network.
    The block hash is a hash chain of the following information:
        1. Parent block hash.
        2. Block number.
        3. New global state root.
        4. Sequencer address.
        5. Creation time (not implemented yet).
        6. Number of transactions.
        7. A commitment on the transactions.
        8. Number of events.
        9. A commitment on the events (not implemented yet).
        10. Protocol version (not implemented yet).
        11. Extra data (not implemented yet).
        12. The network's chain ID (does not appear in spec doc).
    Each hash chain computation begins with 0 as initialization and ends with its length appended.
    The length is appended in order to avoid collisions of the following kind:
    H([x,y,z]) = h(h(x,y),z) = H([w, z]) where w = h(x,y).
    """
    ffc = FactFetchingContext(
        storage=DictStorage(), hash_func=get_async_hash_function(hash_function=hash_function)
    )

    tx_final_hashes = [
        calculate_tx_hash_with_signature(
            tx_hash=tx_hash, tx_signature=tx_signature, hash_function=hash_function
        )
        for (tx_hash, tx_signature) in safe_zip(tx_hashes, tx_signatures)
    ]

    tx_commitment = await calculate_patricia_root(
        leaves=tx_final_hashes,
        height=general_config.tx_commitment_tree_height,
        ffc=ffc,
    )

    return compute_hash_on_elements(
        data=[
            block_number,
            from_bytes(global_state_root),
            general_config.sequencer_address,  # Sequencer address.
            0,  # Creation time.
            len(tx_hashes),  # Number of transactions.
            tx_commitment,  # Transaction commitment.
            0,  # Number of events.
            0,  # Event commitment.
            0,  # Protocol version.
            0,  # Extra data.
            general_config.chain_id.value,
            # Must be last for future optimization; that way we can separate the calculation of all
            # the other fields, which depend on the block itself, from the parent block hash,
            # as the hash is calculated in the following order: H([x,y,z]) = h(h(x,y),z).
            parent_hash,
        ],
        hash_func=hash_function,
    )


def calculate_tx_hash_with_signature(
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
    leaves: Sequence[int], height: int, ffc: FactFetchingContext
) -> int:
    """
    Calculates and return the patricia root whose (leftmost) leaves are given.
    """
    empty_tree = await PatriciaTree.empty_tree(ffc=ffc, height=height, leaf_fact=LeafFact.empty())
    modifications = [(index, LeafFact(value=value)) for index, value in enumerate(leaves)]
    final_tree = await empty_tree.update(ffc=ffc, modifications=modifications)

    return from_bytes(final_tree.root)
