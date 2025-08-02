###############################################################################
# Copyright 2019 StarkWare Industries Ltd.                                    #
#                                                                             #
# Licensed under the Apache License, Version 2.0 (the "License").             #
# You may not use this file except in compliance with the License.            #
# You may obtain a copy of the License at                                     #
#                                                                             #
# https://www.starkware.co/open-source-license/                               #
#                                                                             #
# Unless required by applicable law or agreed to in writing,                  #
# software distributed under the License is distributed on an "AS IS" BASIS,  #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.    #
# See the License for the specific language governing permissions             #
# and limitations under the License.                                          #
###############################################################################


from typing import Tuple

import mpmath
import sympy

from starkware.python.math_utils import igcdex

# A type that represents a point (x,y) on an elliptic curve.
ECPoint = Tuple[int, int]


def pi_as_string(digits: int) -> str:
    """
    Returns pi as a string of decimal digits without the decimal point ("314...").
    """
    if digits < 0:
        raise ValueError("Negative number of digits")
    mpmath.mp.dps = digits  # Set number of digits.
    return "3" + str(mpmath.mp.pi)[2:]


def is_quad_residue(n: int, p: int) -> bool:
    """
    Returns True if n is a quadratic residue mod p.
    """
    return sympy.is_quad_residue(n, p)


def sqrt_mod(n: int, p: int) -> int:
    """
    Finds the minimum positive integer m such that (m*m) % p == n
    """
    return min(sympy.sqrt_mod(n, p, all_roots=True))


def div_mod(n: int, m: int, p: int) -> int:
    """
    Finds a nonnegative integer 0 <= x < p such that (m * x) % p == n
    """
    a, b, c = igcdex(m, p)
    assert c == 1
    return (n * a) % p


def ec_add(point1: ECPoint, point2: ECPoint, p: int) -> ECPoint:
    """
    Gets two points on an elliptic curve mod p and returns their sum.
    Assumes the points are given in affine form (x, y) and have different x coordinates.
    """
    assert (point1[0] - point2[0]) % p != 0
    m = div_mod(point1[1] - point2[1], point1[0] - point2[0], p)
    x = (m * m - point1[0] - point2[0]) % p
    y = (m * (point1[0] - x) - point1[1]) % p
    return x, y


def ec_neg(point: ECPoint, p: int) -> ECPoint:
    """
    Given a point (x,y) return (x, -y)
    """
    x, y = point
    return (x, (-y) % p)


def ec_double(point: ECPoint, alpha: int, p: int) -> ECPoint:
    """
    Doubles a point on an elliptic curve with the equation y^2 = x^3 + alpha*x + beta mod p.
    Assumes the point is given in affine form (x, y) and has y != 0.
    """
    assert point[1] % p != 0
    m = div_mod(3 * point[0] * point[0] + alpha, 2 * point[1], p)
    x = (m * m - 2 * point[0]) % p
    y = (m * (point[0] - x) - point[1]) % p
    return x, y


def ec_mult(m: int, point: ECPoint, alpha: int, p: int) -> ECPoint:
    """
    Multiplies by m a point on the elliptic curve with equation y^2 = x^3 + alpha*x + beta mod p.
    Assumes the point is given in affine form (x, y) and that 0 < m < order(point).
    """
    if m == 1:
        return point
    if m % 2 == 0:
        return ec_mult(m // 2, ec_double(point, alpha, p), alpha, p)
    return ec_add(ec_mult(m - 1, point, alpha, p), point, p)
