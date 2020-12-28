from random import randint

import pytest

from starkware.cairo.lang.compiler.instruction import (
    N_FLAGS, OFFSET_BITS, decode_instruction_values)


def test_decode():
    offsets = [randint(0, 2**OFFSET_BITS) for _ in range(3)]
    flags = randint(0, 2**N_FLAGS)
    instruction = 0
    for part in [flags] + offsets[::-1]:
        instruction = (instruction << OFFSET_BITS) | part
    assert [flags] + offsets == list(decode_instruction_values(instruction))


def test_unsupported_instruction():
    with pytest.raises(AssertionError, match='Unsupported instruction.'):
        decode_instruction_values(1 << (3 * OFFSET_BITS + N_FLAGS))
