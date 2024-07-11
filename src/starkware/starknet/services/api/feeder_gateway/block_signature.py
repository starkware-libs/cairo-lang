from typing import Callable, List, Optional

from starkware.crypto.signature.signature import ECSignature, sign
from starkware.starknet.services.api.feeder_gateway.response_objects import BlockSignature

HashManyFunction = Callable[[List[int]], int]


def sign_block(private_key: int, block_hash: int) -> ECSignature:
    """
    Signs on the block hash.
    """
    return sign(block_hash, priv_key=private_key)


def get_signature(
    block_hash: int, private_key: int, hash_func: Optional[HashManyFunction] = None
) -> BlockSignature:
    return BlockSignature(
        block_hash=block_hash, signature=sign_block(private_key=private_key, block_hash=block_hash)
    )
