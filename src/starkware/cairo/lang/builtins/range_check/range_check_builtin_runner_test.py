import pytest

from starkware.cairo.lang.builtins.builtin_runner_test_utils import PRIME, compile_and_run
from starkware.cairo.lang.vm.vm_exceptions import VmException


def test_validation_rules():
    CODE_FORMAT = """
%builtins range_check

func main(range_check_ptr: felt) -> (range_check_ptr: felt) {{
    assert [range_check_ptr] = {value};
    return (range_check_ptr=range_check_ptr + 1);
}}
"""

    # Test valid values.
    compile_and_run(CODE_FORMAT.format(value=0))
    compile_and_run(CODE_FORMAT.format(value=1))

    with pytest.raises(
        VmException,
        match=f"Value {PRIME - 1}, in range check builtin 0, is out of range "
        r"\[0, {bound}\)".format(bound=2**128),
    ):
        compile_and_run(CODE_FORMAT.format(value=-1))

    with pytest.raises(
        VmException,
        match=f"Range-check builtin: Expected value at address 2:0 to be an integer. Got: 2:0",
    ):
        compile_and_run(CODE_FORMAT.format(value="range_check_ptr"))
