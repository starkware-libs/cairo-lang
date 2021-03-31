import pytest

from starkware.cairo.lang.vm.memory_dict import (
    InconsistentMemoryError, MemoryDict, UnknownMemoryError)
from starkware.cairo.lang.vm.relocatable import RelocatableValue


def test_memory_dict_serialize():
    md = MemoryDict({1: 2, 3: 4, 5: 6})
    expected_serialized = bytes([
        1, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 5, 0, 0, 0, 0, 0, 0, 0,
        6, 0, 0])
    serialized = md.serialize(3)
    assert expected_serialized == serialized
    assert MemoryDict.deserialize(serialized, 3) == md


def test_memory_dict_getitem():
    md = MemoryDict({11: 12})
    with pytest.raises(UnknownMemoryError):
        md[12]


def test_memory_dict_check_element():
    md = MemoryDict()
    with pytest.raises(ValueError, match='must be an int'):
        md['not a number'] = 12
    with pytest.raises(ValueError, match='must be nonnegative'):
        md[-12] = 13
    with pytest.raises(ValueError, match='The offset of a relocatable value must be nonnegative'):
        md[RelocatableValue(segment_index=10, offset=-2)] = 13
    # A value may have a negative offset.
    md[13] = RelocatableValue(segment_index=10, offset=-2)


def test_memory_dict_get():
    md = MemoryDict({14: 15})
    assert md.get(14, 'default') == 15
    assert md.get(1234, 'default') == 'default'
    with pytest.raises(ValueError, match='must be nonnegative'):
        md.get(-10, 'default')
    # Attempting to read address with a negative offset is ok, it simply returns None.
    assert md.get(RelocatableValue(segment_index=10, offset=-2)) is None


def test_memory_dict_setdefault():
    md = MemoryDict({14: 15})
    md.setdefault(14, 0)
    assert md[14] == 15
    md.setdefault(123, 456)
    assert md[123] == 456
    with pytest.raises(ValueError, match='must be an int'):
        md.setdefault(10, 'default')
    with pytest.raises(ValueError, match='must be nonnegative'):
        md.setdefault(-10, 123)
    with pytest.raises(ValueError, match='The offset of a relocatable value must be nonnegative'):
        md[RelocatableValue(segment_index=10, offset=-2)] = 13


def test_memory_dict_in():
    md = MemoryDict({1: 2, 3: 4})
    assert 1 in md
    assert 2 not in md
    # Test that `in` doesn't add the value to the dict.
    assert 2 not in md


def test_memory_dict_multiple_values():
    md = MemoryDict({5: 10})
    md[5] = 10
    md[5] = 10
    with pytest.raises(InconsistentMemoryError):
        md[5] = 11
