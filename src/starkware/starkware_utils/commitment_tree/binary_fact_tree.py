from abc import abstractmethod
from typing import Collection, Dict, Optional, Tuple, Type, TypeVar

from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass
from starkware.storage.storage import Fact, FactFetchingContext

TFact = TypeVar("TFact", bound=Fact)
BinaryFactDict = Dict[bytes, Tuple[bytes, ...]]


class BinaryFactTree(ValidatedMarshmallowDataclass):
    """
    An abstract base class for Merkle and Patricia-Merkle tree.
    An immutable binary tree backed by an immutable fact storage.
    """

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
