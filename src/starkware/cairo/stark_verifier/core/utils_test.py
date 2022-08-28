import os

import pytest

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.lang.builtins.bitwise.instance_def import CELLS_PER_BITWISE
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.cairo.lang.compiler.scoped_name import ScopedName

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "utils.cairo")


@pytest.fixture(scope="session")
def program():
    return compile_cairo_files(
        [CAIRO_FILE],
        prime=DEFAULT_PRIME,
        debug_info=True,
        main_scope=ScopedName.from_string("starkware.cairo.stark_verifier.core.utils"),
    )


@pytest.mark.parametrize("num", [0, 1, 2**64 - 1, 0x123456789ABCDEF0])
def test_bit_reverse_u64(program, num):
    expected_res = int(bin(num)[2:].zfill(64)[::-1], 2)
    runner = CairoFunctionRunner(program, layout="small")
    runner.run(
        "bit_reverse_u64",
        bitwise_ptr=runner.bitwise_builtin.base,
        num=num,
    )
    (bitwise_ptr, res) = runner.get_return_values(2)
    assert bitwise_ptr == runner.bitwise_builtin.base + 6 * CELLS_PER_BITWISE
    assert hex(res) == hex(expected_res)
