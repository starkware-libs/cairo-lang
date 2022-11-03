import os

import pytest

from starkware.cairo.common.test_utils import create_memory_struct
from starkware.cairo.lang.builtins.range_check.range_check_builtin_runner import (
    RangeCheckBuiltinRunner,
)
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.instances import small_instance
from starkware.cairo.lang.vm.cairo_runner import CairoRunner
from starkware.cairo.lang.vm.vm_exceptions import VmException

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "validate_builtins.cairo")


@pytest.mark.parametrize(
    "old_builtins, new_builtins, builtin_sizes, expect_throw",
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
def test_validate_builtins(old_builtins, new_builtins, builtin_sizes, expect_throw):
    """
    Tests the inner_validate_builtins_usage Cairo function: calls the function with different
    builtins usage and checks that the used builtins list was filled correctly.
    """
    # Setup runner.
    runner = CairoRunner.from_file(CAIRO_FILE, DEFAULT_PRIME)
    assert len(runner.program.hints) == 0, "Expecting validator to have no hints."

    range_check_builtin = RangeCheckBuiltinRunner(
        included=True,
        ratio=None,
        inner_rc_bound=2**16,
        n_parts=small_instance.builtins["range_check"].n_parts,
    )
    runner.builtin_runners["range_check_builtin"] = range_check_builtin
    runner.initialize_segments()

    # Setup function.
    old_builtins_ptr = create_memory_struct(runner, old_builtins)
    new_builtins_ptr = create_memory_struct(runner, new_builtins)
    builtins_sizes = create_memory_struct(runner, builtin_sizes)
    args = [
        range_check_builtin.base,
        old_builtins_ptr,
        new_builtins_ptr,
        builtins_sizes,
        len(builtin_sizes),
    ]
    end = runner.initialize_function_entrypoint("validate_builtins", args)
    # Setup context.
    runner.initialize_vm(hint_locals={})

    if expect_throw:
        with pytest.raises(VmException, match="is out of range"):
            runner.run_until_pc(end)
    else:
        runner.run_until_pc(end)
        runner.end_run()
