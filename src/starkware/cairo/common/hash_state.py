import functools

from starkware.cairo.lang.vm.crypto import pedersen_hash


def compute_hash_on_elements(data, hash_func=pedersen_hash):
    """
    Computes a hash chain over the data, in the following order:
        h(h(h(h(0, data[0]), data[1]), ...), data[n-1]), n).

    The hash is initialized with 0 and ends with the data length appended.
    The length is appended in order to avoid collisions of the following kind:
    H([x,y,z]) = h(h(x,y),z) = H([w, z]) where w = h(x,y).
    """
    return functools.reduce(lambda x, y: hash_func(x, y), [*data, len(data)], 0)
