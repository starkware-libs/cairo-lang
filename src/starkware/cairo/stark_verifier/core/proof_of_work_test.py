import os

import pytest

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.structs import CairoStructFactory
from starkware.cairo.common.validate_utils import validate_builtin_usage
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.vm.vm_exceptions import VmException
from starkware.python.test_utils import maybe_raises

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "proof_of_work.cairo")

# These values were taken from the C++ implementation.
DIGEST = 0x1C5A5F4381DF1F5CD7CA1D48A19D8FF802A71D94169DE38382621FDC5514A10A
NONCE = 0x1683B
N_BITS = 20


@pytest.fixture(scope="session")
def program() -> Program:
    return compile_cairo_files([CAIRO_FILE], prime=DEFAULT_PRIME, debug_info=True)


@pytest.fixture
def structs(program):
    return CairoStructFactory.from_program(
        program, additional_imports=["starkware.cairo.common.uint256.Uint256"]
    ).structs


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "nonce, error_message",
    [
        (NONCE, None),
        (NONCE + 1, "out of range"),
    ],
)
def test_proof_of_work(program: Program, structs, nonce, error_message):
    runner = CairoFunctionRunner(program)
    blake2s_start = runner.segments.add()
    with maybe_raises(expected_exception=VmException, error_message=error_message):
        runner.run(
            "verify_proof_of_work",
            range_check_ptr=runner.range_check_builtin.base,
            blake2s_ptr=blake2s_start,
            bitwise_ptr=runner.bitwise_builtin.base,
            digest=structs.Uint256(low=DIGEST % 2**128, high=DIGEST >> 128),
            n_bits=N_BITS,
            nonce=structs.ChannelSentFelt(value=nonce),
        )
        (range_check_ptr, blake2s_ptr, bitwise_ptr) = runner.get_return_values(3)
        validate_builtin_usage(runner.range_check_builtin, range_check_ptr)
        assert blake2s_ptr.segment_index == blake2s_start.segment_index
        validate_builtin_usage(runner.bitwise_builtin, bitwise_ptr)
