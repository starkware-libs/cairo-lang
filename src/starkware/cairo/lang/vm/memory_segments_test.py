from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.memory_segments import MemorySegmentManager, get_segment_used_size
from starkware.cairo.lang.vm.relocatable import RelocatableValue

PRIME = 2**251 + 17 * 2**192 + 1


def test_relocate_segments():
    segments = MemorySegmentManager(memory={}, prime=PRIME)

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
    for i, (size, public_memory) in enumerate(zip(segment_sizes, public_memory_offsets)):
        segments.finalize(i, size=size, public_memory=public_memory)

    segment_offsets = segments.relocate_segments()
    assert segment_offsets == {0: 1, 1: 4, 2: 12, 3: 12, 4: 13}
    assert segments.get_public_memory_addresses(segment_offsets) == [
        (1, 0), (2, 1), (4, 0), (5, 0), (6, 0), (7, 0), (8, 0), (9, 0), (10, 0), (11, 0), (14, 2)]


def test_get_segment_used_size():
    memory = MemoryDict({
        RelocatableValue(0, 0): 0,
        RelocatableValue(0, 2): 0,
        RelocatableValue(1, 5): 0,
        RelocatableValue(1, 7): 0,
        RelocatableValue(3, 0): 0,
        RelocatableValue(4, 1): 0,
    })
    assert [get_segment_used_size(i, memory) for i in range(5)] == [3, 8, 0, 1, 2]


def test_gen_args():
    segments = MemorySegmentManager(memory=MemoryDict({}), prime=PRIME)

    test_array = [2, 3, 7]
    arg = [1, test_array, [4, -1]]
    ptr = segments.gen_arg(arg)

    memory = segments.memory

    assert memory[ptr] == 1
    memory.get_range(memory[ptr + 1], len(test_array)) == test_array
    memory.get_range(memory[ptr + 2], 2) == [4, PRIME - 1]
