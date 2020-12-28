from functools import reduce

from starkware.cairo.lang.vm.crypto import pedersen_hash


def compute_hash_chain(data, hash_func=pedersen_hash):
    """
    Computes a hash chain over the data, in the following order:
        h(data[0], h(data[1], h(..., h(data[n-2], data[n-1])))).
    """

    return reduce(lambda x, y: hash_func(y, x), data[::-1])
