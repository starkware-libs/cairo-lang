import dataclasses

import pytest

from starkware.cairo.lang.vm.relocatable import RelocatableValue


def test_relocatable_operations():
    x = RelocatableValue(1, 2)
    y = 3
    assert x + y == RelocatableValue(1, 5)
    assert x - y == RelocatableValue(1, -1)
    assert (x + y) - x == y
    assert RelocatableValue(1, 101) % 10 == RelocatableValue(1, 1)

    with pytest.raises(TypeError):
        x * y
    with pytest.raises(AssertionError):
        x + x
    with pytest.raises(AssertionError):
        RelocatableValue(1, 2) - RelocatableValue(2, 2)


def test_relocatable_inequalities():
    x = 3
    y = RelocatableValue(1, 2)
    z = RelocatableValue(3, 0)
    w = RelocatableValue(3, 4)
    assert x < y < z < w
    assert x <= y <= z <= w
    assert w > z > y > x
    assert w >= z >= y >= x
    assert not (y < y)
    assert not (y > y)
    assert not (x > y)
    assert not (x >= y)
    assert not (y < x)
    assert not (y <= x)


@pytest.mark.parametrize('byte_order', ['little', 'big'])
@pytest.mark.parametrize('n_bytes', [16, 32])
def test_relocatable_value_serialization(byte_order, n_bytes):
    for num in [19, RelocatableValue(2, 5)]:
        assert RelocatableValue.from_bytes(
            RelocatableValue.to_bytes(num, n_bytes, byte_order),
            byte_order) == num


def test_to_tuple_from_tuple():
    assert RelocatableValue.to_tuple(5) == (5,)
    assert RelocatableValue.from_tuple((5,)) == 5

    x = RelocatableValue(1, 2)
    assert RelocatableValue.to_tuple(x) == (1, 2)
    assert RelocatableValue.from_tuple((1, 2)) == x


def test_relocatable_value_frozen():
    x = RelocatableValue(1, 2)
    with pytest.raises(
            dataclasses.FrozenInstanceError, match="cannot assign to field 'no_such_field'"):
        x.no_such_field = 5
