from eth_hash.auto import keccak

from starkware.cairo.lang.vm.crypto import pedersen_hash

MASK_250 = 2 ** 250 - 1

# MAX_STORAGE_ITEM_SIZE and ADDR_BOUND must be consistent with the corresponding constant in
# starkware/starknet/core/storage/storage.cairo.
MAX_STORAGE_ITEM_SIZE = 256
ADDR_BOUND = 2 ** 251 - MAX_STORAGE_ITEM_SIZE

# OS context offset.
SYSCALL_PTR_OFFSET = 0
STORAGE_PTR_OFFSET = 1


def starknet_keccak(data: bytes) -> int:
    """
    A variant of eth-keccak that computes a value that fits in a StarkNet field element.
    """

    return int.from_bytes(keccak(data), "big") & MASK_250


def get_selector_from_name(func_name: str) -> int:
    return starknet_keccak(data=func_name.encode("ascii"))


def get_storage_var_address(var_name: str, *args) -> int:
    """
    Returns the storage address of a StarkNet storage variable given its name and arguments.
    """
    res = starknet_keccak(var_name.encode("utf8"))

    for arg in args:
        assert isinstance(arg, int), f"Expected arguments to be integers. Found: {arg}."
        res = pedersen_hash(res, arg)

    return res % ADDR_BOUND
