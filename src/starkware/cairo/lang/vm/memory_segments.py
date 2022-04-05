from collections import defaultdict
from typing import Dict, Iterable, List, NamedTuple, Optional, Sequence, Set, Tuple

from starkware.cairo.lang.compiler.ast.cairo_types import TypeFelt, TypePointer, TypeStruct
from starkware.cairo.lang.vm.memory_dict import MemoryDict
from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue
from starkware.cairo.lang.vm.vm_exceptions import SecurityError

FIRST_MEMORY_ADDR = 1
SEGMENT_SIZE_UPPER_BOUND = 2 ** 64


class MemorySegmentManager:
    """
    Manages the list of memory segments, and allows relocating them once their sizes are known.
    """

    def __init__(self, memory: MemoryDict, prime: int):
        self.memory = memory
        self.prime = prime
        # Number of segments.
        self.n_segments = 0
        # A map from segment index to its size.
        self._segment_sizes: Dict[int, int] = {}
        self._segment_used_sizes: Optional[Dict[int, int]] = None
        # A map from segment index to a list of pairs (offset, page_id) that constitute the
        # public memory. Note that the offset is absolute (not based on the page_id).
        self.public_memory_offsets: Dict[int, List[Tuple[int, int]]] = {}
        # The number of temporary segments, see 'add_temp_segment' for more details.
        self.n_temp_segments = 0

    def add(self, size: Optional[int] = None) -> RelocatableValue:
        """
        Adds a new segment and returns its starting location as a RelocatableValue.
        If size is not None the segment is finalized with the given size.
        """
        segment_index = self.n_segments
        self.n_segments += 1
        if size is not None:
            self.finalize(segment_index=segment_index, size=size)

        return RelocatableValue(segment_index=segment_index, offset=0)

    def add_temp_segment(self) -> RelocatableValue:
        """
        Adds a new temporary segment and returns its starting location as a RelocatableValue.

        A temporary segment is a segment that is relocated using memory.add_relocation_rule()
        before the Cairo PIE is produced.
        """

        self.n_temp_segments += 1
        # Temporary segments have negative segment indices that start from -1.
        segment_index = -self.n_temp_segments

        return RelocatableValue(segment_index=segment_index, offset=0)

    def finalize(
        self,
        segment_index: int,
        size: Optional[int] = None,
        public_memory: Sequence[Tuple[int, int]] = [],
    ):
        """
        Writes the following information for the given segment:
        * size - The size of the segment (to be used in relocate_segments).
        * public_memory - A list of offsets for memory cells that will be considered as public
        memory.
        """
        if size is not None:
            self._segment_sizes[segment_index] = size

        self.public_memory_offsets[segment_index] = list(public_memory)

    def compute_effective_sizes(self, include_tmp_segments: bool = False):
        """
        Computes the current used size of the segments, and caches it.
        include_tmp_segments should be used for tests only.
        """
        if self._segment_used_sizes is not None:
            # segment_sizes is already cached.
            return

        assert self.memory.is_frozen(), "Memory has to be frozen before calculating effective size."

        first_segment_index = -self.n_temp_segments if include_tmp_segments else 0
        self._segment_used_sizes = {
            index: 0 for index in range(first_segment_index, self.n_segments)
        }
        for addr in self.memory:
            if not isinstance(addr, RelocatableValue):
                raise SecurityError(
                    f"Expected memory address to be relocatable value. Found: {addr}."
                )

            previous_max_size = self._segment_used_sizes[addr.segment_index]
            self._segment_used_sizes[addr.segment_index] = max(previous_max_size, addr.offset + 1)

    def relocate_segments(self) -> Dict[int, int]:
        current_addr = FIRST_MEMORY_ADDR
        res = {}

        assert (
            self._segment_used_sizes is not None
        ), "compute_effective_sizes must be called before relocate_segments."

        for segment_index, used_size in self._segment_used_sizes.items():
            res[segment_index] = current_addr
            size = self.get_segment_size(segment_index=segment_index)
            assert size >= used_size, f"Segment {segment_index} exceeded its allocated size."
            current_addr += size
        return res

    def get_public_memory_addresses(self, segment_offsets: Dict[int, int]) -> List[Tuple[int, int]]:
        """
        Returns a list of addresses of memory cells that constitute the public memory.
        segment_offsets should be the dictionary returned by relocate_segments().
        """
        res = []
        for segment_index in range(self.n_segments):
            offsets = self.public_memory_offsets.get(segment_index, [])
            segment_start = segment_offsets[segment_index]
            for offset, page_id in offsets:
                res.append((segment_start + offset, page_id))
        return res

    def initialize_segments_from(self, other: "MemorySegmentManager"):
        """
        Adds the segments used by the given MemorySegmentManager.
        Note that this function must be called before any segments are added, to make the segment
        indices identical.
        """
        assert (
            self.n_segments == 0
        ), "initialize_segments_from() must be called before segments are added."
        self.n_segments = other.n_segments

    def load_data(
        self, ptr: MaybeRelocatable, data: Sequence[MaybeRelocatable]
    ) -> MaybeRelocatable:
        """
        Writes data into the memory at address ptr and returns the first address after the data.
        """
        for i, v in enumerate(data):
            self.memory[ptr + i] = v
        return ptr + len(data)

    def gen_arg(self, arg, apply_modulo_to_args=True) -> MaybeRelocatable:
        """
        Converts args to Cairo-friendly ones.
        If an argument is Iterable it is replaced by a pointer to a new segment containing the items
        in the Iterable arg (recursively).
        If apply_modulo_to_args=True, all the integers are taken modulo the program's prime.
        """
        if isinstance(arg, Iterable):
            base = self.add()
            self.write_arg(base, arg)
            return base
        if apply_modulo_to_args and isinstance(arg, int):
            return arg % self.prime
        return arg

    def gen_typed_args(self, args: NamedTuple) -> List[MaybeRelocatable]:
        """
        Takes a Cairo typed NamedTuple generated with CairoStructFactory and
        returns a Cairo-friendly argument list.
        """
        cairo_args = []
        for value, field_type in zip(args, args.__annotations__.values()):
            if field_type is TypePointer or field_type is TypeFelt:
                # Pointer or felt.
                cairo_args.append(self.gen_arg(arg=value))
            elif field_type is TypeStruct:
                # Struct.
                cairo_args += self.gen_typed_args(args=value)
            else:
                raise NotImplementedError(f"{field_type.__name__} is not supported.")

        return cairo_args

    def write_arg(self, ptr, arg, apply_modulo_to_args=True):
        assert isinstance(arg, Iterable)
        data = [self.gen_arg(arg=x, apply_modulo_to_args=apply_modulo_to_args) for x in arg]
        return self.load_data(ptr, data)

    def get_memory_holes(self, accessed_addresses: Set[MaybeRelocatable]) -> int:
        """
        Returns the total number of memory holes in all segments.
        """
        # A map from segment index to the set of accessed offsets.
        accessed_offsets_sets: Dict[int, Set] = defaultdict(set)
        for addr in accessed_addresses:
            assert isinstance(
                addr, RelocatableValue
            ), f"Expected memory address to be relocatable value. Found: {addr}."
            index, offset = addr.segment_index, addr.offset
            assert offset >= 0, f"Address offsets must be non-negative. Found: {offset}."
            assert offset <= self.get_segment_size(segment_index=index), (
                f"Accessed address {addr} has higher offset than the maximal offset "
                f"{self.get_segment_size(segment_index=index)} encountered in the memory segment."
            )
            accessed_offsets_sets[index].add(offset)

        assert (
            self._segment_used_sizes is not None
        ), "compute_effective_sizes must be called before get_memory_holes."
        return sum(
            self.get_segment_size(segment_index=index) - len(accessed_offsets_sets[index])
            for index in self._segment_sizes.keys() | self._segment_used_sizes.keys()
        )

    def get_segment_used_size(self, segment_index: int) -> int:
        assert (
            self._segment_used_sizes is not None
        ), "compute_effective_sizes must be called before get_segment_used_size."

        return self._segment_used_sizes[segment_index]

    def get_segment_size(self, segment_index: int) -> int:
        """
        Returns the finalized size of the given segment. If the segment has not been finalized,
        returns its used size.
        """
        return (
            self._segment_sizes[segment_index]
            if segment_index in self._segment_sizes
            else self.get_segment_used_size(segment_index=segment_index)
        )

    def is_valid_memory_value(self, value: MaybeRelocatable) -> bool:
        assert (
            self._segment_used_sizes is not None
        ), "compute_effective_sizes must be called before is_valid_memory_value."

        return is_valid_memory_value(value=value, segment_sizes=self._segment_used_sizes)


def is_valid_memory_addr(
    addr: MaybeRelocatable, segment_sizes: Dict[int, int], is_concrete_address: bool = True
):
    """
    Returns True if addr is a relocatable value, such that its segment index appears in
    segment_sizes and its offset is in the valid range (if is_concrete_address=False, offset
    may exceed the segment size).
    """
    return (
        isinstance(addr, RelocatableValue)
        and isinstance(addr.segment_index, int)
        and isinstance(addr.offset, int)
        and addr.segment_index in segment_sizes
        and 0
        <= addr.offset
        < (segment_sizes[addr.segment_index] if is_concrete_address else SEGMENT_SIZE_UPPER_BOUND)
    )


def is_valid_memory_value(value: MaybeRelocatable, segment_sizes: Dict[int, int]):
    return isinstance(value, int) or is_valid_memory_addr(
        addr=value, segment_sizes=segment_sizes, is_concrete_address=False
    )
