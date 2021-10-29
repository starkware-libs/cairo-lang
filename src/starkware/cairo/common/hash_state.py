import functools

from starkware.cairo.lang.vm.crypto import pedersen_hash


def compute_hash_on_elements(data, hash_func=pedersen_hash):
    """
    Computes a hash chain over the data, in the following order:
        h(h(h(n, data[0]), data[1]), ...), data[n-1]).

    The hash is initialized with the data length.
    The length is used in order to avoid collisions of the following kind:
    H([x,y,z]) = h(h(x,y),z) = H([w, z]) where w = h(x,y).
    """
    return functools.reduce(lambda x, y: hash_func(x, y), [*data], len(data))
