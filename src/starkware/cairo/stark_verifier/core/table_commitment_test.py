import os

import pytest

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.structs import CairoStructFactory
from starkware.cairo.common.validate_utils import validate_builtin_usage
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.cairo.lang.compiler.scoped_name import ScopedName

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "table_commitment.cairo")


@pytest.fixture(scope="session")
def program():
    return compile_cairo_files(
        [CAIRO_FILE],
        prime=DEFAULT_PRIME,
        debug_info=True,
        main_scope=ScopedName.from_string("starkware.cairo.stark_verifier.core.table_commitment"),
    )


@pytest.fixture
def structs(program):
    return CairoStructFactory.from_program(
        program,
        additional_imports=[
            "starkware.cairo.stark_verifier.core.table_commitment.TableCommitment",
            "starkware.cairo.stark_verifier.core.table_commitment.TableCommitmentConfig",
            "starkware.cairo.stark_verifier.core.table_commitment.TableCommitmentWitness",
            "starkware.cairo.stark_verifier.core.vector_commitment.VectorCommitment",
            "starkware.cairo.stark_verifier.core.vector_commitment.VectorCommitmentConfig",
            "starkware.cairo.stark_verifier.core.vector_commitment.VectorCommitmentWitness",
        ],
    ).structs


def test_table_commitment(program, structs):
    vector_commitment_config = (
        structs.VectorCommitmentConfig(
            height=5,
            n_verifier_friendly_commitment_layers=2,
        ),
    )
    commitment = structs.TableCommitment(
        vector_commitment=structs.VectorCommitment(
            config=structs.VectorCommitmentConfig(
                height=5,
                n_verifier_friendly_commitment_layers=2,
            ),
            commitment_hash=0x77814A8D523E263E544747B743D672CAA538A648BF7B85C7FD0C0F87C63D66D,
        ),
        config=structs.TableCommitmentConfig(
            n_columns=4,
            vector=vector_commitment_config,
        ),
    )

    queries = [1, 4]
    values = [10] * 4 + [20] * 4

    runner = CairoFunctionRunner(program, layout="small")
    blake2s_ptr = runner.segments.add()
    runner.run(
        "table_decommit",
        range_check_ptr=runner.range_check_builtin.base,
        blake2s_ptr=blake2s_ptr,
        pedersen_ptr=runner.pedersen_builtin.base,
        bitwise_ptr=runner.bitwise_builtin.base,
        commitment=commitment,
        n_queries=len(queries),
        queries=queries,
        decommitment=structs.TableDecommitment(
            n_values=len(values),
            values=values,
        ),
        witness=structs.TableCommitmentWitness(
            vector=structs.VectorCommitmentWitness(
                n_authentications=6,
                authentications=[8 * 2**128 + 8] * 6,
            ),
        ),
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
