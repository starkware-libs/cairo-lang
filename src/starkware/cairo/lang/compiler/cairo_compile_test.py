import re

import pytest

from starkware.cairo.lang.compiler.cairo_compile import compile_cairo

PRIME = 2 ** 251 + 17 * 2 ** 192 + 1


def test_main_args_match_builtins():
    """
    Checks that an appropriate exception is thrown if the arguments in a given Cairo program's main
    don't match the list of builtins specified by the directive (and their order).
    """
    expected_error_msg = 'Expected main to contain the following arguments (in this order): ' \
        "['output_ptr', 'range_check_ptr']"
    with pytest.raises(AssertionError, match=re.escape(expected_error_msg)):
        compile_cairo(
            code="""
%builtins output range_check

func main(output_ptr) -> (output_ptr):
    return (output_ptr=output_ptr + 1)
end
""", prime=PRIME)

    # Check that even if all builtin ptrs were passed as arguments but in the wrong order then
    # the same exception is thrown.
    with pytest.raises(AssertionError, match=re.escape(expected_error_msg)):
        compile_cairo(
            code="""
%builtins output range_check

func main(range_check_ptr, output_ptr) -> (range_check_ptr, output_ptr):
    return (range_check_ptr + 1, output_ptr=output_ptr + 1)
end
""", prime=PRIME)


def test_main_return_match_builtins():
    """
    Checks that an appropriate exception is thrown if the arguments in a given Cairo program's main
    don't match the list of builtins specified by the directive (and their order).
    """
    expected_error_msg = 'Expected main to return the following values (in this order): ' \
        "['output_ptr', 'range_check_ptr']"
    with pytest.raises(AssertionError, match=re.escape(expected_error_msg)):
        compile_cairo(
            code="""
%builtins output range_check

func main(output_ptr, range_check_ptr) -> (output_ptr):
    return (output_ptr=output_ptr + 1)
end
""", prime=PRIME)
