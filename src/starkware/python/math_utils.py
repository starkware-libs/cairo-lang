import math
from typing import Tuple, Union

import sympy
from sympy.core.numbers import igcdex


def safe_div(x: int, y: int):
    """
    Computes x / y and fails if x is not divisible by y.
    """
    assert isinstance(x, int) and isinstance(y, int)
    assert y != 0
    assert x % y == 0, f"{x} is not divisible by {y}."
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
    assert x <= res < 2 * x, f"{x}, {res}"
    return res


def is_power_of_2(x):
    return isinstance(x, int) and x > 0 and x & (x - 1) == 0


def prev_power_of_2(x: int):
    """
    Returns the maximal power of two which is <= x.
    """
    assert isinstance(x, int) and x > 0
    return next_power_of_2(x + 1) // 2


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


def isqrt(n: int) -> int:
    """
    Returns the integer square root of the nonnegative integer n. This is the floor of the exact
    square root of n.
    Unlike math.sqrt(), this function doesn't have rounding error issues.
    """
    assert n >= 0

    # The following algorithm was copied from
    # https://stackoverflow.com/questions/15390807/integer-square-root-in-python.
    x = n
    y = (x + 1) // 2
    while y < x:
        x = y
        y = (x + n // x) // 2
    assert x ** 2 <= n < (x + 1) ** 2
    return x


# Elliptic curve functions.
class EcInfinity:
    pass


EC_INFINITY = EcInfinity()


def line_slope(point1: Tuple[int, int], point2: Tuple[int, int], p: int) -> int:
    """
    Computes the slope of the line connecting the two given EC points over the field GF(p).
    Assumes the points are given in affine form (x, y) and have different x coordinates.
    """
    assert (point1[0] - point2[0]) % p != 0
    return div_mod(point1[1] - point2[1], point1[0] - point2[0], p)


def ec_add(point1: Tuple[int, int], point2: Tuple[int, int], p: int) -> Tuple[int, int]:
    """
    Gets two points on an elliptic curve mod p and returns their sum.
    Assumes the points are given in affine form (x, y) and have different x coordinates.
    """
    m = line_slope(point1=point1, point2=point2, p=p)
    x = (m * m - point1[0] - point2[0]) % p
    y = (m * (point1[0] - x) - point1[1]) % p
    return x, y



def ec_double_slope(point: Tuple[int, int], alpha: int, p: int) -> int:
    """
    Computes the slope of an elliptic curve with the equation y^2 = x^3 + alpha*x + beta mod p, at
    the given point.
    Assumes the point is given in affine form (x, y) and has y != 0.
    """
    assert point[1] % p != 0
    return div_mod(3 * point[0] * point[0] + alpha, 2 * point[1], p)


def ec_double(point: Tuple[int, int], alpha: int, p: int) -> Tuple[int, int]:
    """
    Doubles a point on an elliptic curve with the equation y^2 = x^3 + alpha*x + beta mod p.
    Assumes the point is given in affine form (x, y) and has y != 0.
    """
    m = ec_double_slope(point=point, alpha=alpha, p=p)
    x = (m * m - 2 * point[0]) % p
    y = (m * (point[0] - x) - point[1]) % p
    return x, y


def ec_safe_add(point1, point2, alpha, p):
    """
    Gets two points on an elliptic curve mod p and returns their sum.
    Safe to use always. May get or return the point at infinity, represented as EC_INFINITY.
    """
    if point1 == EC_INFINITY:
        return point2
    if point2 == EC_INFINITY:
        return point1
    x1, y1 = point1[0] % p, point1[1] % p
    x2, y2 = point2[0] % p, point2[1] % p
    if x1 == x2:
        if y1 == (p - y2) % p:
            return EC_INFINITY
        else:
            return ec_double((x1, y1), alpha, p)
    else:
        return ec_add((x1, y1), (x2, y2), p)


def ec_mult(m, point, alpha, p):
    """
    Multiplies by m a point on the elliptic curve with equation y^2 = x^3 + alpha*x + beta mod p.
    Assumes the point is given in affine form (x, y) and that 0 < m < order(point).
    """
    if m == 1:
        return point
    if m % 2 == 0:
        return ec_mult(m // 2, ec_double(point, alpha, p), alpha, p)
    return ec_add(ec_mult(m - 1, point, alpha, p), point, p)


def ec_safe_mult(m: int, point: Tuple[int, int], alpha: int, p: int) -> Union[Tuple[int, int], str]:
    """
    Multiplies by m a point on the elliptic curve with equation y^2 = x^3 + alpha*x + beta mod p.
    Assumes the point is given in affine form (x, y).
    Safe to use always. May get or return the point at infinity, represented as EC_INFINITY.
    """
    if m == 1:
        return point
    if m % 2 == 0:
        return ec_safe_mult(m // 2, ec_safe_add(point, point, alpha, p), alpha, p)
    return ec_safe_add(ec_safe_mult(m - 1, point, alpha, p), point, alpha, p)


def horner_eval(coefs, point, prime):
    """
    Computes the evaluation of a polynomial on the given point in the field GF(prime).
    """
    res = 0
    for coef in coefs[::-1]:
        res = (res * point + coef) % prime
    return res
