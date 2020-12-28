import dataclasses
from typing import Dict, Tuple, TypeVar, Union

MaybeRelocatable = Union[int, 'RelocatableValue']
T = TypeVar('T', int, MaybeRelocatable)


@dataclasses.dataclass(frozen=True)
class RelocatableValue:
    """
    A value in the cairo vm representing an address in some memory segment. This is meant to be
    replaced by a real memory address (field element) after the VM finished.
    """
    segment_index: int
    offset: int

    SEGMENT_BITS = 16
    OFFSET_BITS = 47

    def __add__(self, other: MaybeRelocatable) -> 'RelocatableValue':
        if isinstance(other, int):
            return RelocatableValue(self.segment_index, self.offset + other)
        assert not isinstance(other, RelocatableValue), 'Cannot add two relocatable values'
        return NotImplemented

    def __radd__(self, other: MaybeRelocatable) -> 'RelocatableValue':
        return self + other

    def __sub__(self, other: MaybeRelocatable) -> MaybeRelocatable:
        if isinstance(other, int):
            return RelocatableValue(self.segment_index, self.offset - other)
        assert self.segment_index == other.segment_index, \
            'Can only subtract two relocatable values of the same segment ' \
            f'({self.segment_index} != {other.segment_index}).'
        return self.offset - other.offset

    def __mod__(self, other: int):
        return RelocatableValue(self.segment_index, self.offset % other)

    def __lt__(self, other: MaybeRelocatable):
        if isinstance(other, int):
            # Integers are considered smaller than all relocatable values.
            return False
        if not isinstance(other, RelocatableValue):
            return NotImplemented
        return (self.segment_index, self.offset) < (other.segment_index, other.offset)

    def __le__(self, other: MaybeRelocatable):
        return (self < other or self == other)

    def __ge__(self, other: MaybeRelocatable):
        return not (self < other)

    def __gt__(self, other: MaybeRelocatable):
        return not (self <= other)

    def __hash__(self):
        return hash((self.segment_index, self.offset))

    def __format__(self, format_spec):
        return f'{self.segment_index}:{self.offset}'.__format__(format_spec)

    def __str__(self):
        return f'{self.segment_index}:{self.offset}'

    def to_bytes(self, n_bytes: int, byte_order: str) -> bytes:
        """
        Serializes RelocatableValue as:
        1bit |   SEGMENT_BITS |   OFFSET_BITS
        1    |     segment    |   offset
        Serializes int as
        1bit | num
        0    | num
        """
        if isinstance(self, int):
            assert self < 2 ** (8 * n_bytes - 1)
            return self.to_bytes(n_bytes, byte_order)
        assert n_bytes * 8 > self.SEGMENT_BITS + self.OFFSET_BITS
        num = 2 ** (8 * n_bytes - 1) + self.segment_index * 2 ** self.OFFSET_BITS + self.offset
        return num.to_bytes(n_bytes, byte_order)

    @classmethod
    def from_bytes(cls, data: bytes, byte_order: str) -> MaybeRelocatable:
        n_bytes = len(data)
        num = int.from_bytes(data, byte_order)
        if num & (2 ** (8 * n_bytes - 1)):
            offset = num & (2 ** cls.OFFSET_BITS - 1)
            segment_index = (num >> cls.OFFSET_BITS) & (2 ** cls.SEGMENT_BITS - 1)
            return RelocatableValue(segment_index, offset)
        return num

    @staticmethod
    def to_tuple(value: MaybeRelocatable) -> Tuple[int, ...]:
        """
        Converts a MaybeRelocatable to a tuple (which can be used to serialize the value in JSON).
        """
        if isinstance(value, RelocatableValue):
            return (value.segment_index, value.offset)
        elif isinstance(value, int):
            return (value,)
        else:
            raise NotImplementedError(f'Expected MaybeRelocatable, got: {type(value).__name__}.')

    @classmethod
    def from_tuple(cls, value: Tuple[int, ...]) -> MaybeRelocatable:
        """
        Converts a tuple to a MaybeRelocatable. See to_tuple().
        """
        if len(value) == 2:
            return RelocatableValue(*value)
        elif len(value) == 1:
            return value[0]
        else:
            raise NotImplementedError(f'Expected a tuple of size 1 or 2, got: {value}.')


def relocate_value(
        value: MaybeRelocatable, segment_offsets: Dict[int, T], prime: int,
        allow_missing_segments: bool = False) -> T:
    if isinstance(value, int):
        return value
    elif isinstance(value, RelocatableValue):
        segment_offset = segment_offsets.get(value.segment_index)
        if segment_offset is None:
            assert allow_missing_segments, f"""\
Failed to relocate {value} with allow_missing_segments = False.
segment_offsets={segment_offsets}.
"""
            return value  # type: ignore

        value = value.offset + segment_offset
        if isinstance(value, int):
            assert value < prime
        return value
    else:
        raise NotImplementedError('Not relocatable')
