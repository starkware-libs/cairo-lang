import dataclasses
from typing import Dict

import pytest

from starkware.cairo.lang.builtins.builtin_runner_test_utils import compile_and_run
from starkware.cairo.lang.builtins.modulo.instance_def import AddModInstanceDef, MulModInstanceDef
from starkware.cairo.lang.builtins.modulo.mod_builtin_runner import (
    AddModBuiltinRunner,
    ModBuiltinRunner,
    MulModBuiltinRunner,
)
from starkware.cairo.lang.instances import all_cairo_instance
from starkware.cairo.lang.vm.builtin_runner import SimpleBuiltinRunner
from starkware.cairo.lang.vm.cairo_runner import CairoRunner
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.relocatable import RelocatableValue
from starkware.cairo.lang.vm.vm_exceptions import SecurityError, VmException


def check_result(runner: ModBuiltinRunner, inverse_bool: bool, p: int, x1: int, x2: int, res: int):
    """
    Tests whether runner completes a trio a, b, c as the input implies:
    If inverse_bool is False it tests whether a=x1, b=x2, c=None will be completed with c=res.
    If inverse_bool is True it tests whether c=x1, b=x2, a=None will be completed with a=res.
    The case c=x1, a=x2, b=None is currently completely symmetric in fill_value so it isn't tested.
    This function does not return a value but instead asserts equality.
    """
    nwords = runner.instance_def.n_words
    memory = MemoryDict()
    offsets_ptr = RelocatableValue(0, 0)
    memory[offsets_ptr + 0] = 0
    memory[offsets_ptr + 1] = nwords
    memory[offsets_ptr + 2] = 2 * nwords

    values_ptr = RelocatableValue(0, 24)
    runner.write_n_words_value(memory, values_ptr + nwords, x2)
    x1_addr = values_ptr
    res_addr = values_ptr + 2 * nwords

    if inverse_bool:
        (x1_addr, res_addr) = (res_addr, x1_addr)

    runner.write_n_words_value(memory, x1_addr, x1)

    ModBuiltinRunner.InstanceData(
        builtin=runner,
        memory=memory,
        values_ptr=values_ptr,
        offsets_ptr=offsets_ptr,
        modulus=p,
    ).fill_value(index=0)
    _, out_res = runner.read_n_words_value(memory, res_addr)
    assert out_res == res


@pytest.fixture(params=[1, 8])
def batch_size(request):
    return request.param


@pytest.fixture
def run_mod_p_circuit(batch_size):
    run_mod_p_circuit = (
        "run_mod_p_circuit" if batch_size == 1 else "run_mod_p_circuit_with_large_batch_size"
    )
    return run_mod_p_circuit


@pytest.fixture
def layout(batch_size):
    # Create a dummy layout.
    layout = dataclasses.replace(
        all_cairo_instance,
        builtins={
            **all_cairo_instance.builtins,
            "add_mod": AddModInstanceDef(
                ratio=1, ratio_den=1, word_bit_len=3, n_words=4, batch_size=batch_size
            ),
            "mul_mod": MulModInstanceDef(
                ratio=1,
                ratio_den=1,
                word_bit_len=3,
                n_words=4,
                batch_size=batch_size,
                bits_per_part=1,
            ),
        },
    )
    return layout


@pytest.fixture
def builtin_runners(layout):
    builtin_runners: Dict[str, ModBuiltinRunner] = {
        "add_mod_builtin": AddModBuiltinRunner(
            included=True,
            instance_def=layout.builtins["add_mod"],
        ),
        "mul_mod_builtin": MulModBuiltinRunner(
            included=True,
            instance_def=layout.builtins["mul_mod"],
        ),
    }
    return builtin_runners


def test_mod_builtin_runner(batch_size, layout, run_mod_p_circuit):
    CODE_FORMAT = """
%builtins range_check add_mod mul_mod
from starkware.cairo.common.cairo_builtins import ModBuiltin, UInt384
from starkware.cairo.common.registers import get_label_location
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.modulo import {run_mod_p_circuit}

func main{{range_check_ptr, add_mod_ptr: ModBuiltin*, mul_mod_ptr: ModBuiltin*}}() {{
    alloc_locals;

    let p = UInt384(d0={p[0]}, d1={p[1]}, d2={p[2]}, d3={p[3]});
    let x1 = UInt384(d0={x1[0]}, d1={x1[1]}, d2={x1[2]}, d3={x1[3]});
    let x2 = UInt384(d0={x2[0]}, d1={x2[1]}, d2={x2[2]}, d3={x2[3]});
    let x3 = UInt384(d0={x3[0]}, d1={x3[1]}, d2={x3[2]}, d3={x3[3]});
    let res = UInt384(d0={res[0]}, d1={res[1]}, d2={res[2]}, d3={res[3]});

    let (local values_arr: UInt384*) = alloc();
    assert values_arr[0] = x1;
    assert values_arr[1] = x2;
    assert values_arr[2] = x3;
    assert values_arr[7] = res;

    let (local add_mod_offsets_arr: felt*) = alloc();
    assert add_mod_offsets_arr[0] = 0;   // x1
    assert add_mod_offsets_arr[1] = 12;  // x2 - x1
    assert add_mod_offsets_arr[2] = 4;   // x2
    assert add_mod_offsets_arr[3] = 16;  // (x2 - x1) / x3
    assert add_mod_offsets_arr[4] = 20;  // x1 / x3
    assert add_mod_offsets_arr[5] = 24;  // (x2 - x1) / x3 + x1 / x3

    let (local mul_mod_offsets_arr: felt*) = alloc();
    assert mul_mod_offsets_arr[0] = 8;   // x3
    assert mul_mod_offsets_arr[1] = 16;  // (x2 - x1) / x3
    assert mul_mod_offsets_arr[2] = 12;  // (x2 - x1)
    assert mul_mod_offsets_arr[3] = 8;   // x3
    assert mul_mod_offsets_arr[4] = 20;  // x1 / x3
    assert mul_mod_offsets_arr[5] = 0;  // x1
    assert mul_mod_offsets_arr[6] = 8;   // x3
    assert mul_mod_offsets_arr[7] = 24;  // ((x2 - x1) / x3 + x1 / x3)
    assert mul_mod_offsets_arr[8] = 28;  // ((x2 - x1) / x3 + x1 / x3) * x3

    {run_mod_p_circuit}(
        p=p,
        values_ptr=values_arr,
        add_mod_offsets_ptr=add_mod_offsets_arr,
        add_mod_n=2,
        mul_mod_offsets_ptr=mul_mod_offsets_arr,
        mul_mod_n=3,
    );

    return ();
}}
"""

    # A valid computation.
    compile_and_run(
        CODE_FORMAT.format(
            p=[1, 1, 0, 0],
            x1=[1, 0, 0, 0],
            x2=[2, 1, 0, 0],
            x3=[2, 0, 0, 0],
            res=[1, 0, 0, 0],
            run_mod_p_circuit=run_mod_p_circuit,
        ),
        layout=layout,
        secure_run=True,
    )

    # Test that the runner fails where a0 is too big.
    with pytest.raises(VmException, match="Expected integer at address .* to be smaller"):
        compile_and_run(
            CODE_FORMAT.format(
                p=[1, 1, 0, 0],
                x1=[8, 0, 0, 0],
                x2=[2, 1, 0, 0],
                x3=[2, 0, 0, 0],
                res=[1, 0, 0, 0],
                run_mod_p_circuit=run_mod_p_circuit,
            ),
            layout=layout,
            secure_run=True,
        )

    # Test that the runner fails when an incorrect result is given.
    with pytest.raises(SecurityError, match=r"Expected a .* b == c \(mod p\)"):
        compile_and_run(
            CODE_FORMAT.format(
                p=[1, 1, 0, 0],
                x1=[1, 0, 0, 0],
                x2=[2, 1, 0, 0],
                x3=[2, 0, 0, 0],
                res=[2, 0, 0, 0],
                run_mod_p_circuit=run_mod_p_circuit,
            ),
            layout=layout,
            secure_run=True,
        )

    expected_error = (
        "Inconsistent memory assignment at address 4:6\. 3 != 0\."
        if batch_size == 1
        else "Inverse failure is supported only at batch_size == 1\."
    )

    # Test that the runner fails when dividing by zero.
    with pytest.raises(
        VmException,
        match=expected_error,
    ):
        compile_and_run(
            CODE_FORMAT.format(
                p=[1, 1, 0, 0],
                x1=[1, 0, 0, 0],
                x2=[2, 1, 0, 0],
                x3=[0, 0, 0, 0],
                res=[2, 0, 0, 0],
                run_mod_p_circuit=run_mod_p_circuit,
            ),
            layout=layout,
            secure_run=True,
        )


def read_builtin_segment_at_offset(runner: CairoRunner, builtin_name: str, offset: int):
    """
    Returns the value at runner.builtin_runners[builtin_name] + offset,
    Assumes builtin_runner is a SimpleBuiltinRunner.
    """
    builtin_runner = runner.builtin_runners[builtin_name]
    assert isinstance(builtin_runner, SimpleBuiltinRunner)
    return runner.memory[builtin_runner.base + offset]


def test_mod_builtin_inverse():
    CODE_FORMAT = """
%builtins range_check96 add_mod mul_mod
from starkware.cairo.common.cairo_builtins import ModBuiltin, UInt384
from starkware.cairo.common.alloc import alloc

func main{{range_check96_ptr, add_mod_ptr: ModBuiltin*, mul_mod_ptr: ModBuiltin*}}() {{
    alloc_locals;

    let x1 = UInt384(d0={x1[0]}, d1={x1[1]}, d2={x1[2]}, d3={x1[3]});

    let values_arr = cast(range_check96_ptr, UInt384*);
    assert values_arr[0] = UInt384(1, 0, 0, 0);
    assert values_arr[1] = x1;


    let (local mul_mod_offsets_arr: felt*) = alloc();
    assert mul_mod_offsets_arr[0] = 0;  // 1
    assert mul_mod_offsets_arr[1] = 0;  // 1
    assert mul_mod_offsets_arr[2] = 0;  // 1 * 1
    assert mul_mod_offsets_arr[3] = 4;  // x1
    assert mul_mod_offsets_arr[4] = 8;  // x1 ^ (-1)
    assert mul_mod_offsets_arr[5] = 0;  // 1

    assert mul_mod_ptr[0].p = UInt384({p[0]}, {p[1]}, {p[2]}, {p[3]});
    assert mul_mod_ptr[0].values_ptr = values_arr;
    assert mul_mod_ptr[0].offsets_ptr = mul_mod_offsets_arr;

    %{{
        from starkware.cairo.lang.builtins.modulo.mod_builtin_runner import ModBuiltinRunner
        assert builtin_runners["add_mod_builtin"].instance_def.batch_size == 1
        assert builtin_runners["mul_mod_builtin"].instance_def.batch_size == 1

        ModBuiltinRunner.fill_memory(
            memory=memory,
            add_mod=(ids.add_mod_ptr.address_, builtin_runners["add_mod_builtin"], 0),
            mul_mod=(ids.mul_mod_ptr.address_, builtin_runners["mul_mod_builtin"], 2),
        )
    %}}

    let range_check96_ptr = range_check96_ptr + 12;
    let mul_mod_ptr = &mul_mod_ptr[mul_mod_ptr.n];

    return ();
}}
"""

    # Valid Computation.
    runner = compile_and_run(
        CODE_FORMAT.format(
            p=[7, 0, 0, 0],
            x1=[3, 0, 0, 0],
        ),
        layout=all_cairo_instance,
        secure_run=True,
    )

    # Check that two mul mod gates were computed and that the inverse is correct.
    assert read_builtin_segment_at_offset(runner, "mul_mod_builtin", 6) == 2
    assert read_builtin_segment_at_offset(runner, "range_check96_builtin", 8) == 5

    # Fail on second multiplication.
    runner = compile_and_run(
        CODE_FORMAT.format(
            p=[55, 0, 0, 0],
            x1=[11, 0, 0, 0],
        ),
        layout=all_cairo_instance,
        secure_run=True,
    )

    # Check that only the one mul mod gate was computed and that a nullifier is written instead
    # of the inverse.
    assert read_builtin_segment_at_offset(runner, "mul_mod_builtin", 6) == 1
    assert read_builtin_segment_at_offset(runner, "range_check96_builtin", 8) == 5

    # Fail on second multiplication.
    runner = compile_and_run(
        CODE_FORMAT.format(
            p=[7, 0, 0, 0],
            x1=[0, 0, 0, 0],
        ),
        layout=all_cairo_instance,
        secure_run=True,
    )

    # Check that only the one mul mod gate was computed and that a nullifier is written instead
    # of the inverse.
    assert read_builtin_segment_at_offset(runner, "mul_mod_builtin", 6) == 1
    assert read_builtin_segment_at_offset(runner, "range_check96_builtin", 8) == 1


def test_mod_builtin_zero_mulmods():
    CODE_FORMAT = """
%builtins range_check96 add_mod mul_mod
from starkware.cairo.common.cairo_builtins import ModBuiltin, UInt384
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.modulo import run_mod_p_circuit

func main{{range_check96_ptr, add_mod_ptr: ModBuiltin*, mul_mod_ptr: ModBuiltin*}}() {{
    alloc_locals;

    let x1 = UInt384(d0={x1[0]}, d1={x1[1]}, d2={x1[2]}, d3={x1[3]});

    let values_arr = cast(range_check96_ptr, UInt384*);
    assert values_arr[0] = UInt384(0, 0, 0, 0);
    assert values_arr[1] = x1;

    let (local add_mod_offsets_arr: felt*) = alloc();
    assert add_mod_offsets_arr[0] = 4;  // x1
    assert add_mod_offsets_arr[1] = 0;  // 0
    assert add_mod_offsets_arr[2] = 4;  // x1

    run_mod_p_circuit(
        p=UInt384({p[0]}, {p[1]}, {p[2]}, {p[3]}),
        values_ptr=values_arr,
        add_mod_offsets_ptr=add_mod_offsets_arr,
        add_mod_n=1,
        mul_mod_offsets_ptr=add_mod_offsets_arr,
        mul_mod_n=0,
    );
    let range_check96_ptr = range_check96_ptr + 8;
    return ();
}}
"""

    # Valid Computation.
    compile_and_run(
        CODE_FORMAT.format(
            p=[7, 0, 0, 0],
            x1=[3, 0, 0, 0],
        ),
        layout=all_cairo_instance,
        secure_run=True,
    )


def test_add_mod_builtin_runner_addition(builtin_runners):
    add_mod_runner = builtin_runners["add_mod_builtin"]
    check_result(runner=add_mod_runner, inverse_bool=False, p=67, x1=17, x2=40, res=57)
    check_result(runner=add_mod_runner, inverse_bool=False, p=67, x1=82, x2=31, res=46)
    check_result(runner=add_mod_runner, inverse_bool=False, p=67, x1=68, x2=69, res=70)
    check_result(runner=add_mod_runner, inverse_bool=False, p=67, x1=68, x2=0, res=1)

    with pytest.raises(
        AssertionError,
        match="add_mod builtin: Expected a <built-in function add> b - 1 \* p <= 4095.",
    ):
        check_result(
            runner=add_mod_runner, inverse_bool=False, p=67, x1=2**12 - 1, x2=2**12 - 1, res=1
        )


def test_add_mod_builtin_runner_subtraction(builtin_runners):
    add_mod_runner = builtin_runners["add_mod_builtin"]
    check_result(runner=add_mod_runner, inverse_bool=True, p=67, x1=52, x2=38, res=14)
    check_result(runner=add_mod_runner, inverse_bool=True, p=67, x1=5, x2=68, res=4)
    check_result(runner=add_mod_runner, inverse_bool=True, p=67, x1=5, x2=0, res=5)
    check_result(runner=add_mod_runner, inverse_bool=True, p=67, x1=0, x2=5, res=62)
    with pytest.raises(
        AssertionError,
        match=r"add_mod builtin: addend greater than sum \+ p: " + r"[0-9]* > [0-9]* \+ [0-9]*\.",
    ):
        check_result(runner=add_mod_runner, inverse_bool=True, p=67, x1=70, x2=138, res=1)


def test_mul_mod_builtin_runner_multiplication(builtin_runners):
    mul_mod_runner = builtin_runners["mul_mod_builtin"]
    check_result(runner=mul_mod_runner, inverse_bool=False, p=67, x1=11, x2=8, res=21)
    check_result(runner=mul_mod_runner, inverse_bool=False, p=67, x1=68, x2=69, res=2)
    check_result(runner=mul_mod_runner, inverse_bool=False, p=67, x1=525, x2=526, res=1785)
    check_result(runner=mul_mod_runner, inverse_bool=False, p=67, x1=525, x2=0, res=0)
    with pytest.raises(
        AssertionError,
        match=r"mul_mod builtin: Expected a <built-in function mul> b - 4095 \* p <= 4095. "
        + r"Got: values=",
    ):
        check_result(runner=mul_mod_runner, inverse_bool=False, p=67, x1=3777, x2=3989, res=1)


def test_mul_mod_builtin_runner_division(builtin_runners):
    mul_mod_runner = builtin_runners["mul_mod_builtin"]
    check_result(runner=mul_mod_runner, inverse_bool=True, p=67, x1=36, x2=9, res=4)
    check_result(runner=mul_mod_runner, inverse_bool=True, p=67, x1=138, x2=41, res=5)
    check_result(runner=mul_mod_runner, inverse_bool=True, p=67, x1=272, x2=41, res=72)
    with pytest.raises(AssertionError):
        check_result(runner=mul_mod_runner, inverse_bool=True, p=67, x1=0, x2=0, res=0)
    with pytest.raises(AssertionError):
        check_result(runner=mul_mod_runner, inverse_bool=True, p=66, x1=6, x2=3, res=2)
