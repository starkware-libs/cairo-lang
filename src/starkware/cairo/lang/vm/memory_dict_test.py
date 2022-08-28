import pytest

from starkware.cairo.lang.vm.memory_dict import (
    InconsistentMemoryError,
    MemoryDict,
    UnknownMemoryError,
)
from starkware.cairo.lang.vm.relocatable import RelocatableValue


def test_memory_dict_items():
    memory = MemoryDict()
    assert list(memory.items()) == []
    memory = MemoryDict({1: 2, 3: 4, 5: 6})
    assert list(memory.items()) == [(1, 2), (3, 4), (5, 6)]


def test_memory_dict_serialize():
    memory = MemoryDict({1: 2, 3: 4, 5: 6})
    expected_serialized = bytes(
        [
            1,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            2,
            0,
            0,
            3,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            4,
            0,
            0,
            5,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            6,
            0,
            0,
        ]
    )
    serialized = memory.serialize(3)
    assert expected_serialized == serialized
    assert MemoryDict.deserialize(serialized, 3) == memory


def test_memory_dict_getitem():
    memory = MemoryDict({11: 12})
    with pytest.raises(UnknownMemoryError):
        memory[12]


def test_memory_dict_check_element():
    memory = MemoryDict()
    with pytest.raises(KeyError, match="must be an int"):
        memory["not a number"] = 12  # type: ignore
    with pytest.raises(KeyError, match="must be nonnegative"):
        memory[-12] = 13
    with pytest.raises(ValueError, match="must be nonnegative"):
        memory[12] = -13
    with pytest.raises(ValueError, match="The offset of a relocatable value must be nonnegative"):
        memory[RelocatableValue(segment_index=10, offset=-2)] = 13
    # A value may have a negative offset.
    memory[13] = RelocatableValue(segment_index=10, offset=-2)


def test_memory_dict_get():
    DEFAULT = 12345
    memory = MemoryDict({14: 15})
    assert memory.get(14, DEFAULT) == 15
    assert memory.get(1234, DEFAULT) == DEFAULT
    assert memory.get(-10, DEFAULT) == DEFAULT
    # Attempting to read address with a negative offset is ok, it simply returns None.
    assert memory.get(RelocatableValue(segment_index=10, offset=-2)) is None


def test_memory_dict_setdefault():
    memory = MemoryDict({14: 15})
    memory.setdefault(14, 0)
    assert memory[14] == 15
    memory.setdefault(123, 456)
    assert memory[123] == 456
    with pytest.raises(ValueError, match="must be an int"):
        memory.setdefault(10, "default")
    with pytest.raises(KeyError, match="must be nonnegative"):
        memory.setdefault(-10, 123)
    with pytest.raises(ValueError, match="The offset of a relocatable value must be nonnegative"):
        memory[RelocatableValue(segment_index=10, offset=-2)] = 13


def test_memory_dict_in():
    memory = MemoryDict({1: 2, 3: 4})
    assert 1 in memory
    assert 2 not in memory
    # Test that `in` doesn't add the value to the dict.
    assert 2 not in memory


def test_memory_dict_multiple_values():
    memory = MemoryDict({5: 10})
    memory[5] = 10
    memory[5] = 10
    with pytest.raises(InconsistentMemoryError):
        memory[5] = 11


def test_segment_relocations():
    memory = MemoryDict()

    temp_segment = RelocatableValue(segment_index=-1, offset=0)
    memory[5] = temp_segment + 2
    assert memory[5] == RelocatableValue(segment_index=-1, offset=2)
    relocation_target = RelocatableValue(segment_index=4, offset=25)
    memory.add_relocation_rule(src_ptr=temp_segment, dest_ptr=relocation_target)
    assert memory[5] == relocation_target + 2

    memory[temp_segment + 3] = 17
    memory.relocate_memory()
    assert memory.data == {
        5: relocation_target + 2,
        relocation_target + 3: 17,
    }


def test_segment_relocation_failures():
    memory = MemoryDict()

    relocation_target = RelocatableValue(segment_index=4, offset=25)
    with pytest.raises(AssertionError, match="src_ptr.segment_index must be < 0, src_ptr=1:2."):
        memory.add_relocation_rule(
            src_ptr=RelocatableValue(segment_index=1, offset=2), dest_ptr=relocation_target
        )

    with pytest.raises(AssertionError, match="src_ptr.offset must be 0, src_ptr=-3:2."):
        memory.add_relocation_rule(
            src_ptr=RelocatableValue(segment_index=-3, offset=2), dest_ptr=relocation_target
        )

    memory.add_relocation_rule(
        src_ptr=RelocatableValue(segment_index=-3, offset=0), dest_ptr=relocation_target
    )

    with pytest.raises(
        AssertionError, match="The segment with index -3 already has a relocation rule."
    ):
        memory.add_relocation_rule(
            src_ptr=RelocatableValue(segment_index=-3, offset=0), dest_ptr=relocation_target
        )
