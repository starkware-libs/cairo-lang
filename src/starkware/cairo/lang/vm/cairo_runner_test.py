import os
import re

import pytest

from starkware.cairo.lang.compiler.cairo_compile import compile_cairo
from starkware.cairo.lang.vm.builtin_runner import InsufficientAllocatedCells
from starkware.cairo.lang.vm.cairo_runner import CairoRunner, get_runner_from_code
from starkware.cairo.lang.vm.vm import VmException, VmExceptionBase

CAIRO_FILE = os.path.join(os.path.dirname(__file__), 'test.cairo')
PRIME = 2 ** 251 + 17 * 2 ** 192 + 1


def test_run_until_label():
    runner = CairoRunner.from_file(CAIRO_FILE, PRIME, proof_mode=True)
    runner.initialize_segments()
    runner.initialize_main_entrypoint()
    runner.initialize_vm({})

    # Test runs.
    assert runner.vm.run_context.pc - runner.program_base == 0
    runner.run_until_label(3)
    assert runner.vm.run_context.pc - runner.program_base == 3
    assert runner.vm.current_step == 3
    runner.run_until_label('label1')
    assert runner.vm.run_context.pc - runner.program_base == 6
    assert runner.vm.current_step == 6
    with pytest.raises(VmException, match='End of program was not reached'):
        runner.run_until_label('label0', max_steps=100)
    assert runner.vm.run_context.pc - runner.program_base == 8
    assert runner.vm.current_step == 106
    runner.run_until_next_power_of_2()
    assert runner.vm.current_step == 128


def test_run_past_end():
    code = """\
func main():
    ret
end
"""
    program = compile_cairo(code, PRIME)
    runner = CairoRunner(program, layout='plain')
    runner.initialize_segments()
    runner.initialize_main_entrypoint()
    runner.initialize_vm({})

    runner.run_for_steps(1)
    with pytest.raises(VmException, match='Error: Execution reached the end of the program.'):
        runner.run_for_steps(1)


def test_bad_stop_ptr():
    code = """\
%builtins output

func main(output_ptr) -> (output_ptr):
    [ap] = 0; ap++
    [ap - 1] = [output_ptr]
    [ap] = output_ptr + 3; ap++  # The correct return value is output_ptr + 1
    ret
end
"""
    with pytest.raises(
            AssertionError,
            match='Invalid stop pointer for output. Expected: 2:1, found: 2:3'):
        runner = get_runner_from_code(code, layout='small', prime=PRIME)


def test_builtin_list():
    # This should work.
    program = compile_cairo(
        code=[('%builtins output pedersen range_check ecdsa\n', '')], prime=PRIME)
    CairoRunner(program, layout='small')

    # These should fail.
    program = compile_cairo(code=[('%builtins pedersen output\n', '')], prime=PRIME)
    with pytest.raises(
            AssertionError,
            match=r"Expected builtin list \['output', 'pedersen'\] does not match "
            r"\['pedersen', 'output'\]."):
        CairoRunner(program, layout='small')

    program = compile_cairo(code=[('%builtins pedersen foo\n', '')], prime=PRIME)
    with pytest.raises(
            AssertionError,
            match=r'Builtins {\'foo\'} are not present in layout "small"'):
        CairoRunner(program, layout='small')


def test_missing_exit_scope():
    code = """\
func main():
    %{ vm_enter_scope() %}
    ret
end
"""
    with pytest.raises(
            VmExceptionBase,
            match=re.escape('Every enter_scope() requires a corresponding exit_scope().')):
        runner = get_runner_from_code(code, layout='small', prime=PRIME)


def test_load_data_after_init():
    code = """\
func main():
    ret
end
"""
    runner = get_runner_from_code(code, layout='plain', prime=PRIME)
    addr = runner.segments.add()
    runner.load_data(addr, [42])
    assert runner.vm_memory[addr] == 42


def test_small_memory_hole():
    code = """\
func main():
    [ap] = 0
    ap += 4
    [ap] = 0
    ret
end
"""
    runner = get_runner_from_code(code, layout='plain', prime=PRIME)
    runner.check_memory_usage()


def test_memory_hole_insufficient():
    code = """\
func main():
    [ap] = 0
    ap += 1000
    [ap] = 0
    ret
end
"""
    runner = get_runner_from_code(code, layout='plain', prime=PRIME)

    with pytest.raises(
            InsufficientAllocatedCells,
            match=re.escape(
                'There are only 8 cells to fill the memory address holes, but 999 are required.')):
        runner.check_memory_usage()
