import pytest

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.vm.cairo_runner import get_runner_from_code
from starkware.cairo.lang.vm.crypto import get_crypto_lib_context_manager
from starkware.cairo.lang.vm.relocatable import RelocatableValue
from starkware.cairo.lang.vm.security import verify_secure_runner
from starkware.cairo.lang.vm.vm_exceptions import SecurityError


def run_code_in_runner(code, layout="plain"):
    return get_runner_from_code(code=code, layout=layout, prime=DEFAULT_PRIME)


def test_completeness():
    verify_secure_runner(
        run_code_in_runner(
            """
main:
[ap] = 1;
ret;
"""
        )
    )


def test_negative_address():
    runner = run_code_in_runner(
        """
main:
[ap] = 0, ap++;
ret;
"""
    )
    # Access negative offset manually, so it is not taken modulo prime.
    runner.vm_memory.set_without_checks(RelocatableValue(segment_index=0, offset=-17), 0)
    with pytest.raises(SecurityError, match="Accessed address 0:-17 has negative offset."):
        verify_secure_runner(runner)


def test_out_of_program_bounds():
    with pytest.raises(SecurityError, match="Out of bounds access to program segment"):
        verify_secure_runner(
            run_code_in_runner(
                """
main:
call test;
ret;

test:
[ap] = [fp - 1];  // pc.
[ap] = [[ap] + 4];  // Write right after end of program.
ret;
"""
            )
        )


def test_pure_address_access():
    runner = run_code_in_runner(
        """
main:
[fp - 1] = [fp - 1];  // nop.
ret;
"""
    )
    # Access a pure address manually, because runner disallows it as well.
    runner.vm_memory.unfreeze_for_testing()
    runner.vm_memory[1234] = 1

    with pytest.raises(SecurityError, match="Accessed address 1234 is not relocatable."):
        verify_secure_runner(runner)


def test_builtin_segment_access():
    with get_crypto_lib_context_manager(flavor=None):
        verify_secure_runner(
            run_code_in_runner(
                """
%builtins pedersen

main:
[ap] = 1, ap++;
[ap - 1] = [[fp - 3] + 0];
[ap - 1] = [[fp - 3] + 1];
[ap] = [[fp - 3] + 2], ap++;  // Read hash result.
[ap] = [fp - 3] + 3, ap++;  // Return pedersen_ptr.
ret;
""",
                layout="small",
            )
        )

    # Out of bound is not ok.
    runner = run_code_in_runner(
        """
%builtins pedersen

main:
[fp - 1] = [[fp - 3] + 2];  // Access only the result portion of the builtin.
[ap] = [fp - 3] + 3, ap++;  // Return pedersen_ptr.
ret;
""",
        layout="small",
    )
    # Access out of bounds manually, because runner disallows it as well.
    pedersen_base = runner.builtin_runners["pedersen_builtin"].base
    runner.vm_memory.unfreeze_for_testing()
    runner.vm_memory[pedersen_base + 7] = 1
    with pytest.raises(SecurityError, match="Out of bounds access to builtin segment pedersen"):
        verify_secure_runner(runner)

    # Invalid segment size (only first input is written).
    with pytest.raises(SecurityError, match=r"Missing memory cells for pedersen: 1, 4\."):
        verify_secure_runner(
            run_code_in_runner(
                """
%builtins pedersen
func main{pedersen_ptr}() {
    assert [pedersen_ptr] = 0;
    assert [pedersen_ptr + 2] = 0;
    assert [pedersen_ptr + 3] = 0;
    assert [pedersen_ptr + 5] = 0;
    let pedersen_ptr = pedersen_ptr + 6;
    return ();
}
""",
                layout="small",
            )
        )
