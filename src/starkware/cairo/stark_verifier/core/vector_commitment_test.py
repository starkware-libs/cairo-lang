import itertools
import json
import os

import pytest

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.structs import CairoStructFactory
from starkware.cairo.common.validate_utils import validate_builtin_usage
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.cairo.lang.compiler.scoped_name import ScopedName

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "vector_commitment.cairo")
TEST_DATA_FILE = os.path.join(os.path.dirname(__file__), "merkle_test_data.json")


@pytest.fixture(scope="session")
def program():
    return compile_cairo_files(
        [CAIRO_FILE],
        prime=DEFAULT_PRIME,
        debug_info=True,
        main_scope=ScopedName.from_string("starkware.cairo.stark_verifier.core.vector_commitment"),
    )


@pytest.fixture
def structs(program):
    return CairoStructFactory.from_program(
        program,
        additional_imports=[
            "starkware.cairo.stark_verifier.core.vector_commitment.VectorUnsentCommitment",
            "starkware.cairo.stark_verifier.core.vector_commitment.VectorCommitment",
            "starkware.cairo.stark_verifier.core.vector_commitment.VectorCommitmentWitness",
            "starkware.cairo.stark_verifier.core.vector_commitment.VectorCommitmentConfig",
        ],
    ).structs


def test_vector_commitment(program, structs):
    with open(
        TEST_DATA_FILE,
        "r",
    ) as fp:
        data = json.load(fp)
    commitment = structs.VectorCommitment(
        config=structs.VectorCommitmentConfig(
            height=data["merkle_height"],
            n_verifier_friendly_commitment_layers=9,
        ),
        commitment_hash=int(data["expected_root"], 16),
    )

    runner = CairoFunctionRunner(program, layout="small")
    query_indices = data["merkle_queue_indices"]
    query_values = [int(query, 16) for query in data["merkle_queue_values"]]
    n_queries = len(query_indices)
    queries = list(
        itertools.chain(
            *[
                runner.segments.gen_typed_args(
                    structs.VectorQuery(
                        index=index - 2 ** data["merkle_height"],
                        value=value,
                    )
                )
                for index, value in zip(query_indices, query_values)
            ]
        )
    )
    blake2s_ptr = runner.segments.add()
    proof_values = [int(proof_val, 16) for proof_val in data["proof"]]
    runner.run(
        "vector_commitment_decommit",
        range_check_ptr=runner.range_check_builtin.base,
        blake2s_ptr=blake2s_ptr,
        pedersen_ptr=runner.pedersen_builtin.base,
        bitwise_ptr=runner.bitwise_builtin.base,
        commitment=commitment,
        n_queries=n_queries,
        queries=queries,
        witness=structs.VectorCommitmentWitness(
            n_authentications=len(data["proof"]),
            authentications=proof_values,
        ),
        n_columns=1,
    )
    (
        res_range_check_ptr,
        res_blake2s_ptr,
        res_pedersen_ptr,
        res_bitwise_ptr,
    ) = runner.get_return_values(4)
    validate_builtin_usage(runner.range_check_builtin, res_range_check_ptr)
    assert res_blake2s_ptr.segment_index == blake2s_ptr.segment_index
    validate_builtin_usage(runner.pedersen_builtin, res_pedersen_ptr)
    validate_builtin_usage(runner.bitwise_builtin, res_bitwise_ptr)
