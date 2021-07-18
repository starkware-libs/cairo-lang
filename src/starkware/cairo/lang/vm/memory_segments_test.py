import pytest

from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.memory_segments import MemorySegmentManager
from starkware.cairo.lang.vm.relocatable import RelocatableValue

PRIME = 2**251 + 17 * 2**192 + 1


def test_relocate_segments():
    segments = MemorySegmentManager(memory=MemoryDict({}), prime=PRIME)

    for i in range(5):
        assert segments.add() == RelocatableValue(segment_index=i, offset=0)

    segment_sizes = [3, 8, 0, 1, 2]
    public_memory_offsets = [
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
        (1, 0), (2, 1), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (10, 0), (11, 0), (14, 2)]

    # Negative flows.
    segments = MemorySegmentManager(memory=MemoryDict({}), prime=PRIME)
    segments.add(size=1)
    with pytest.raises(AssertionError, match='compute_effective_sizes must be called before'):
        segments.relocate_segments()

    segments.memory[RelocatableValue(0, 2)] = 0
    segments.memory.freeze()
    segments.compute_effective_sizes()
    with pytest.raises(AssertionError, match='Segment 0 exceeded its allocated size'):
        segments.relocate_segments()


def test_get_segment_used_size():
    memory = MemoryDict({
        RelocatableValue(0, 0): 0,
        RelocatableValue(0, 2): 0,
        RelocatableValue(1, 5): 0,
        RelocatableValue(1, 7): 0,
        RelocatableValue(3, 0): 0,
        RelocatableValue(4, 1): 0,
    })
    segments = MemorySegmentManager(memory=memory, prime=PRIME)
    segments.n_segments = 5
    memory.freeze()
    segments.compute_effective_sizes()
    assert [segments.get_segment_used_size(i) for i in range(5)] == [3, 8, 0, 1, 2]


def test_gen_args():
    segments = MemorySegmentManager(memory=MemoryDict({}), prime=PRIME)

    test_array = [2, 3, 7]
    arg = [1, test_array, [4, -1]]
    ptr = segments.gen_arg(arg)

    memory = segments.memory

    assert memory[ptr] == 1
    memory.get_range(memory[ptr + 1], len(test_array)) == test_array
    memory.get_range(memory[ptr + 2], 2) == [4, PRIME - 1]
