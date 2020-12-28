import pytest

from starkware.cairo.lang.compiler.cairo_compile import compile_cairo
from starkware.cairo.lang.vm.cairo_runner import CairoRunner
from starkware.cairo.lang.vm.crypto import get_crypto_lib_context_manager
from starkware.cairo.lang.vm.security import SecurityError, verify_secure_runner

PRIME = 2**251 + 17 * 2**192 + 1


def run_code_in_runner(code, layout='plain'):
    program = compile_cairo(code, PRIME)
    runner = CairoRunner(program, layout=layout)
    runner.initialize_segments()
    end = runner.initialize_main_entrypoint()
    runner.initialize_vm(hint_locals={})
    runner.run_until_pc(end)
    runner.end_run()
    runner.read_return_values()
    runner.finalize_segments_by_effective_size()
    return runner


def test_completeness():
    verify_secure_runner(run_code_in_runner("""
main:
[ap] = 1
ret
"""))


def test_negative_addresses():
    # Negative value is taken modulo prime, so it is caught as non continuity.
    with pytest.raises(SecurityError, match='Non continuous segment 1 at offset 2'):
        verify_secure_runner(run_code_in_runner("""
main:
[fp - 100] = 1
ret
"""))


def test_out_of_program_bounds():
    with pytest.raises(SecurityError, match='Out of bounds access to program segment'):
        verify_secure_runner(run_code_in_runner("""
main:
call test
ret
test:
[ap] = [fp - 1]  # pc.
[ap] = [[ap] + 4] # Write right after end of program.
ret
"""))


def test_non_continuous_access():
    with pytest.raises(SecurityError, match='Non continuous segment 1 at offset 4'):
        verify_secure_runner(run_code_in_runner("""
main:
[ap] = 3; ap++
[ap] = 4; ap++
[ap + 1] = 5
ret
"""))


def test_pure_address_access():
    runner = run_code_in_runner("""
main:
[fp - 1] = [fp - 1]  # nop.
ret
""")
    # Access a pure address manually, because runner disallows it as well.
    runner.vm_memory[1234] = 1

    with pytest.raises(SecurityError, match='Accessed address 1234 is not relocatable.'):
        verify_secure_runner(runner)


def test_builtin_segment_access():
    # Non continuous is ok.
    with get_crypto_lib_context_manager(flavor=None):
        verify_secure_runner(run_code_in_runner(
            """
%builtins pedersen
main:
[ap] = 1; ap++
[ap - 1] = [[fp - 3] + 0]
[ap - 1] = [[fp - 3] + 1]
[ap] = [[fp - 3] + 2]; ap++  # Read hash result.
[ap] = [fp - 3] + 3; ap++  # Return pedersen_ptr.
ret
""",
            layout='small'))

    # Out of bound is not ok.
    runner = run_code_in_runner(
        """
%builtins pedersen
main:
[fp - 1] = [[fp - 3] + 2]  # Access only the result portion of the builtin.
[ap] = [fp - 3] + 3; ap++  # Return pedersen_ptr.
ret
""",
        layout='small')
    # Access out of bounds manually, because runner disallows it as well.
    pedersen_base = runner.builtin_runners['pedersen_builtin'].base
    runner.vm_memory[pedersen_base + 7] = 1
    with pytest.raises(SecurityError, match='Out of bounds access to builtin segment pedersen'):
        verify_secure_runner(runner)
