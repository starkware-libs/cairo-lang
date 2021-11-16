# Implementation of Keccak-f[u*u*w], as defined in https://en.wikipedia.org/wiki/SHA-3.

import operator
from functools import reduce
from typing import Iterable, List, Optional

from starkware.python.math_utils import div_ceil
from starkware.python.utils import from_bytes, to_bytes


def rot_left(x, n, w):
    """
    Rotates a w-bit number n bits to the left.
    """
    return ((x << n) & (2 ** w - 1)) | (x >> (w - n))


def precompute_offsets(w: int, u: int, alpha: int, beta: int) -> List[List[int]]:
    x, y = 1, 0
    xy_pairs = set()
    offset = 0
    result = [[0] * u for _ in range(u)]
    for t in range(1, u ** 2):
        xy_pairs.add((x, y))
        offset = (offset + t) % w
        result[x][y] = offset
        # The official definition is (alpha, beta) = (3, 2) for u = 5. Any other u has no official
        # definition, but the iteration must go over each (x, y) != (0, 0) pair exactly once.
        x, y = y, (beta * x + alpha * y) % u
    assert len(xy_pairs) == u ** 2 - 1
    return result


def precompute_rc(ell: int, rounds: Optional[int] = None) -> Iterable[int]:
    x = 1
    if rounds is None:
        rounds = 12 + 2 * ell
    for _ in range(rounds):
        rc = 0
        for m in range(ell + 1):
            rc += (x & 1) << (2 ** m - 1)
            x <<= 1
            x ^= 0x171 * (x >> 8)
        yield rc


def keccak_round(
    a: List[List[int]], offsets: List[List[int]], rc: int, w: int, u: int, alpha: int, beta: int
) -> List[List[int]]:
    """
    Performs one keccak round on a matrix of uxu w-bit integers.
    rc is the round constant.
    """
    c = [reduce(operator.xor, a[x]) for x in range(u)]
    d = [c[(x - 1) % u] ^ rot_left(c[(x + 1) % u], 1, w) for x in range(u)]
    a = [[a[x][y] ^ d[x] for y in range(u)] for x in range(u)]
    b = [a[x][:] for x in range(u)]
    for x in range(u):
        for y in range(u):
            b[y][(beta * x + alpha * y) % u] = rot_left(a[x][y], offsets[x][y], w)
    a = [[b[x][y] ^ ((~b[(x + 1) % u][y]) & b[(x + 2) % u][y]) for y in range(u)] for x in range(u)]
    a[0][0] ^= rc
    return a


def keccak_func(
    values: List[int],
    ell: int = 6,
    u: int = 5,
    alpha: int = 3,
    beta: int = 2,
    rounds: Optional[int] = None,
) -> List[int]:
    """
    Computes the keccak block permutation on u**2 2**ell-bit integers.
    """
    # Reshape values to a matrix.
    value_matrix = [[values[u * y + x] for y in range(u)] for x in range(u)]
    w = 2 ** ell
    offsets = precompute_offsets(w, u, alpha, beta)
    for rc in precompute_rc(ell, rounds):
        value_matrix = keccak_round(
            a=value_matrix, offsets=offsets, rc=rc, w=w, u=u, alpha=alpha, beta=beta
        )
    # Reshape values to a flat list.
    values = [value_matrix[y][x] for x in range(u) for y in range(u)]

    return values


def keccak_f(
    message: bytes,
    ell: int = 6,
    u: int = 5,
    alpha: int = 3,
    beta: int = 2,
    rounds: Optional[int] = None,
) -> bytes:
    """
    Computes the keccak block permutation on a u**2*2**ell-bit message (pads with zeros).
    """
    w = 2 ** ell
    assert len(message) <= div_ceil(u * u * w, 8)
    as_bigint = from_bytes(message, byte_order="little")
    assert as_bigint < 2 ** (u * u * w)
    as_integers = [(as_bigint >> (i * w)) & (2 ** w - 1) for i in range(u ** 2)]
    result = keccak_func(values=as_integers, ell=ell, u=u, alpha=alpha, beta=beta, rounds=rounds)
    return to_bytes(
        sum(x << (i * w) for i, x in enumerate(result)),
        length=(u ** 2 * w + 7) // 8,
        byte_order="little",
    )
