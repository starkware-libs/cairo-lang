import os

import pytest

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.validate_utils import validate_builtin_usage
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "channel_test.cairo")


@pytest.fixture(scope="session")
def program():
    return compile_cairo_files([CAIRO_FILE], prime=DEFAULT_PRIME, debug_info=True)


def test_channel(program):
    runner = CairoFunctionRunner(program, layout="small")
    blake2s_ptr = runner.segments.add()
    runner.run(
        "main_test", runner.range_check_builtin.base, runner.bitwise_builtin.base, blake2s_ptr
    )
    res_range_check_ptr, res_bitwise_ptr, res_blake2s_ptr = runner.get_return_values(3)
    validate_builtin_usage(runner.range_check_builtin, res_range_check_ptr)
    validate_builtin_usage(runner.bitwise_builtin, res_bitwise_ptr)
    assert res_blake2s_ptr.segment_index == blake2s_ptr.segment_index
