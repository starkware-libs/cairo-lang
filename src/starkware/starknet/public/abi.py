from eth_hash.auto import keccak

from starkware.cairo.lang.vm.crypto import pedersen_hash

MASK_250 = 2 ** 250 - 1


def starknet_keccak(data: bytes) -> int:
    """
    A variant of eth-keccak that computes a value that fits in a StarkNet field element.
    """

    return int.from_bytes(keccak(data), 'big') & MASK_250


def get_storage_var_address(var_name: str, *args) -> int:
    """
    Returns the storage address of a StarkNet storage variable given its name and arguments.
    """
    res = starknet_keccak(var_name.encode('utf8'))

    for arg in args:
        assert isinstance(arg, int), f'Expected arguments to be integers. Found: {arg}.'
        res = pedersen_hash(res, arg)

    return res
