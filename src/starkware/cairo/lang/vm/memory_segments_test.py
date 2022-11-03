from typing import List, Set, Tuple

import pytest

from starkware.cairo.common.structs import CairoStructFactory
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.memory_segments import MemorySegmentManager
from starkware.cairo.lang.vm.relocatable import (
    MaybeRelocatable,
    MaybeRelocatableDict,
    RelocatableValue,
)


def test_relocate_segments():
    segments = MemorySegmentManager(memory=MemoryDict({}), prime=DEFAULT_PRIME)

    for i in range(5):
        assert segments.add() == RelocatableValue(segment_index=i, offset=0)

    segment_sizes = [3, 8, 0, 1, 2]
    public_memory_offsets: List[List[Tuple[int, int]]] = [
        [(0, 0), (1, 1)],
        [(i, 0) for i in range(8)],
        [],
        [],
        [(1, 2)],
    ]

    # These segments are not finalized.
    assert segments.add() == RelocatableValue(segment_index=5, offset=0)
    assert segments.add() == RelocatableValue(segment_index=6, offset=0)
    segments.memory[RelocatableValue(5, 4)] = 0

    segments.memory.freeze()
    segments.compute_effective_sizes()
    for i, (size, public_memory) in enumerate(zip(segment_sizes, public_memory_offsets)):
        segments.finalize(i, size=size, public_memory=public_memory)

    segment_offsets = segments.relocate_segments()
    assert segment_offsets == {0: 1, 1: 4, 2: 12, 3: 12, 4: 13, 5: 15, 6: 20}
    assert segments.get_public_memory_addresses(segment_offsets) == [
        (1, 0),
        (2, 1),
        (4, 0),
        (5, 0),
        (6, 0),
        (7, 0),
        (8, 0),
        (9, 0),
        (10, 0),
        (11, 0),
        (14, 2),
    ]

    # Negative flows.
    segments = MemorySegmentManager(memory=MemoryDict({}), prime=DEFAULT_PRIME)
    segments.add(size=1)
    with pytest.raises(AssertionError, match="compute_effective_sizes must be called before"):
        segments.relocate_segments()

    segments.memory[RelocatableValue(0, 2)] = 0
    segments.memory.freeze()
    segments.compute_effective_sizes()
    with pytest.raises(AssertionError, match="Segment 0 exceeded its allocated size"):
        segments.relocate_segments()


def test_get_segment_used_size():
    memory_data: MaybeRelocatableDict = {
        RelocatableValue(0, 0): 0,
        RelocatableValue(0, 2): 0,
        RelocatableValue(1, 5): 0,
        RelocatableValue(1, 7): 0,
        RelocatableValue(3, 0): 0,
        RelocatableValue(4, 1): 0,
    }
    memory = MemoryDict(memory_data)
    segments = MemorySegmentManager(memory=memory, prime=DEFAULT_PRIME)
    segments.n_segments = 5
    memory.freeze()
    segments.compute_effective_sizes()
    assert [segments.get_segment_used_size(i) for i in range(5)] == [3, 8, 0, 1, 2]


def test_gen_args():
    segments = MemorySegmentManager(memory=MemoryDict({}), prime=DEFAULT_PRIME)

    test_array = [2, 3, 7]
    arg = [1, test_array, [4, -1]]
    ptr = segments.gen_arg(arg)

    memory = segments.memory

    assert memory[ptr] == 1
    memory.get_range(memory[ptr + 1], len(test_array)) == test_array
    memory.get_range(memory[ptr + 2], 2) == [4, DEFAULT_PRIME - 1]


def test_get_memory_holes():
    segments = MemorySegmentManager(memory=MemoryDict({}), prime=DEFAULT_PRIME)
    seg0 = segments.add(size=10)
    seg1 = segments.add()

    accessed_addresses: Set[MaybeRelocatable] = {seg0, seg1, seg0 + 1, seg1 + 5}
    # Since segment 1 has no specified size, we must set a memory entry directly.
    segments.memory[seg1 + 5] = 0

    segments.memory.relocate_memory()
    segments.memory.freeze()
    segments.compute_effective_sizes()
    seg0_holes = 10 - 2
    seg1_holes = 6 - 2
    assert segments.get_memory_holes(accessed_addresses) == seg0_holes + seg1_holes


def test_gen_typed_args():
    """
    Tests gen_typed_args.
    """

    code = """
struct Inner {
    a: felt,
    b: felt,
}

struct MyStruct {
    nested: Inner,
    ptr: Inner*,
}
"""

    program = compile_cairo(code=code, prime=DEFAULT_PRIME)

    structs = CairoStructFactory.from_program(program=program).structs
    my_struct = structs.MyStruct
    inner = structs.Inner

    typed_args = my_struct(nested=inner(a=1, b=7), ptr=inner(a=3, b=4))

    segments = MemorySegmentManager(memory=MemoryDict({}), prime=DEFAULT_PRIME)
    cairo_arg = segments.gen_typed_args(args=typed_args)

    assert len(cairo_arg) == 3
    assert cairo_arg[:2] == [1, 7]
    assert segments.memory.get_range(addr=cairo_arg[2], size=2) == [3, 4]
