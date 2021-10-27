import os

import pytest

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.cairo.lang.compiler.program import Program
from starkware.starknet.public.abi import ADDR_BOUND, MAX_STORAGE_ITEM_SIZE

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "storage.cairo")


@pytest.fixture
def program() -> Program:
    return compile_cairo_files([CAIRO_FILE], prime=DEFAULT_PRIME)


@pytest.fixture
def runner(program: Program) -> CairoFunctionRunner:
    return CairoFunctionRunner(program)


def test_constants(program: Program):
    assert program.get_const("ADDR_BOUND") % DEFAULT_PRIME == ADDR_BOUND
    assert program.get_const("MAX_STORAGE_ITEM_SIZE") == MAX_STORAGE_ITEM_SIZE


@pytest.mark.parametrize(
    "value",
    [
        0,
        2 ** 250 - 1,
        2 ** 250,
        2 ** 250 + 1,
        ADDR_BOUND - 1,
        ADDR_BOUND,
        ADDR_BOUND + 1,
        2 ** 251 - 1,
        2 ** 251,
        2 ** 251 + 1,
        DEFAULT_PRIME - 1,
    ],
)
def test_normalize_address(runner: CairoFunctionRunner, value):
    runner.run("normalize_address", range_check_ptr=runner.range_check_builtin.base, addr=value)
    range_check_ptr_end, result = runner.get_return_values(2)
    assert range_check_ptr_end.segment_index == runner.range_check_builtin.base.segment_index

    assert result == value % ADDR_BOUND
