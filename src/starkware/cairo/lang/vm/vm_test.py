import tempfile
from typing import Optional, cast

import pytest

from starkware.cairo.lang.compiler.cairo_compile import compile_cairo
from starkware.cairo.lang.vm.memory_dict import (
    InconsistentMemoryError,
    MemoryDict,
    UnknownMemoryError,
)
from starkware.cairo.lang.vm.relocatable import (
    MaybeRelocatable,
    MaybeRelocatableDict,
    RelocatableValue,
)
from starkware.cairo.lang.vm.test_utils import run_program_in_vm
from starkware.cairo.lang.vm.virtual_machine_base import Rule, VirtualMachineBase
from starkware.cairo.lang.vm.vm import RunContext, VirtualMachine
from starkware.cairo.lang.vm.vm_exceptions import InconsistentAutoDeductionError, VmException
from starkware.python.test_utils import maybe_raises

PRIME = 2**64 + 13


def run_single(code: str, steps: int, *, pc=RelocatableValue(0, 10), ap=100, fp=100, extra_mem={}):
    program = compile_cairo(code, PRIME, debug_info=True)
    return run_program_in_vm(
        program=program, steps=steps, pc=pc, ap=ap, fp=fp, extra_mem=extra_mem, prime=PRIME
    )


def test_memory_dict():
    d: MaybeRelocatableDict = {1: 2}
    mem = MemoryDict(d)
    d[2] = 3
    assert 2 not in mem

    assert mem[1] == 2
    with pytest.raises(UnknownMemoryError):
        mem[2]
    mem[1] = 2
    with pytest.raises(InconsistentMemoryError):
        mem[1] = 3


def test_simple():
    code = """
[ap] = [ap - 1] + 2, ap++;
[ap] = [ap - 1] * 3, ap++;
[ap] = 10, ap++;
// Skip two instructions.
jmp rel 6;
[ap] = [ap - 1] + 4, ap++;  // Skipped.
[ap] = [ap - 1] + 5, ap++;  // Skipped.
[ap] = [ap - 1] + 6, ap++;
jmp abs 12;
[ap] = [ap - 1] * 7, ap++;
"""

    vm = run_single(code, 9, pc=10, ap=102, extra_mem={101: 1})

    assert [vm.run_context.memory[101 + i] for i in range(7)] == [1, 3, 9, 10, 16, 48, 10]
    assert (
        vm.accessed_addresses
        == set(vm.run_context.memory.keys())
        == {*range(10, 28), 99, *range(101, 108)}
    )


def test_jnz():
    code = """
[ap] = 7, ap++;

loop:
jmp body if [ap - 1] != 0;
[ap] = 4, ap++;

body:
[ap] = [ap - 1] - 1, ap++;
jmp loop;
"""

    vm = run_single(code, 100, ap=101)

    assert [vm.run_context.memory[101 + i] for i in range(8 + 25)] == [7, 6, 5, 4, 3, 2, 1, 0] + [
        4,
        3,
        2,
        1,
        0,
    ] * 5


@pytest.mark.parametrize("offset", [0, -1])
def test_jnz_relocatables(offset: int):
    code = """
jmp body if [ap - 1] != 0;
[ap] = 0, ap++;

body:
[ap] = 1, ap++;
"""
    relocatable_value = RelocatableValue(segment_index=5, offset=offset)
    error_message = (
        None
        if relocatable_value.offset >= 0
        else f"Could not complete computation jmp != 0 of non pure value: {relocatable_value}"
    )
    with maybe_raises(expected_exception=VmException, error_message=error_message):
        vm = run_single(code, 2, ap=102, extra_mem={101: relocatable_value})
        assert vm.run_context.memory[102] == 1


def test_call_ret():
    code = """
[fp] = 1000, ap++;
call a;
[ap] = [fp] + 1, ap++;
call a;
[ap] = [fp] + 2, ap++;

l_end:
jmp l_end;

a:
[fp] = 2000, ap++;
call b;
[ap] = [fp] + 1, ap++;
call b;
[ap] = [fp] + 2, ap++;
ret;

b:
[fp] = 3000, ap++;
ret;
"""

    vm = run_single(code, 30)

    # Consider the memory cells which are at least 1000 to filter out pc and fp addresses.
    mem = [vm.run_context.memory[100 + i] for i in range(25)]
    assert [x for x in mem if isinstance(x, int) and x >= 1000] == [
        1000,
        2000,
        3000,
        2001,
        3000,
        2002,
        1001,
        2000,
        3000,
        2001,
        3000,
        2002,
        1002,
    ]


def test_addap():
    code = """
[ap] = 3, ap++;
ap += 30;
[ap] = 4;
"""

    vm = run_single(code, 3)

    mem = [vm.run_context.memory.get(100 + i) for i in range(32)]
    assert mem == [3, *[None] * 30, 4]
    assert vm.run_context.ap == 131


def test_access_op1_ap():
    code = """
[ap] = 3, ap++;
[ap] = [ap - 1] * [ap - 1], ap++;
jmp abs [ap - 1] + [ap - 2];
"""

    vm = run_single(code, 3, ap=200)

    mem = [vm.run_context.memory.get(200 + i) for i in range(2)]
    assert mem == [3, 9]
    assert vm.run_context.pc == 12


def test_hints():
    code = """
const x = 1200;
const y = 8000;

%{
    # Test math utils.
    x = fdiv(3, 2)
    assert fmul(x, 2) == 3
    assert (x * 2) % PRIME == 3
    assert fsub(0, 1) == PRIME - 1
%}
call foo;

%{
    assert ids.x + ids.foo.y == 1234
    assert ids.y == 8000
    memory[fp + 1] = ids.z
%}
[fp] = [fp];

func foo() {
    const y = 34;
    const z = 0;
    let mem_at_fp_plus_one = [fp + 1];
    %{ abc = 123 %}
    [fp] = 2000;
    %{
        v = memory[fp] // 2

        ids.mem_at_fp_plus_one = v
        memory[fp + 2] = ids.x + ids.y

        # Make sure abc is accessible.
        assert abc == 123

        # Try to use imports in list comprehension (check that exec() is called correctly).
        import random
        [random.randrange(10) for _ in range(10)]
    %}
    [fp] = [fp + 1] + [fp + 1];
    ret;
}
"""

    vm = run_single(code, 4, ap=200)

    with pytest.raises(VmException, match="Unknown identifier 'z'"):
        vm.step()

    assert [vm.run_context.memory[202 + i] for i in range(3)] == [2000, 1000, 1234]
    # Check that address fp + 2, whose value was only set in a hint, is not counted as accessed.
    assert [202 + i in vm.accessed_addresses for i in range(3)] == [True, True, False]


def test_hint_between_references():
    code = """
let x = 1;
%{ assert ids.x == 1 %}
let x = 2;
%{ assert ids.x == 2 %}
ap += 0;
"""
    run_single(code=code, steps=1)


def test_nondet_hint_pointer():
    code = """
%{ from starkware.cairo.lang.vm.relocatable import RelocatableValue %}
tempvar x: felt* = cast(nondet %{ RelocatableValue(12, 34) %}, felt*) + 3;
"""
    vm = run_single(code=code, steps=2)
    assert vm.run_context.memory[101] == RelocatableValue(12, 37)


def test_hint_exception():
    code = """
// Some comment.

%{ x = 0 %}

%{
def f():
    0 / 0  # Raises exception.
%}
[ap] = 0, ap++;

%{ y = 0 %}
%{


f()
%}
[ap] = 1, ap++;
"""

    # In this test we actually do write the code to a file, to allow the linecache module to fetch
    # the line raising the exception.
    cairo_file = tempfile.NamedTemporaryFile("w")
    print(code, file=cairo_file)
    cairo_file.flush()
    program = compile_cairo(code=[(code, cairo_file.name)], prime=PRIME, debug_info=True)
    program_base = 10
    memory: MaybeRelocatableDict = {program_base + i: v for i, v in enumerate(program.data)}

    # Set memory[fp - 1] to an arbitrary value, since [fp - 1] is assumed to be set.
    memory[99] = 1234

    context = RunContext(
        pc=program_base,
        ap=200,
        fp=100,
        memory=MemoryDict(memory),
        prime=PRIME,
    )

    vm = VirtualMachine(program, context, {})

    vm.step()
    with pytest.raises(VmException) as excinfo:
        vm.step()
    assert (
        str(excinfo.value)
        == f"""\
{cairo_file.name}:13:1: Error at pc=12:
Got an exception while executing a hint.
%{{
^^
Traceback (most recent call last):
  File "{cairo_file.name}", line 16, in <module>
    f()
  File "{cairo_file.name}", line 8, in f
    0 / 0  # Raises exception.
ZeroDivisionError: division by zero\
"""
    )


def test_hint_indentation_error():
    code = """
// Some comment.

%{
    def f():
        b = 1
            a = 1 # Wrong indentation.
%}
[ap] = 0, ap++;
"""

    # In this test we actually do write the code to a file, to allow the linecache module to fetch
    # the line raising the exception.
    cairo_file = tempfile.NamedTemporaryFile("w")
    print(code, file=cairo_file)
    cairo_file.flush()
    program = compile_cairo(code=[(code, cairo_file.name)], prime=PRIME, debug_info=True)
    program_base = 10
    memory: MaybeRelocatableDict = {program_base + i: v for i, v in enumerate(program.data)}

    # Set memory[fp - 1] to an arbitrary value, since [fp - 1] is assumed to be set.
    memory[99] = 1234

    context = RunContext(
        pc=program_base,
        ap=200,
        fp=100,
        memory=MemoryDict(memory),
        prime=PRIME,
    )

    with pytest.raises(VmException) as excinfo:
        VirtualMachine(program, context, {})
    expected_error = f"""\
{cairo_file.name}:4:1: Error at pc=10:
Got an exception while compiling a hint.
%{{
^^
  File "{cairo_file.name}", line 7
    a = 1 # Wrong indentation.
IndentationError: unexpected indent\
"""
    assert expected_error == str(excinfo.value)


def test_hint_syntax_error():
    code = """
// Make sure the hint is not located at the start of the program.
[ap] = 1;

%{
    def f():
        b = # Wrong syntax.
        a = 1
%}
[ap] = 0, ap++;
"""

    # In this test we actually do write the code to a file, to allow the linecache module to fetch
    # the line raising the exception.
    cairo_file = tempfile.NamedTemporaryFile("w")
    print(code, file=cairo_file)
    cairo_file.flush()
    program = compile_cairo(code=[(code, cairo_file.name)], prime=PRIME, debug_info=True)
    program_base = 10
    memory: MaybeRelocatableDict = {program_base + i: v for i, v in enumerate(program.data)}

    # Set memory[fp - 1] to an arbitrary value, since [fp - 1] is assumed to be set.
    memory[99] = 1234

    context = RunContext(
        pc=program_base,
        ap=200,
        fp=100,
        memory=MemoryDict(memory),
        prime=PRIME,
    )

    with pytest.raises(VmException) as excinfo:
        VirtualMachine(program, context, {})
    expected_error = f"""\
{cairo_file.name}:5:1: Error at pc=12:
Got an exception while compiling a hint.
%{{
^^
  File "{cairo_file.name}", line 7
    b = # Wrong syntax.
        ^
SyntaxError: invalid syntax\
"""
    assert expected_error == str(excinfo.value)


def test_hint_scopes():
    code = """
%{
    outer_scope_var = 17
    vm_enter_scope({'inner_scope_var': 'scope 1'})
    assert outer_scope_var == 17
    assert 'inner_scope_var' not in locals()
%}
[ap] = 1, ap++;
%{
    assert 'outer_scope_var' not in locals()
    assert inner_scope_var == 'scope 1'
    # create new inner_scope_var local in the inner scope.
    vm_enter_scope({'inner_scope_var': 'scope 2'})
%}
[ap] = 2, ap++;
%{
    assert 'outer_scope_var' not in locals()
    assert inner_scope_var == 'scope 2'
    vm_exit_scope()
%}
[ap] = 3, ap++;
%{
    # Make sure that the we get the original inner_scope_var.
    assert inner_scope_var == 'scope 1'
    vm_exit_scope()
%}
[ap] = 4, ap++;
%{
    assert outer_scope_var == 17
    # Try to access a variable in the scope we just exited.
    inner_scope_var
%}
[ap] = 5, ap++;
"""

    vm = run_single(code, 4)
    with pytest.raises(VmException, match="name 'inner_scope_var' is not defined"):
        vm.step()


def test_skip_instruction_execution():
    code = """
%{
    x = 0
    vm.run_context.pc += 2
    vm.skip_instruction_execution = True
%}
[ap] = [ap] + 1, ap++;  // This intruction will not be executed.
%{ x = 1 %}
[ap] = 10, ap++;
"""

    program = compile_cairo(code, PRIME, debug_info=True)

    initial_ap = 100
    memory: MaybeRelocatableDict = {
        **{i: v for i, v in enumerate(program.data)},
        initial_ap - 1: 1234,
    }
    context = RunContext(
        pc=0,
        ap=initial_ap,
        fp=initial_ap,
        memory=MemoryDict(memory),
        prime=PRIME,
    )

    vm = VirtualMachine(program, context, {})
    vm.enter_scope({"vm": vm})
    exec_locals = vm.exec_scopes[-1]

    assert "x" not in exec_locals
    assert vm.run_context.pc == 0
    vm.step()
    assert exec_locals["x"] == 0
    assert vm.run_context.pc == 2
    vm.step()
    assert exec_locals["x"] == 1
    assert vm.run_context.pc == 4
    assert vm.run_context.ap == initial_ap + 1
    assert vm.run_context.memory[vm.run_context.ap - 1] == 10
    vm.exit_scope()


def test_auto_deduction_rules():
    code = """
[fp + 1] = [fp] + [ap];
"""

    program = compile_cairo(code=code, prime=PRIME, debug_info=True)
    memory: MaybeRelocatableDict = {i: v for i, v in enumerate(program.data)}
    initial_ap = RelocatableValue(segment_index=1, offset=200)
    initial_fp = RelocatableValue(segment_index=2, offset=100)

    context = RunContext(
        pc=0,
        ap=initial_ap,
        fp=initial_fp,
        memory=MemoryDict(memory),
        prime=PRIME,
    )

    vm = VirtualMachine(program, context, {})

    def rule_ap_segment(
        vm: VirtualMachineBase, addr: MaybeRelocatable, val: MaybeRelocatable
    ) -> Optional[MaybeRelocatable]:
        return val

    vm.add_auto_deduction_rule(1, cast(Rule, rule_ap_segment), 100)
    vm.add_auto_deduction_rule(2, cast(Rule, lambda vm, addr: None))
    vm.add_auto_deduction_rule(2, cast(Rule, lambda vm, addr: 200 if addr == initial_fp else None))
    vm.add_auto_deduction_rule(2, cast(Rule, lambda vm, addr: 456))

    vm.step()

    assert vm.run_context.memory[initial_ap] == 100
    assert vm.run_context.memory[initial_fp] == 200
    assert vm.run_context.memory[initial_fp + 1] == 300

    with pytest.raises(InconsistentAutoDeductionError, match="at address 2:100. 200 != 456"):
        vm.verify_auto_deductions()


def test_memory_validation_in_hints():
    code = """
%{ memory[ap] = 0 %}
[ap] = [ap], ap++;
%{ memory[ap] = 0 %}
[ap] = [ap], ap++;
"""

    program = compile_cairo(code=code, prime=PRIME, debug_info=True)
    initial_ap_and_fp = RelocatableValue(segment_index=1, offset=200)
    memory: MaybeRelocatableDict = {i: v for i, v in enumerate(program.data)}
    # Set memory[fp - 1] to an arbitrary value, since [fp - 1] is assumed to be set.
    memory[initial_ap_and_fp - 1] = 1234

    context = RunContext(
        pc=0,
        ap=initial_ap_and_fp,
        fp=initial_ap_and_fp,
        memory=MemoryDict(memory),
        prime=PRIME,
    )

    vm = VirtualMachine(program, context, {})

    vm.add_validation_rule(1, lambda memory, addr: {addr})
    assert vm.validated_memory._ValidatedMemoryDict__validated_addresses == set()
    vm.step()
    assert vm.validated_memory._ValidatedMemoryDict__validated_addresses == {initial_ap_and_fp}

    def fail_validation(memory, addr):
        raise Exception("Validation failed.")

    vm.add_validation_rule(1, fail_validation)
    with pytest.raises(VmException, match="Exception: Validation failed."):
        vm.step()


def test_nonpure_mul():
    code = """
[ap] = [ap - 1] * 2, ap++;
"""

    with pytest.raises(VmException, match="Could not complete computation *"):
        run_single(code, 1, ap=102, extra_mem={101: RelocatableValue(1, 0)})


def test_nonpure_jmp_rel():
    code = """
jmp rel [ap - 1];
"""

    with pytest.raises(VmException, match="Could not complete computation jmp rel"):
        run_single(code, 1, ap=102, extra_mem={101: RelocatableValue(1, 0)})


def test_jmp_segment():
    code = """
jmp abs [ap], ap++;
"""
    program = compile_cairo(code=code, prime=PRIME, debug_info=True)

    program_base_a = RelocatableValue(0, 10)
    program_base_b = RelocatableValue(1, 20)

    memory: MaybeRelocatableDict = {
        **{program_base_a + i: v for i, v in enumerate(program.data)},
        **{program_base_b + i: v for i, v in enumerate(program.data)},
        99: 0,
        100: program_base_b,
        101: program_base_a,
    }
    context = RunContext(
        pc=program_base_a,
        ap=100,
        fp=100,
        memory=MemoryDict(memory),
        prime=PRIME,
    )

    vm = VirtualMachine(program, context, {})
    vm.step()
    assert vm.run_context.pc == program_base_b
    assert vm.get_location(vm.run_context.pc) is None
    vm.step()
    assert vm.run_context.pc == program_base_a
    assert vm.get_location(vm.run_context.pc) is not None


def test_simple_deductions():
    code = """
// 2 = 3 * ?.
[fp] = [fp - 1] * [ap], ap++;
// 2 = ? * 3.
[fp] = [ap] * [fp - 1], ap++;
// 2 = 3 + ?.
[fp] = [fp - 1] + [ap], ap++;
// 2 = ? + 3.
[fp] = [ap] + [fp - 1], ap++;
// 2 = ?.
[fp] = [ap], ap++;
// ? = 2.
[ap] = [fp], ap++;
"""

    vm = run_single(code, 6, ap=101, extra_mem={99: 3, 100: 2})

    assert [vm.run_context.memory[101 + i] for i in range(6)] == [
        (2 * PRIME + 2) // 3,
        (2 * PRIME + 2) // 3,
        PRIME - 1,
        PRIME - 1,
        2,
        2,
    ]


def test_failing_assert_eq():
    code = """
[ap] = [ap + 1] + [ap + 2];
"""

    with pytest.raises(VmException, match="An ASSERT_EQ instruction failed"):
        run_single(code, 1, extra_mem={100: 1, 101: 3, 102: 2})


def test_call_unknown():
    code = """
call rel [ap];
"""
    with pytest.raises(VmException, match="Unknown value for memory cell at address 100"):
        run_single(code, 1)


def test_invalid_instruction():
    code = """
dw -1;
"""
    with pytest.raises(VmException) as exc_info:
        run_single(code, 1)

    assert str(exc_info.value) == (
        """\
:2:1: Error at pc=0:10:
Unsupported instruction.
dw -1;
^***^\
"""
    )


def test_call_wrong_operands():
    code = """
call rel 0;
"""
    with pytest.raises(
        VmException,
        match=r"Call failed to write return-pc \(inconsistent op0\): 0 != 0:12. "
        + "Did you forget to increment ap?",
    ):
        run_single(code, 1, extra_mem={101: 0})
    with pytest.raises(
        VmException,
        match=r"Call failed to write return-fp \(inconsistent dst\): 0 != 100. "
        + "Did you forget to increment ap?",
    ):
        run_single(code, 1, extra_mem={100: 0})


def test_traceback():
    code = """
call main;

func foo(x) {
    %{ assert ids.x != 0 %}
    return ();
}

func bar(x) {
    foo(x * x * x);
    return ();
}

func main() {
    bar(x=1);
    bar(x=0);  // This line will cause an error.
    return ();
}
"""

    with pytest.raises(VmException) as exc_info:
        run_single(code, 100, ap=101, extra_mem={99: 3, 100: 2})

    assert (
        str(exc_info.value)
        == """\
:5:5: Error at pc=0:12:
Got an exception while executing a hint.
    %{ assert ids.x != 0 %}
    ^*********************^
Cairo traceback (most recent call last):
:2:1: (pc=0:10)
call main;
^*******^
:16:5: (pc=0:24)
    bar(x=0);  // This line will cause an error.
    ^******^
:10:5: (pc=0:15)
    foo(x * x * x);
    ^************^

Traceback (most recent call last):
  File "", line 5, in <module>
AssertionError\
"""
    )


def test_traceback_with_attr():
    code = """
call main;

func foo(x) {
    with_attr error_message("Error in foo (x={x}).") {
        with_attr error_message("Should not appear in trace.") {
            assert 0 = 0;
        }
        with_attr attr_name("Should not appear in trace (attr_name instead of error_message).") {
            %{ assert ids.x != 1 %}
            [ap] = 1, ap++;
        }
    }
    return ();
}

func bar(x) {
    tempvar y = x + 2;
    // y and x.y evaluation should fail (y is ap-based and x.y doesn't exist).
    with_attr error_message("Error in bar (x={x}, y={y}, {x.y}).") {
        foo(y * y * y);
    }
    return ();
}

func main() {
    with_attr error_message("Error in main.") {
        with_attr error_message("Running bar(x=1).") {
            bar(x=1);
        }
        with_attr error_message("Running bar(x=0).") {
            bar(x=-1);  // This line will cause an error.
        }
    }
    return ();
}
"""

    with pytest.raises(VmException) as exc_info:
        run_single(code, 100, pc=RelocatableValue(0, 10), ap=101, extra_mem={99: 3, 100: 2})

    assert (
        str(exc_info.value)
        == """\
Error message: Error in foo (x=1).
:10:13: Error at pc=0:16:
Got an exception while executing a hint.
            %{ assert ids.x != 1 %}
            ^*********************^
Cairo traceback (most recent call last):
:2:1: (pc=0:10)
call main;
^*******^
Error message: Running bar(x=0).
Error message: Error in main.
:32:13: (pc=0:32)
            bar(x=-1);  // This line will cause an error.
            ^*******^
Error message: Error in bar (x=-1, y={y}, {x.y}). (Cannot evaluate ap-based or complex references: \
['y', 'x.y'])
:21:9: (pc=0:23)
        foo(y * y * y);
        ^************^

Traceback (most recent call last):
  File "", line 10, in <module>
AssertionError\
"""
    )
