import itertools
import os
import random

import pytest

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.structs import CairoStructFactory, CairoStructProxy
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.vm.vm_exceptions import VmException
from starkware.python.math_utils import div_mod, horner_eval
from starkware.python.test_utils import maybe_raises

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "fri.cairo")


@pytest.fixture(scope="session")
def program() -> Program:
    return compile_cairo_files([CAIRO_FILE], prime=DEFAULT_PRIME, debug_info=True)


@pytest.fixture
def structs(program):
    return CairoStructFactory.from_program(program).structs


@pytest.mark.parametrize(
    "success_verification",
    [True, False],
)
def test_last_layer_verification(
    program: Program, structs: CairoStructProxy, success_verification: bool
):
    n_points = 8

    # Choose a random polynomial of degree < 256: sum(poly[i] * x^i).
    poly = [random.randrange(DEFAULT_PRIME) for _ in range(256)]

    # Choose random points and evaluate the polynomial on each of the points.
    points = [random.randrange(DEFAULT_PRIME) for _ in range(n_points)]
    values = [horner_eval(poly, x, DEFAULT_PRIME) for x in points]

    if not success_verification:
        # Set one of the values/points to a wrong value.
        index = random.randrange(n_points)
        if random.randrange(2) == 0:
            values[index] = values[index] - 1
        else:
            points[index] = points[index] - 1

    queries = [
        structs.FriLayerQuery(
            index=0,  # Irrelevant.
            y_value=values[i],
            x_inv_value=div_mod(1, points[i], DEFAULT_PRIME),
        )
        for i in range(len(points))
    ]
    runner = CairoFunctionRunner(program)
    with maybe_raises(
        VmException, None if success_verification else "ASSERT_EQ instruction failed"
    ):
        runner.run(
            f"verify_last_layer",
            n_queries=len(values),
            queries=list(itertools.chain(*queries)),
            n_coefficients=len(poly),
            coefficients=poly,
        )
