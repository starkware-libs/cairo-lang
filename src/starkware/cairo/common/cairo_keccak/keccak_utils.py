from typing import List

OFFSETS = list(
    zip(
        *[
            [0, 1, 62, 28, 27],
            [36, 44, 6, 55, 20],
            [3, 10, 43, 25, 39],
            [41, 45, 15, 21, 8],
            [18, 2, 61, 56, 14],
        ]
    )
)

ROUND_CONSTANTS = [
    0x0000000000000001,
    0x0000000000008082,
    0x800000000000808A,
    0x8000000080008000,
    0x000000000000808B,
    0x0000000080000001,
    0x8000000080008081,
    0x8000000000008009,
    0x000000000000008A,
    0x0000000000000088,
    0x0000000080008009,
    0x000000008000000A,
    0x000000008000808B,
    0x800000000000008B,
    0x8000000000008089,
    0x8000000000008003,
    0x8000000000008002,
    0x8000000000000080,
    0x000000000000800A,
    0x800000008000000A,
    0x8000000080008081,
    0x8000000000008080,
    0x0000000080000001,
    0x8000000080008008,
]


def rot_left(x, n):
    """
    Rotates a 64-bit number n bits to the left.
    """
    return ((x << n) & (2 ** 64 - 1)) | (x >> (64 - n))


def keccak_round(a: List[List[int]], rc: int) -> List[List[int]]:
    """
    Performs one keccak round on a matrix of 5x5 64-bit integers.
    rc is the round constant.
    """
    c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
    d = [c[(x - 1) % 5] ^ rot_left(c[(x + 1) % 5], 1) for x in range(5)]
    a = [[a[x][y] ^ d[x] for y in range(5)] for x in range(5)]
    b = [[0] * 5 for _ in range(5)]
    for x in range(5):
        for y in range(5):
            b[y][(2 * x + 3 * y) % 5] = rot_left(a[x][y], OFFSETS[x][y])

    a = [[b[x][y] ^ ((~b[(x + 1) % 5][y]) & b[(x + 2) % 5][y]) for y in range(5)] for x in range(5)]

    a[0][0] ^= rc
    return a


def keccak_func(values: List[int]) -> List[int]:
    """
    Computes the keccak block permutation on 25 64-bit integers.
    """
    # Reshape values to a matrix.
    value_matrix = [[values[5 * y + x] for y in range(5)] for x in range(5)]
    for rc in ROUND_CONSTANTS:
        value_matrix = keccak_round(value_matrix, rc)
    # Reshape values to a flat list.
    values = [value_matrix[y][x] for x in range(5) for y in range(5)]

    return values
