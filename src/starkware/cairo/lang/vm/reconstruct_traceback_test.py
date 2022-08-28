import pytest

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo
from starkware.cairo.lang.vm.cairo_runner import get_main_runner
from starkware.cairo.lang.vm.reconstruct_traceback import reconstruct_traceback
from starkware.cairo.lang.vm.vm_exceptions import VmException


def test_reconstruct_traceback():
    code = """
func bar() {
    assert 0 = 1;
    return ();
}

func foo() {
    bar();
    return ();
}

func main() {
    foo();
    return ();
}
"""
    codes = [(code, "filename")]
    program_with_debug_info = compile_cairo(code=codes, prime=DEFAULT_PRIME, debug_info=True)
    program_without_debug_info = compile_cairo(code=codes, prime=DEFAULT_PRIME, debug_info=False)

    with pytest.raises(VmException) as exc:
        get_main_runner(program=program_without_debug_info, hint_locals={}, layout="plain")

    exception_str = str(exc.value)

    # The exception before calling reconstruct_traceback().
    assert (
        exception_str
        == """\
Error at pc=0:2:
An ASSERT_EQ instruction failed: 1 != 0.
Cairo traceback (most recent call last):
Unknown location (pc=0:8)
Unknown location (pc=0:5)\
"""
    )

    res = reconstruct_traceback(program=program_with_debug_info, traceback_txt=exception_str)
    # The exception after calling reconstruct_traceback().
    assert (
        res
        == """\
filename:3:5: Error at pc=0:2:
    assert 0 = 1;
    ^***********^
An ASSERT_EQ instruction failed: 1 != 0.
Cairo traceback (most recent call last):
filename:13:5
    foo();
    ^***^
filename:8:5
    bar();
    ^***^\
"""
    )
