import os
import random

import pytest

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.stark_verifier.core.fri.test_utils import (
    apply_fri_steps_on_coset,
    evaluate_polynomial_on_coset,
)
from starkware.python.math_utils import safe_div

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "fri_formula.cairo")


@pytest.fixture(scope="session")
def program() -> Program:
    return compile_cairo_files([CAIRO_FILE], prime=DEFAULT_PRIME, debug_info=True)


def test_omega(program: Program):
    assert (program.get_const("OMEGA_2") + 1) % DEFAULT_PRIME == 0


@pytest.mark.parametrize("fri_step", range(1, 5))
def test_fri(program: Program, fri_step: int):
    # Choose a random polynomial of degree < 256: sum(poly[i] * x^i).
    poly = [random.randrange(DEFAULT_PRIME) for i in range(256)]

    # Choose random eval_point and random x.
    eval_point = random.randrange(DEFAULT_PRIME)
    x = random.randrange(DEFAULT_PRIME)

    # Compute the values of the polynomial on the coset.
    coset_size = 2**fri_step
    coset_gen = pow(3, safe_div(DEFAULT_PRIME - 1, coset_size), DEFAULT_PRIME)
    _, coset_values = evaluate_polynomial_on_coset(
        poly=poly, x=x, coset_gen=coset_gen, coset_size_log2=fri_step
    )

    # Apply fri_step layers of FRI and evaluate the result on y=x^coset_size.
    expected_res = apply_fri_steps_on_coset(
        poly=poly, x=x, coset_size=coset_size, eval_point=eval_point
    )

    # The fri_formula function returns the result multiplied by coset_size for efficiency.
    expected_res = (expected_res * coset_size) % DEFAULT_PRIME

    runner = CairoFunctionRunner(program)
    x_inv = pow(x, DEFAULT_PRIME - 2, DEFAULT_PRIME)
    runner.run(f"fri_formula", coset_values, eval_point, x_inv, coset_size)
    (res,) = runner.get_return_values(1)
    print(f"fri_formula{coset_size} took {runner.vm.current_step} steps.")

    assert res == expected_res
