from abc import abstractmethod
from dataclasses import field
from importlib import import_module
from logging import Logger
from typing import Collection, Dict, Optional, Tuple, Type, TypeVar

import marshmallow_dataclass

from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass
from starkware.starkware_utils.validated_fields import bytes_as_hex_metadata
from starkware.storage.storage import Fact, FactFetchingContext

TFact = TypeVar("TFact", bound=Fact)
BinaryFactDict = Dict[int, Tuple[int, ...]]


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@marshmallow_dataclass.dataclass(frozen=True)  # type: ignore[misc]
class BinaryFactTree(ValidatedMarshmallowDataclass):
    """
    An abstract base class for Merkle and Patricia-Merkle tree.
    An immutable binary tree backed by an immutable fact storage.
    """

    root: bytes = field(metadata=bytes_as_hex_metadata(validated_field=None))
    height: int

    @classmethod
    @abstractmethod
    async def empty_tree(
        cls, ffc: FactFetchingContext, height: int, leaf_fact: Fact
    ) -> "BinaryFactTree":
        """
        Initializes an empty BinaryFactTree of the given height.
        """

    @abstractmethod
    async def get_leaves(
        self,
        ffc: FactFetchingContext,
        indices: Collection[int],
        fact_cls: Type[TFact],
        facts: Optional[BinaryFactDict] = None,
    ) -> Dict[int, TFact]:
        """
        Returns the values of the leaves whose indices are given.
        """

    @abstractmethod
    async def update(
        self,
        ffc: FactFetchingContext,
        modifications: Collection[Tuple[int, Fact]],
        facts: Optional[BinaryFactDict] = None,
    ) -> "BinaryFactTree":
        """
        Updates the tree with the given list of modifications, writes all the new facts to the
        storage and returns a new BinaryFactTree representing the fact of the root of the new tree.

        If facts argument is not None, this dictionary is filled during traversal through the tree
        by the facts of their paths from the leaves up.
        """

    async def get_leaf(self, ffc: FactFetchingContext, index: int, fact_cls: Type[TFact]) -> TFact:
        """
        Returns the value of a single leaf whose index is given.
        """
        leaves = await self.get_leaves(ffc=ffc, indices=[index], fact_cls=fact_cls)
        assert leaves.keys() == {
            index
        }, f"get_leaves() on single leaf index returned an unexpected result."

        return leaves[index]

    @staticmethod
    def from_config(import_path: str, logger: Optional[Logger] = None) -> Type["BinaryFactTree"]:
        """
        Creates a tree class from an import string.
        """
        if logger is not None:
            logger.info(f"Importing {import_path}")
        parts = import_path.rsplit(".", 1)
        state_class = getattr(import_module(parts[0]), parts[1])
        return state_class
