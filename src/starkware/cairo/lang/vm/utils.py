import dataclasses
import re
from typing import Dict, Optional

import marshmallow.fields as mfields

from starkware.cairo.lang.vm.relocatable import MaybeRelocatable, RelocatableValue


class IntAsHex(mfields.Field):
    """
    A field that behaves like an integer, but serializes to hex string. Usually, this applies to
    field elements.
    """

    default_error_messages = {"invalid": 'Expected hex string, got: "{input}".'}

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        assert isinstance(value, int)
        return hex(value)

    def _deserialize(self, value, attr, data, **kwargs):
        if re.match("^0x[0-9a-f]+$", value) is None:
            self.fail("invalid", input=value)

        return int(value, 16)


@dataclasses.dataclass
class MemorySegmentAddresses:
    # Represents the address of the beginning of the memory segment.
    begin_addr: int

    # Represents the location of the segment pointer after the program is completed. This is not
    # the end of the segment. For example, for the program segment, it will point to the last
    # instruction executed, rather than the end of the program segment.
    stop_ptr: Optional[int]


@dataclasses.dataclass
class MemorySegmentRelocatableAddresses:
    """
    Same as MemorySegmentAddresses, except that the addresses are RelocatableValue.
    """

    begin_addr: RelocatableValue
    stop_ptr: Optional[RelocatableValue]


class ResourcesError(Exception):
    """
    Base class for exceptions thrown due to lack of Cairo run resources.
    """


@dataclasses.dataclass
class RunResources:
    """
    Maintains the resources of a Cairo run. Can be used across multiple runners.
    """

    n_steps: Optional[int]

    @property
    def consumed(self) -> bool:
        """
        Returns True if the resources were consumed.
        """
        return self.n_steps is not None and self.n_steps <= 0

    def consume_step(self):
        """
        Consumes one Cairo step.
        """
        if self.n_steps is not None:
            self.n_steps -= 1


def sort_segments(
    memory_segments: Dict[str, MemorySegmentAddresses]
) -> Dict[str, MemorySegmentAddresses]:
    """
    Sorts the segments dictionary according to the correct serialization order in the
    public input.
    Gets and returns a dictionary from segment name to a MemorySegmentAddresses.
    """
    segment_names = ["program", "execution", "output", "pedersen", "range_check", "ecdsa"]
    if "bitwise" in memory_segments:
        segment_names.append("bitwise")
    res = {name: memory_segments[name] for name in segment_names}
    assert len(res) == len(memory_segments), f"Wrong segments given: {memory_segments}."
    return res


def decimal_repr(val: MaybeRelocatable, prime: int) -> str:
    """
    Returns a (possibly negative) decimal representation of the given value.
    """
    if isinstance(val, int):
        # Shift val to the range (-prime // 2, prime // 2).
        return str((val + prime // 2) % prime - (prime // 2))
    else:
        return str(val)
