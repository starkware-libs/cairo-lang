import os

import pytest

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.lang.builtins.range_check.range_check_builtin_runner import (
    RangeCheckBuiltinRunner,
)
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.instances import small_instance
from starkware.cairo.lang.vm.vm_exceptions import VmException
from starkware.python.test_utils import maybe_raises

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "validate_builtins.cairo")


@pytest.mark.parametrize(
    "old_builtins, new_builtins, builtin_instance_sizes, expect_throw",
    [
        ([10, 10], [10, 10], [1, 1], False),
        # Second builtin usage is negative.
        ([10, 10], [10, 9], [1, 1], True),
        ([0, 0], [1, 3], [1, 3], False),
        # Second builtin usage is not a multiple of the builtin_size.
        ([0, 0], [1, 2], [1, 3], True),
        ([5, 5], [9, 26], [2, 7], False),
    ],
)
def test_validate_builtins(old_builtins, new_builtins, builtin_instance_sizes, expect_throw):
    """
    Tests the inner_validate_builtins_usage Cairo function: calls the function with different
    builtins usage and checks that the used builtins list was filled correctly.
    """
    # Setup runner.
    runner = CairoFunctionRunner.from_file(CAIRO_FILE, DEFAULT_PRIME)
    assert len(runner.program.hints) == 0, "Expecting validator to have no hints."

    range_check_builtin = RangeCheckBuiltinRunner(
        name="range_check",
        included=True,
        ratio=None,
        ratio_den=1,
        inner_rc_bound=2**16,
        n_parts=small_instance.builtins["range_check"].n_parts,
    )
    runner.builtin_runners["range_check_builtin"] = range_check_builtin
    runner.initialize_segments()

    with maybe_raises(
        expected_exception=VmException,
        error_message="is out of range" if expect_throw else None,
    ):
        runner.run(
            "validate_builtins",
            range_check_ptr=range_check_builtin.base,
            prev_builtin_ptrs=old_builtins,
            new_builtin_ptrs=new_builtins,
            builtin_instance_sizes=builtin_instance_sizes,
            n_builtins=len(builtin_instance_sizes),
        )
