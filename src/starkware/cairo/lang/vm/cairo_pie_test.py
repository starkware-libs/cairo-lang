import io
import random
from typing import Dict

import pytest

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo
from starkware.cairo.lang.vm.cairo_pie import (
    CairoPie,
    CairoPieMetadata,
    ExecutionResources,
    SegmentInfo,
)
from starkware.cairo.lang.vm.cairo_runner import get_runner_from_code
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.memory_segments import SEGMENT_SIZE_UPPER_BOUND
from starkware.cairo.lang.vm.relocatable import MaybeRelocatableDict, RelocatableValue
from starkware.python.utils import add_counters


def test_cairo_pie_serialize_deserialize():
    program = compile_cairo(
        code=[("%builtins output pedersen range_check ecdsa\nmain:\n[ap] = [ap];\n", "")],
        prime=DEFAULT_PRIME,
    )
    metadata = CairoPieMetadata(
        program=program.stripped(),
        program_segment=SegmentInfo(0, 10),
        execution_segment=SegmentInfo(1, 20),
        ret_fp_segment=SegmentInfo(6, 12),
        ret_pc_segment=SegmentInfo(7, 21),
        builtin_segments={
            "a": SegmentInfo(4, 15),
        },
        extra_segments=[],
    )
    memory: MaybeRelocatableDict = {
        1: 2,
        RelocatableValue(3, 4): RelocatableValue(6, 7),
    }

    additional_data = {"c": ["d", 3]}
    execution_resources = ExecutionResources(
        n_steps=10,
        n_memory_holes=7,
        builtin_instance_counter={
            "output": 6,
            "pedersen": 3,
        },
    )
    cairo_pie = CairoPie(
        metadata=metadata,
        memory=MemoryDict(memory),
        additional_data=additional_data,
        execution_resources=execution_resources,
    )

    fileobj = io.BytesIO()
    cairo_pie.to_file(fileobj)
    actual_cairo_pie = CairoPie.from_file(fileobj)

    assert cairo_pie == actual_cairo_pie


@pytest.fixture
def cairo_pie():
    code = """
%builtins output pedersen

func main(output_ptr: felt*, pedersen_ptr: felt*) -> (output_ptr: felt*, pedersen_ptr: felt*) {
    return (output_ptr=output_ptr, pedersen_ptr=pedersen_ptr);
}
"""
    runner = get_runner_from_code(code=[(code, "")], layout="small", prime=DEFAULT_PRIME)
    return runner.get_cairo_pie()


def test_cairo_pie_validity(cairo_pie):
    cairo_pie.run_validity_checks()


def test_cairo_pie_validity_invalid_program_size(cairo_pie: CairoPie):
    cairo_pie.metadata.program_segment.size += 1
    with pytest.raises(
        AssertionError, match="Program length does not match the program segment size."
    ):
        cairo_pie.run_validity_checks()


def test_cairo_pie_validity_invalid_builtin_list(cairo_pie: CairoPie):
    cairo_pie.program.builtins.append("output")
    with pytest.raises(AssertionError, match="Invalid builtin list."):
        cairo_pie.run_validity_checks()


def test_cairo_pie_validity_invalid_builtin_segments(cairo_pie: CairoPie):
    cairo_pie.metadata.builtin_segments["tmp"] = cairo_pie.metadata.builtin_segments["output"]
    with pytest.raises(AssertionError, match="Builtin list mismatch in builtin_segments."):
        cairo_pie.run_validity_checks()


def test_cairo_pie_validity_invalid_builtin_list_execution_resources(cairo_pie: CairoPie):
    cairo_pie.execution_resources.builtin_instance_counter[
        "tmp_builtin"
    ] = cairo_pie.execution_resources.builtin_instance_counter["output_builtin"]
    with pytest.raises(AssertionError, match="Builtin list mismatch in execution_resources."):
        cairo_pie.run_validity_checks()


def test_cairo_pie_memory_negative_address(cairo_pie: CairoPie):
    # Write to a negative address.
    cairo_pie.memory.set_without_checks(
        RelocatableValue(segment_index=cairo_pie.metadata.program_segment.index, offset=-5), 0
    )
    with pytest.raises(AssertionError, match="Invalid memory cell address."):
        cairo_pie.run_validity_checks()


def test_cairo_pie_memory_invalid_address(cairo_pie: CairoPie):
    # Write to an invalid address.
    cairo_pie.memory.unfreeze_for_testing()
    cairo_pie.memory[
        RelocatableValue(segment_index=cairo_pie.metadata.ret_pc_segment.index, offset=0)
    ] = 0
    with pytest.raises(AssertionError, match="Invalid memory cell address."):
        cairo_pie.run_validity_checks()


def test_cairo_pie_memory_invalid_value(cairo_pie: CairoPie):
    # Write a value after the execution segment.
    output_end = RelocatableValue(
        segment_index=cairo_pie.metadata.execution_segment.index,
        offset=cairo_pie.metadata.execution_segment.size,
    )
    cairo_pie.memory.unfreeze_for_testing()
    cairo_pie.memory[output_end] = output_end + SEGMENT_SIZE_UPPER_BOUND
    # It should fail because the address is outside the segment expected size.
    with pytest.raises(AssertionError, match="Invalid memory cell address."):
        cairo_pie.run_validity_checks()
    # Increase the size.
    cairo_pie.metadata.execution_segment.size += 1
    # Now it should fail because of the value.
    with pytest.raises(AssertionError, match="Invalid memory cell value."):
        cairo_pie.run_validity_checks()


def test_add_execution_resources():
    """
    Tests ExecutionResources.__add__().
    """
    dummy_builtins = ["builtin1", "builtin2", "builtin3", "builtin4"]

    total_execution_resources = ExecutionResources.empty()
    total_builtin_instance_counter: Dict[str, int] = {}
    total_steps = 0

    # Create multiple random ExecutionResources objects, sum them using __ add __() and validate
    # the result.
    random_n_execution_resources = random.randint(2, 10)
    for _ in range(random_n_execution_resources):
        # Create an ExecutionResources object with random values (random builtin_instance_counter
        # and random n_steps).
        random_builtin_instance_counter: Dict[str, int] = {}
        random_n_counters = random.randint(0, 3)
        for _ in range(random_n_counters):
            random_builtin_type = random.choice(dummy_builtins)
            random_builtin_counter = random.randint(0, 10)
            random_builtin_instance_counter[random_builtin_type] = random_builtin_counter
        random_steps = random.randint(0, 1000)
        execution_resources = ExecutionResources(
            n_steps=random_steps,
            builtin_instance_counter=random_builtin_instance_counter,
            n_memory_holes=0,
        )

        # Update totals.
        total_steps += random_steps
        total_builtin_instance_counter = add_counters(
            total_builtin_instance_counter, random_builtin_instance_counter
        )

        # Calculate total_execution_resources using __add__() function.
        total_execution_resources += execution_resources

    assert total_execution_resources.builtin_instance_counter == total_builtin_instance_counter
    assert total_execution_resources.n_steps == total_steps


def test_filter_unused_builtins():
    """
    Tests ExecutionResources.filter_unused_builtins().
    """
    execution_resources1 = ExecutionResources(
        n_steps=17,
        builtin_instance_counter={"builtin1": 1, "builtin2": 2, "builtin3": 1, "builtin4": 4},
        n_memory_holes=5,
    )

    execution_resources2 = ExecutionResources(
        n_steps=17,
        builtin_instance_counter={"builtin1": 1, "builtin2": 2, "builtin3": 3, "builtin4": 4},
        n_memory_holes=5,
    )

    diff = (execution_resources2 - execution_resources1).filter_unused_builtins()

    assert diff.builtin_instance_counter == {"builtin3": 2}
