import dataclasses
import struct
from typing import Dict, Generic, List, TypeVar

from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, relocate_value

T = TypeVar("T", int, MaybeRelocatable)


@dataclasses.dataclass
class TraceEntry(Generic[T]):
    """
    A trace entry for every instruction that was executed.
    Holds the register values before the instruction was executed.
    """

    pc: T
    ap: T
    fp: T

    def serialize(self) -> bytes:
        """
        Serializes the trace entry to binary format:
          [ 8 bytes | 8 bytes | 8 bytes ]
          [ ap      | fp      | pc      ]
        """
        values = [self.ap, self.fp, self.pc]
        for x in values:
            assert isinstance(x, int)
            assert 0 <= x < 2 ** 64
        return struct.pack("<3Q", *values)

    @classmethod
    def deserialize(cls, serialized: bytes) -> "TraceEntry":
        assert len(serialized) == cls.serialization_size(), "Unexpected input length."

        ap, fp, pc = struct.unpack("<3Q", serialized)

        return cls(
            pc=pc,
            ap=ap,
            fp=fp,
        )

    @staticmethod
    def serialization_size():
        return 3 * 8


def relocate_trace(
    trace: List[TraceEntry[MaybeRelocatable]],
    segment_offsets: Dict[int, T],
    prime: int,
    allow_missing_segments: bool = False,
) -> List[TraceEntry[T]]:
    new_trace: List[TraceEntry[T]] = []

    def relocate_val(x):
        return relocate_value(x, segment_offsets, prime, allow_missing_segments)

    for entry in trace:
        new_trace.append(
            TraceEntry(
                pc=relocate_val(entry.pc),
                ap=relocate_val(entry.ap),
                fp=relocate_val(entry.fp),
            )
        )
    return new_trace
