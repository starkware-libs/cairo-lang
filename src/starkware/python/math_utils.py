import math

import sympy
from sympy.core.numbers import igcdex


def safe_div(x: int, y: int):
    """
    Computes x / y and fails if x is not divisible by y.
    """
    assert isinstance(x, int) and isinstance(y, int)
    assert y != 0
    assert x % y == 0, f'{x} is not divisible by {y}.'
    return x // y


def div_ceil(x, y):
    assert isinstance(x, int) and isinstance(y, int)
    return -((-x) // y)


def div_mod(n, m, p):
    """
    Finds a nonnegative integer x < p such that (m * x) % p == n.
    """
    a, b, c = igcdex(m, p)
    assert c == 1
    return (n * a) % p


def next_power_of_2(x: int):
    """
    Returns the smallest power of two which is >= x.
    """
    assert isinstance(x, int) and x > 0
    res = 2 ** (x - 1).bit_length()
    assert x <= res < 2 * x, f'{x}, {res}'
    return res


def is_power_of_2(x):
    return isinstance(x, int) and x > 0 and x & (x - 1) == 0


def is_quad_residue(n, p):
    """
    Returns True if n is a quadratic residue mod p.
    """
    return sympy.ntheory.residue_ntheory.is_quad_residue(n, p)


def safe_log2(x: int):
    """
    Computes log2(x) where x is a power of 2. This function fails if x is not a power of 2.
    """
    assert x > 0
    res = int(math.log(x, 2))
    assert 2 ** res == x
    return res


def sqrt(n, p):
    """
    Finds the minimum positive integer m such that (m*m) % p == n.
    """
    return min(sympy.ntheory.residue_ntheory.sqrt_mod(n, p, all_roots=True))
