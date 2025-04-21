import dataclasses
import itertools
from abc import ABC, abstractmethod
from typing import List

from starkware.cairo.lang.vm.crypto import poseidon_hash_many


class BytecodeSegmentStructure(ABC):
    """
    Represents the structure of the bytecode to allow loading it partially into the OS memory.
    See the documentation of the OS function `bytecode_hash_node` in `compiled_class.cairo`
    for more details.
    """

    @abstractmethod
    def hash(self) -> int:
        """
        Computes the hash of the node.
        """


@dataclasses.dataclass
class BytecodeLeaf(BytecodeSegmentStructure):
    """
    Represents a leaf in the bytecode segment tree.
    """

    data: List[int]

    def hash(self) -> int:
        return poseidon_hash_many(self.data)


@dataclasses.dataclass
class BytecodeSegmentedNode(BytecodeSegmentStructure):
    """
    Represents an internal node in the bytecode segment tree.
    Each child can be loaded into memory or skipped.
    """

    segments: List["BytecodeSegment"]

    def hash(self) -> int:
        return (
            poseidon_hash_many(
                itertools.chain(
                    *[(node.segment_length, node.inner_structure.hash()) for node in self.segments]
                )
            )
            + 1
        )


@dataclasses.dataclass
class BytecodeSegment:
    """
    Represents a child of BytecodeSegmentedNode.
    """

    # The length of the segment.
    segment_length: int
    # The inner structure of the segment.
    inner_structure: BytecodeSegmentStructure

    def __post_init__(self):
        assert self.segment_length > 0, f"Invalid segment length: {self.segment_length}."
