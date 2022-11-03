import itertools
import os
import random
from typing import List

import pytest

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.structs import CairoStructFactory, CairoStructProxy
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.stark_verifier.core.fri.test_utils import (
    apply_fri_steps_on_coset,
    evaluate_polynomial_on_coset,
)
from starkware.python.math_utils import div_mod, safe_div

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "fri_layer.cairo")

MAX_COSET_GEN = pow(3, safe_div(DEFAULT_PRIME - 1, 16), DEFAULT_PRIME)


def fri_group() -> List[int]:
    """
    Returns the elements of the multiplicative subgroup of size 16 in bit-reversed order.
    """
    result = []
    for i in [0, 4, 2, 6, 1, 5, 3, 7]:
        val = pow(MAX_COSET_GEN, i, DEFAULT_PRIME)
        result.append(val)
        result.append(DEFAULT_PRIME - val)
    return result


@pytest.fixture(scope="session")
def program() -> Program:
    return compile_cairo_files([CAIRO_FILE], prime=DEFAULT_PRIME, debug_info=True)


@pytest.fixture
def structs(program):
    return CairoStructFactory.from_program(
        program,
    ).structs


@pytest.mark.parametrize("fri_step", range(1, 5))
@pytest.mark.parametrize("num_queries", range(0, 5))
def test_fri(program: Program, structs: CairoStructProxy, fri_step: int, num_queries: int):
    layer_size_log2 = 5
    layer_size = 2**layer_size_log2

    # Choose a random polynomial of degree < 256: sum(poly[i] * x^i).
    poly = [random.randrange(DEFAULT_PRIME) for i in range(256)]

    # Choose random eval_point and random x.
    eval_point = random.randrange(DEFAULT_PRIME)
    rand_x = random.randrange(DEFAULT_PRIME)

    # Compute the values of the polynomial on the coset.
    coset_gen = pow(3, safe_div(DEFAULT_PRIME - 1, layer_size), DEFAULT_PRIME)
    coset_x_values, coset_values = evaluate_polynomial_on_coset(
        poly=poly, x=rand_x, coset_gen=coset_gen, coset_size_log2=layer_size_log2
    )

    # Choose random points in the coset that will be used as queries for the layer.
    indices = sorted(random.sample(range(layer_size), num_queries))
    coset_size = 2**fri_step
    queried_cosets = sorted(set(i // coset_size for i in indices))

    # Prepare inputs and expected outputs.
    queries = []
    for i in indices:
        queries.append(
            structs.FriLayerQuery(
                index=i,
                y_value=coset_values[i],
                x_inv_value=div_mod(1, coset_x_values[i], DEFAULT_PRIME),
            )
        )

    sibling_witness = []
    expected_verify_indices = []
    expected_verify_y_values = []
    for coset_index in sorted(queried_cosets):
        expected_verify_indices.append(coset_index)
        coset_start_index = coset_index * coset_size
        for i in range(coset_start_index, coset_start_index + coset_size):
            expected_verify_y_values.append(coset_values[i])
            if i not in indices:
                sibling_witness.append(coset_values[i])

    # Apply fri_step layers of FRI to evaluate the results on y=x^coset_size for each queried
    # coset.
    expected_next_queries = []
    for coset_index in sorted(queried_cosets):
        coset_start_index = coset_index * coset_size
        x = coset_x_values[coset_start_index]
        expected_val = apply_fri_steps_on_coset(poly, x, coset_size, eval_point)
        # The fri_formula function returns the result multiplied by coset_size for
        # efficiency.
        expected_val = (expected_val * coset_size) % DEFAULT_PRIME
        expected_next_queries.append(
            structs.FriLayerQuery(
                index=coset_index,
                y_value=expected_val,
                x_inv_value=div_mod(1, pow(x, coset_size, DEFAULT_PRIME), DEFAULT_PRIME),
            )
        )

    runner = CairoFunctionRunner(program)
    next_queries = runner.segments.add()
    verify_indices = runner.segments.add()
    verify_y_values = runner.segments.add()

    runner.run(
        f"compute_next_layer",
        range_check_ptr=runner.range_check_builtin.base,
        n_queries=len(queries),
        queries=list(itertools.chain(*queries)),
        sibling_witness=sibling_witness,
        next_queries=next_queries,
        verify_indices=verify_indices,
        verify_y_values=verify_y_values,
        params=structs.FriLayerComputationParams(
            coset_size=coset_size,
            fri_group=fri_group(),
            eval_point=eval_point,
        ),
    )

    (
        res_range_check_ptr,
        res_n_queries,
        res_queries,
        res_sibling_witness,
        res_next_queries,
        res_verify_indices,
        res_verify_y_values,
    ) = runner.get_return_values(7)

    assert res_range_check_ptr.segment_index == runner.range_check_builtin.base.segment_index
    assert res_n_queries == 0
    assert res_sibling_witness.offset == len(sibling_witness)
    assert res_queries.offset == len(queries) * structs.FriLayerQuery.size
    assert (
        res_next_queries == next_queries + len(expected_next_queries) * structs.FriLayerQuery.size
    )
    for i, expected_next_query in enumerate(expected_next_queries):
        res_next_query = structs.FriLayerQuery.from_ptr(
            memory=runner.memory, addr=next_queries + i * structs.FriLayerQuery.size
        )
        assert res_next_query == expected_next_query
    assert expected_verify_indices == runner.memory.get_range(
        verify_indices, res_verify_indices - verify_indices
    )
    assert expected_verify_y_values == runner.memory.get_range(
        verify_y_values, res_verify_y_values - verify_y_values
    )
