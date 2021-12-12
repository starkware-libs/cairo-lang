from typing import List

from starkware.cairo.common.math_utils import as_int

SECP_P = 2 ** 256 - 2 ** 32 - 2 ** 9 - 2 ** 8 - 2 ** 7 - 2 ** 6 - 2 ** 4 - 1


def split(num: int) -> List[int]:
    """
    Takes a 256-bit integer and returns its canonical representation as:
        d0 + BASE * d1 + BASE**2 * d2,
    where BASE = 2**86.
    """
    BASE = 2 ** 86
    a = []
    for _ in range(3):
        num, residue = divmod(num, BASE)
        a.append(residue)
    assert num == 0
    return a


def pack(z, prime):
    """
    Takes a BigInt3 struct which represents a triple of limbs (d0, d1, d2) of field elements are
    reconstruct the 256-bit integer (see split()).
    Note that the limbs do not have to be in the range [0, BASE).
    prime should be the Cairo field, and it is used to handle negative values of the limbs.
    """
    limbs = z.d0, z.d1, z.d2
    return sum(as_int(limb, prime) * 2 ** (86 * i) for i, limb in enumerate(limbs))
