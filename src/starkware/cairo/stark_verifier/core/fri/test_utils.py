from typing import List, Tuple

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.python.math_utils import horner_eval


def evaluate_polynomial_on_coset(
    poly: List[int], x: int, coset_gen: int, coset_size_log2: int
) -> Tuple[List[int], List[int]]:
    """
    Evaluates the given polynomial on the coset x*<coset_gen> in bit reversed order.
    Returns 2 lists: a list of the x values in the coset, and a list of the corresponding poly(x)
    values.
    """
    coset_size = 2**coset_size_log2
    coset_x_vals = []
    coset_poly_x_vals = []
    for i in range(coset_size):
        # The input should be given in bit-reversed order.
        # Convert i to its binary representation and reverse its bits.
        rev_i = int(bin(i)[2:].rjust(coset_size_log2, "0")[::-1], 2)
        x1 = x * pow(coset_gen, rev_i, DEFAULT_PRIME)
        value = horner_eval(poly, x1, DEFAULT_PRIME)
        coset_x_vals.append(x1)
        coset_poly_x_vals.append(value)

    return (coset_x_vals, coset_poly_x_vals)


def apply_fri_steps_on_coset(poly: List[int], x: int, coset_size: int, eval_point: int) -> int:
    """
    Applies log2(coset_szie) layers of FRI and evaluates the result on y=x^coset_size.
    """
    result = 0
    y = pow(x, coset_size, DEFAULT_PRIME)
    for i in range(coset_size):
        # Take the coefficients of x^(coset_size * j + i).
        coefs = poly[i::coset_size]
        # Substitute x^coset_size in the resulting polynomial.
        eval_x = horner_eval(coefs, y, DEFAULT_PRIME)
        # Multiply by eval_point^i and sum the results.
        result += eval_x * pow(eval_point, i, DEFAULT_PRIME)

    return result
