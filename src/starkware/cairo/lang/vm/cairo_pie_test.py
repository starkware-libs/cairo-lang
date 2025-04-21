import copy
import io
import random
from dataclasses import field
from typing import ClassVar, Dict, Mapping, Type, no_type_check

import marshmallow
import marshmallow.fields as mfields
import marshmallow_dataclass
import pytest
from pytest import MonkeyPatch

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo
from starkware.cairo.lang.vm.cairo_pie import (
    CairoPie,
    CairoPieMetadata,
    ExecutionResources,
    ExecutionResourcesStone,
    ExecutionResourcesStwo,
    SegmentInfo,
)
from starkware.cairo.lang.vm.cairo_runner import get_runner_from_code
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.memory_segments import SEGMENT_SIZE_UPPER_BOUND
from starkware.cairo.lang.vm.relocatable import (
    MaybeRelocatable,
    MaybeRelocatableDict,
    RelocatableValue,
)
from starkware.python.utils import add_counters
from starkware.starkware_utils.marshmallow_dataclass_fields import additional_metadata


def mock_allow_dummy_builtins(self):
    pass


@marshmallow_dataclass.dataclass
class ExecutionResourcesStoneCopy:
    """
    This class has the same fields as ExecutionResourcesStone. It is used for
    testing the serialization and deserialization of ExecutionResourcesStone
    with a different name.
    """

    n_steps: int
    builtin_instance_counter: Dict[str, int]
    n_memory_holes: int = field(
        metadata=additional_metadata(marshmallow_field=mfields.Integer(load_default=0))
    )
    Schema: ClassVar[Type[marshmallow.Schema]] = marshmallow.Schema


@pytest.mark.parametrize(
    "execution_resources_class", [ExecutionResourcesStone, ExecutionResourcesStoneCopy]
)
def test_cairo_pie_serialize_deserialize(execution_resources_class: Type):
    """
    Tests CairoPie serialization and deserialization. Also checks that changing the class name
    will not affect the serialization/deserialization.
    """
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
    execution_resources = execution_resources_class(
        n_steps=10,
        n_memory_holes=7,
        builtin_instance_counter={
            "output_builtin": 6,
            "pedersen_builtin": 3,
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

    if execution_resources_class == ExecutionResourcesStoneCopy:
        assert isinstance(cairo_pie.execution_resources, ExecutionResourcesStoneCopy)
        assert cairo_pie.execution_resources.n_steps == 10
        assert cairo_pie.execution_resources.builtin_instance_counter == {
            "output_builtin": 6,
            "pedersen_builtin": 3,
        }
        assert cairo_pie.execution_resources.n_memory_holes == 7

        cairo_pie.execution_resources = ExecutionResourcesStone(
            n_steps=10,
            n_memory_holes=7,
            builtin_instance_counter={
                "output_builtin": 6,
                "pedersen_builtin": 3,
            },
        )

    assert cairo_pie == actual_cairo_pie


def test_dump_load_execution_resources():
    """
    Tests that changing the class name of ExecutionResourcesStone will not affect the
    serialization.
    """
    execution_resources = ExecutionResourcesStoneCopy(
        n_steps=10,
        builtin_instance_counter={
            "output_builtin": 6,
            "pedersen_builtin": 3,
        },
        n_memory_holes=7,
    )
    execution_resources_stone = ExecutionResourcesStone(
        n_steps=10,
        builtin_instance_counter={
            "output_builtin": 6,
            "pedersen_builtin": 3,
        },
        n_memory_holes=7,
    )
    dumped = ExecutionResourcesStoneCopy.Schema().dump(execution_resources)
    loaded = ExecutionResourcesStone.Schema().load(dumped)
    assert execution_resources_stone == loaded


def test_dumps_loads_execution_resources():
    execution_resources = ExecutionResourcesStoneCopy(
        n_steps=10,
        builtin_instance_counter={
            "output_builtin": 6,
            "pedersen_builtin": 3,
        },
        n_memory_holes=7,
    )
    execution_resources_stone = ExecutionResourcesStone(
        n_steps=10,
        builtin_instance_counter={
            "output_builtin": 6,
            "pedersen_builtin": 3,
        },
        n_memory_holes=7,
    )
    dumped = ExecutionResourcesStoneCopy.Schema().dumps(execution_resources)
    loaded = ExecutionResourcesStone.Schema().loads(dumped)
    assert execution_resources_stone == loaded


def test_dump_load_stone_execution_resources():
    execution_resources_stone = ExecutionResourcesStone(
        n_steps=10,
        builtin_instance_counter={
            "output_builtin": 6,
            "pedersen_builtin": 3,
        },
        n_memory_holes=7,
    )
    dumped = ExecutionResourcesStone.Schema().dump(execution_resources_stone)
    loaded = ExecutionResources.Schema().load(dumped)
    assert isinstance(loaded, ExecutionResourcesStone)
    assert loaded.n_steps == execution_resources_stone.n_steps
    assert loaded.builtin_instance_counter == execution_resources_stone.builtin_instance_counter
    assert loaded.n_memory_holes == execution_resources_stone.n_memory_holes


def test_dumps_loads_stone_execution_resources():
    execution_resources_stone = ExecutionResourcesStone(
        n_steps=10,
        builtin_instance_counter={
            "output_builtin": 6,
            "pedersen_builtin": 3,
        },
        n_memory_holes=7,
    )
    dumped = ExecutionResourcesStone.Schema().dumps(execution_resources_stone)
    loaded = ExecutionResources.Schema().loads(dumped)
    assert isinstance(loaded, ExecutionResourcesStone)
    assert loaded.n_steps == execution_resources_stone.n_steps
    assert loaded.builtin_instance_counter == execution_resources_stone.builtin_instance_counter
    assert loaded.n_memory_holes == execution_resources_stone.n_memory_holes


def test_dump_load_stwo_execution_resources():
    execution_resources_stwo = ExecutionResourcesStwo(
        builtin_instance_counter={
            "output_builtin": 6,
            "pedersen_builtin": 3,
        },
        opcodes_instance_counter={
            "opcode1": 1,
            "opcode2": 2,
        },
        memory_tables_sizes={
            "table1": 10,
            "table2": 20,
        },
        n_memory_holes=12,
        n_verify_instructions=5,
    )
    dumped = ExecutionResources.Schema().dump(execution_resources_stwo)
    loaded = ExecutionResources.Schema().load(dumped)
    assert isinstance(loaded, ExecutionResourcesStwo)
    assert loaded.builtin_instance_counter == execution_resources_stwo.builtin_instance_counter
    assert loaded.opcodes_instance_counter == execution_resources_stwo.opcodes_instance_counter
    assert loaded.memory_tables_sizes == execution_resources_stwo.memory_tables_sizes
    assert loaded.n_memory_holes == execution_resources_stwo.n_memory_holes
    assert loaded.n_verify_instructions == execution_resources_stwo.n_verify_instructions


def test_dumps_loads_stwo_execution_resources():
    execution_resources_stwo = ExecutionResourcesStwo(
        builtin_instance_counter={
            "output_builtin": 6,
            "pedersen_builtin": 3,
        },
        opcodes_instance_counter={
            "opcode1": 1,
            "opcode2": 2,
        },
        memory_tables_sizes={
            "table1": 10,
            "table2": 20,
        },
        n_memory_holes=12,
        n_verify_instructions=5,
    )
    dumped = ExecutionResources.Schema().dumps(execution_resources_stwo)
    loaded = ExecutionResources.Schema().loads(dumped)
    assert isinstance(loaded, ExecutionResourcesStwo)
    assert loaded.builtin_instance_counter == execution_resources_stwo.builtin_instance_counter
    assert loaded.opcodes_instance_counter == execution_resources_stwo.opcodes_instance_counter
    assert loaded.memory_tables_sizes == execution_resources_stwo.memory_tables_sizes
    assert loaded.n_memory_holes == execution_resources_stwo.n_memory_holes
    assert loaded.n_verify_instructions == execution_resources_stwo.n_verify_instructions


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


def test_n_steps_execution_resources_stwo(monkeypatch: MonkeyPatch):
    """
    Test that the property n_steps of ExecutionResourcesStwo is calculated correctly.
    """
    monkeypatch.setattr(ExecutionResourcesStwo, "__post_init__", mock_allow_dummy_builtins)

    opcodes_instance_counter = {"ret": 7, "add_ap": 6, "jmp_rel_imm": 5, "jmp_abs": 4}

    execution_resources = ExecutionResourcesStwo(
        builtin_instance_counter={"builtin1": 1},
        opcodes_instance_counter=opcodes_instance_counter,
        memory_tables_sizes={"table1": 10, "table2": 20},
        n_memory_holes=5,
        n_verify_instructions=3,
    )

    # Calculate the expected n_steps.
    expected_n_steps = 0
    for _, counter in opcodes_instance_counter.items():
        expected_n_steps += counter

    assert execution_resources.n_steps == expected_n_steps


def test_add_execution_resources_stone(monkeypatch: MonkeyPatch):
    """
    Tests ExecutionResourcesStone.__add__().
    """
    monkeypatch.setattr(ExecutionResourcesStwo, "__post_init__", mock_allow_dummy_builtins)

    dummy_builtins = ["builtin1", "builtin2", "builtin3", "builtin4"]

    total_execution_resources = ExecutionResourcesStone.empty()
    total_builtin_instance_counter: Dict[str, int] = {}
    total_steps = 0

    # Create multiple random ExecutionResourcesStone objects, sum them using
    # __ add __() and validate the result.
    random_n_execution_resources = random.randint(2, 10)
    for _ in range(random_n_execution_resources):
        # Create an ExecutionResourcesStone object with random values (random
        # builtin_instance_counter and random n_steps).
        random_builtin_instance_counter: Dict[str, int] = {}
        random_n_counters = random.randint(0, 3)
        for _ in range(random_n_counters):
            random_builtin_type = random.choice(dummy_builtins)
            random_builtin_counter = random.randint(0, 10)
            random_builtin_instance_counter[random_builtin_type] = random_builtin_counter
        random_steps = random.randint(0, 1000)
        execution_resources = ExecutionResourcesStone(
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


def test_add_execution_resources_stwo(monkeypatch: MonkeyPatch):
    """
    Tests ExecutionResourcesStwo.__add__().
    """
    monkeypatch.setattr(ExecutionResourcesStwo, "__post_init__", mock_allow_dummy_builtins)

    dummy_builtins = ["builtin1", "builtin2", "builtin3", "builtin4"]
    dummy_opcodes = ["opcode1", "opcode2", "opcode3", "opcode4"]
    dummy_memory_tables = ["table1", "table2", "table3", "table4"]

    total_execution_resources = ExecutionResourcesStwo.empty()
    total_builtin_instance_counter: Dict[str, int] = {}
    total_memory_tables_sizes: Dict[str, int] = {}

    # Create multiple random ExecutionResourcesStwo objects, sum them using
    # __ add __() and validate the result.
    random_n_execution_resources = random.randint(2, 10)
    for _ in range(random_n_execution_resources):
        # Create an ExecutionResourcesStwo object with random values (random
        # builtin_instance_counter and random n_steps).
        random_builtin_instance_counter: Dict[str, int] = {}
        random_n_counters = random.randint(0, 3)
        for _ in range(random_n_counters):
            random_builtin_type = random.choice(dummy_builtins)
            random_builtin_counter = random.randint(0, 10)
            random_builtin_instance_counter[random_builtin_type] = random_builtin_counter
        random_n_opcodes = random.randint(0, 3)
        random_opcode_counter: Dict[str, int] = {}
        for _ in range(random_n_opcodes):
            random_opcode = random.choice(dummy_opcodes)
            random_opcode_counter[random_opcode] = random.randint(0, 10)
        random_n_memory_tables = random.randint(0, 3)
        random_memory_tables_sizes: Dict[str, int] = {}
        for _ in range(random_n_memory_tables):
            random_memory_table = random.choice(dummy_memory_tables)
            random_memory_tables_sizes[random_memory_table] = random.randint(0, 10)

        execution_resources = ExecutionResourcesStwo(
            builtin_instance_counter=random_builtin_instance_counter,
            opcodes_instance_counter=random_opcode_counter,
            memory_tables_sizes=random_memory_tables_sizes,
            n_memory_holes=1,
            n_verify_instructions=1,
        )

        # Update totals.
        total_builtin_instance_counter = add_counters(
            total_builtin_instance_counter, random_builtin_instance_counter
        )
        total_opcode_counter = add_counters(
            total_execution_resources.opcodes_instance_counter, random_opcode_counter
        )
        total_memory_tables_sizes = add_counters(
            total_memory_tables_sizes, random_memory_tables_sizes
        )

        # Calculate total_execution_resources using __add__() function.
        total_execution_resources += execution_resources

    assert total_execution_resources.builtin_instance_counter == total_builtin_instance_counter
    assert total_execution_resources.opcodes_instance_counter == total_opcode_counter
    assert total_execution_resources.memory_tables_sizes == total_memory_tables_sizes
    assert total_execution_resources.n_memory_holes == random_n_execution_resources
    assert total_execution_resources.n_verify_instructions == random_n_execution_resources


def test_sub_execution_resources_stwo(monkeypatch: MonkeyPatch):
    """
    Tests ExecutionResourcesStwo.__sub__().
    """
    monkeypatch.setattr(ExecutionResourcesStwo, "__post_init__", mock_allow_dummy_builtins)

    execution_resources1 = ExecutionResourcesStwo(
        builtin_instance_counter={"builtin1": 1, "builtin2": 2, "builtin3": 1, "builtin4": 4},
        opcodes_instance_counter={"opcode1": 1, "opcode2": 2, "opcode3": 1, "opcode4": 4},
        memory_tables_sizes={"table1": 1, "table2": 2, "table3": 3, "table4": 4},
        n_memory_holes=5,
        n_verify_instructions=10,
    )

    execution_resources2 = ExecutionResourcesStwo(
        builtin_instance_counter={"builtin1": 1, "builtin2": 2, "builtin3": 3, "builtin4": 4},
        opcodes_instance_counter={"opcode1": 1, "opcode2": 2, "opcode3": 3, "opcode4": 4},
        memory_tables_sizes={"table1": 10, "table2": 20, "table3": 30, "table4": 40},
        n_memory_holes=15,
        n_verify_instructions=10,
    )

    diff = execution_resources2 - execution_resources1

    assert isinstance(diff, ExecutionResourcesStwo)
    assert diff.builtin_instance_counter == {
        "builtin1": 0,
        "builtin2": 0,
        "builtin3": 2,
        "builtin4": 0,
    }
    assert diff.opcodes_instance_counter == {"opcode1": 0, "opcode2": 0, "opcode3": 2, "opcode4": 0}
    assert diff.memory_tables_sizes == {"table1": 9, "table2": 18, "table3": 27, "table4": 36}
    assert diff.n_memory_holes == 10
    assert diff.n_verify_instructions == 0


def test_filter_unused_builtins(monkeypatch: MonkeyPatch):
    """
    Tests ExecutionResourcesStone.filter_unused_builtins().
    """
    monkeypatch.setattr(ExecutionResourcesStwo, "__post_init__", mock_allow_dummy_builtins)

    execution_resources1 = ExecutionResourcesStone(
        n_steps=17,
        builtin_instance_counter={"builtin1": 1, "builtin2": 2, "builtin3": 1, "builtin4": 4},
        n_memory_holes=5,
    )

    execution_resources2 = ExecutionResourcesStone(
        n_steps=17,
        builtin_instance_counter={"builtin1": 1, "builtin2": 2, "builtin3": 3, "builtin4": 4},
        n_memory_holes=5,
    )

    stone_diff = (execution_resources2 - execution_resources1).filter_unused_builtins()

    assert stone_diff.builtin_instance_counter == {"builtin3": 2}

    execution_resources3 = ExecutionResourcesStwo(
        builtin_instance_counter={"builtin1": 1, "builtin2": 2, "builtin3": 1, "builtin4": 4},
        opcodes_instance_counter={"opcode1": 1, "opcode2": 2, "opcode3": 1, "opcode4": 4},
        memory_tables_sizes={"table1": 1, "table2": 2, "table3": 3, "table4": 4},
        n_memory_holes=5,
        n_verify_instructions=10,
    )

    execution_resources4 = ExecutionResourcesStwo(
        builtin_instance_counter={"builtin1": 1, "builtin2": 2, "builtin3": 3, "builtin4": 4},
        opcodes_instance_counter={"opcode1": 1, "opcode2": 2, "opcode3": 3, "opcode4": 4},
        memory_tables_sizes={"table1": 1, "table2": 2, "table3": 3, "table4": 4},
        n_memory_holes=5,
        n_verify_instructions=10,
    )

    stwo_diff = (execution_resources4 - execution_resources3).filter_unused_builtins()

    assert stwo_diff.builtin_instance_counter == {"builtin3": 2}


def test_cairo_pie_merge_extra_segments(cairo_pie: CairoPie):
    """
    Tests to_file when merge_extra_segments parameter is True.
    """
    cairo_pie.metadata.extra_segments = [SegmentInfo(8, 10), SegmentInfo(9, 20)]
    initializer: Mapping[MaybeRelocatable, MaybeRelocatable] = {
        1: 2,
        RelocatableValue(3, 4): RelocatableValue(6, 7),
        RelocatableValue(8, 0): RelocatableValue(8, 4),
        RelocatableValue(9, 3): RelocatableValue(9, 7),
    }
    cairo_pie.memory = MemoryDict(initializer)

    fileobj = io.BytesIO()
    cairo_pie.to_file(fileobj, merge_extra_segments=True)
    actual_cairo_pie = CairoPie.from_file(fileobj)

    assert actual_cairo_pie.metadata.extra_segments == [SegmentInfo(8, 30)]

    expected_memory_initializer: Mapping[MaybeRelocatable, MaybeRelocatable] = {
        1: 2,
        RelocatableValue(3, 4): RelocatableValue(6, 7),
        RelocatableValue(8, 0): RelocatableValue(8, 4),
        RelocatableValue(8, 13): RelocatableValue(8, 17),
    }
    assert actual_cairo_pie.memory == MemoryDict(expected_memory_initializer)


@pytest.mark.parametrize(
    "has_pedersen1,has_pedersen2,are_compatible",
    [
        (True, True, True),
        (True, True, False),
        (True, False, True),
        (True, False, False),
        (False, False, True),
        (False, False, False),
    ],
)
def test_cairo_pie_is_compatible_with(
    cairo_pie: CairoPie,
    has_pedersen1: bool,
    has_pedersen2: bool,
    are_compatible: bool,
):
    """
    Tests CairoPie.is_compatible_with().
    """
    cairo_pie.additional_data = {}
    another_cairo_pie = copy.deepcopy(cairo_pie)
    if has_pedersen1:
        cairo_pie.additional_data["pedersen_builtin"] = 1
    if has_pedersen2:
        another_cairo_pie.additional_data["pedersen_builtin"] = 2
    if not are_compatible:
        cairo_pie.additional_data["test"] = 1
        another_cairo_pie.additional_data["test"] = 2
    assert cairo_pie.is_compatible_with(another_cairo_pie) == are_compatible
    assert another_cairo_pie.is_compatible_with(cairo_pie) == are_compatible


@no_type_check
def test_cairo_pie_diff():
    cairo_pie = CairoPie(
        metadata=1,
        memory=1,
        additional_data={"a": 1, "b": 2, "c": 3},
        execution_resources=1,
        version=1,
    )
    another_cairo_pie = CairoPie(
        metadata=2,
        memory=2,
        additional_data={"b": 2, "c": 4, "d": 5},
        execution_resources=2,
        version=2,
    )
    assert (
        cairo_pie.diff(another_cairo_pie)
        == """CairoPie diff:
 * metadata mismatch.
 * memory mismatch.
 * additional_data mismatch:
   * a mismatch.
   * c mismatch.
   * d mismatch.
 * execution_resources mismatch: 1 != 2.
 * version mismatch: 1 != 2."""
    )


def test_equivalent_stone_version():
    """
    Tests that ExecutionResourcesStwo.convert_to_stone()
    returns the correct value.
    """
    execution_resources_stone = ExecutionResourcesStone(
        n_steps=10,
        builtin_instance_counter={
            "output_builtin": 6,
            "pedersen_builtin": 3,
        },
        n_memory_holes=12,
    )

    execution_resources_stwo = ExecutionResourcesStwo(
        builtin_instance_counter={
            "output_builtin": 6,
            "pedersen_builtin": 3,
        },
        opcodes_instance_counter={
            "opcode1": 7,
            "opcode2": 3,
        },
        memory_tables_sizes={
            "table1": 10,
            "table2": 20,
        },
        n_verify_instructions=5,
        n_memory_holes=12,
    )

    assert execution_resources_stwo.convert_to_stone() == execution_resources_stone


def test_equivalent_stwo_version():
    """
    Tests that ExecutionResourcesStone.convert_to_stwo()
    returns the correct value.
    """
    execution_resources_stone = ExecutionResourcesStone(
        n_steps=10,
        builtin_instance_counter={
            "output_builtin": 6,
            "pedersen_builtin": 3,
        },
        n_memory_holes=12,
    )

    execution_resources_stwo = ExecutionResourcesStwo(
        builtin_instance_counter={
            "output_builtin": 6,
            "pedersen_builtin": 3,
        },
        opcodes_instance_counter={
            "generic_opcode": 10,
        },
        memory_tables_sizes={},
        n_verify_instructions=0,
        n_memory_holes=12,
    )

    assert execution_resources_stone.convert_to_stwo() == execution_resources_stwo
    assert (
        execution_resources_stone.convert_to_stwo().convert_to_stone() == execution_resources_stone
    )
