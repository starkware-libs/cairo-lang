from typing import cast

import pytest

from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.relocatable import RelocatableValue
from starkware.cairo.lang.vm.validated_memory_dict import ValidatedMemoryDict, ValidationRule


def test_validated_memory_dict():
    memory = MemoryDict()
    prime = 23
    memory_validator = ValidatedMemoryDict(memory=memory, prime=prime)

    def rule_identical_pairs(mem, addr):
        """
        Validates that the values in address pairs (i, i+1), where i is even, are identical.
        """
        offset_diff = (-1) ** (addr.offset % 2)
        other_addr = RelocatableValue.from_tuple((addr.segment_index, addr.offset + offset_diff))
        if other_addr in mem:
            assert mem[addr] == mem[other_addr]
            return {addr, other_addr}
        return set()

    def rule_constant_value(mem, addr, constant):
        assert (
            mem[addr] == constant
        ), f"Expected value in address {addr} to be {constant}, got {mem[addr]}."
        return {addr}

    memory_validator.add_validation_rule(1, lambda memory, addr: set())
    memory_validator.add_validation_rule(2, lambda memory, addr: {addr})
    memory_validator.add_validation_rule(3, rule_identical_pairs)
    memory_validator.add_validation_rule(4, cast(ValidationRule, rule_constant_value), 0)

    addr0 = RelocatableValue.from_tuple((1, 0))
    addr1 = RelocatableValue.from_tuple((2, 0))
    addr2 = RelocatableValue.from_tuple((3, 0))
    addr3 = RelocatableValue.from_tuple((3, 1))
    addr4 = RelocatableValue.from_tuple((4, 0))

    # Test validated_addresses update.
    memory_validator[addr0] = 0
    assert memory_validator._ValidatedMemoryDict__validated_addresses == set()
    memory_validator[addr1] = 0
    assert memory_validator._ValidatedMemoryDict__validated_addresses == {addr1}
    # Test validation rule application.
    memory_validator[addr2] = 1
    assert memory_validator._ValidatedMemoryDict__validated_addresses == {addr1}
    memory_validator[addr3] = 1
    assert memory_validator._ValidatedMemoryDict__validated_addresses == {addr1, addr2, addr3}

    # Test validation of existing valid memory.
    assert len(memory_validator) > 0
    memory_validator.validate_existing_memory()

    # Invalidate existing memory and test negative case.
    with pytest.raises(AssertionError, match="Expected value in address 4:0 to be 0, got 1."):
        memory_validator[addr4] = 1

    # Test validation of existing invalid memory.
    with pytest.raises(AssertionError, match="Expected value in address 4:0 to be 0, got 1."):
        memory_validator.validate_existing_memory()

    # Test insertion of a value bigger than prime.
    memory_validator[7] = prime + 2
    assert memory_validator[7] == 2
