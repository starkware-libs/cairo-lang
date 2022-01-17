import asyncio
import dataclasses
from typing import Optional, Tuple

from starkware.starkware_utils.commitment_tree.binary_fact_tree import BinaryFactDict
from starkware.starkware_utils.commitment_tree.binary_fact_tree_node import (
    BinaryFactTreeNode,
    read_node_fact,
    write_node_fact,
)
from starkware.starkware_utils.commitment_tree.patricia_tree.nodes import (
    BinaryNodeFact,
    EdgeNodeFact,
    EmptyNodeFact,
    PatriciaNodeFact,
    verify_path_value,
)
from starkware.starkware_utils.validated_dataclass import ValidatedDataclass
from starkware.storage.storage import FactFetchingContext


@dataclasses.dataclass(frozen=True)
class VirtualPatriciaNode(BinaryFactTreeNode, ValidatedDataclass):
    """
    Represents a virtual Patricia node.
    Virtual node instances are used to build and traverse through a Patricia tree.
    The main purpose of this class is to maintain the information of a virtual edge node up until
    the point it can be hashed (committed).
    """

    # The information of the virtual node.
    bottom_node: bytes
    path: int
    length: int

    # The height of the subtree rooted at this node.
    # In other words, this is the length of the path from this node to the leaves.
    height: int

    def __post_init__(self):
        """
        Performs validations on the constructed object.
        Note that many of the functions in this class rely on the invariants checked in this
        function, and on the fact they are made at initialization time (the object is immutable).
        """
        super().__post_init__()

        verify_path_value(path=self.path, length=self.length)

    @classmethod
    def empty_node(cls, height: int) -> "VirtualPatriciaNode":
        return cls(bottom_node=EmptyNodeFact.EMPTY_NODE_HASH, path=0, length=0, height=height)

    @classmethod
    def from_hash(cls, hash_value: bytes, height: int) -> "VirtualPatriciaNode":
        """
        Returns a virtual Patricia node of the form (hash, 0, 0).
        """
        return cls(bottom_node=hash_value, path=0, length=0, height=height)

    @classmethod
    def create_leaf(cls, hash_value: bytes) -> "VirtualPatriciaNode":
        return cls.from_hash(hash_value=hash_value, height=0)

    async def read_bottom_node_fact(
        self, ffc: FactFetchingContext, facts: Optional[BinaryFactDict]
    ) -> PatriciaNodeFact:
        return await read_node_fact(
            ffc=ffc,
            inner_node_fact_cls=PatriciaNodeFact,  # type: ignore
            fact_hash=self.bottom_node,
            facts=facts,
        )

    @property
    def is_empty(self) -> bool:
        return self.bottom_node == EmptyNodeFact.EMPTY_NODE_HASH

    @property
    def is_virtual_edge(self) -> bool:
        return self.length != 0

    @property
    def _leaf_hash(self) -> bytes:
        return self.bottom_node

    def get_height_in_tree(self) -> int:
        return self.height

    async def commit(self, ffc: FactFetchingContext, facts: Optional[BinaryFactDict]) -> bytes:
        """
        Calculates and returns the hash of self.
        If this is a virtual edge node, an edge node fact is written to the DB.
        """
        if not self.is_virtual_edge:
            # Node is already of form (hash, 0, 0); no work to be done.
            return self.bottom_node

        edge_node_fact = EdgeNodeFact(
            bottom_node=self.bottom_node, edge_path=self.path, edge_length=self.length
        )
        return await write_node_fact(ffc=ffc, inner_node_fact=edge_node_fact, facts=facts)

    async def decommit(
        self, ffc: FactFetchingContext, facts: Optional[BinaryFactDict]
    ) -> "VirtualPatriciaNode":
        """
        Returns the canonical representation of the information embedded in self.
        Returns (bottom, path, length) for an edge node of form (hash, 0, 0), which is the
        canonical form.
        """
        if self.is_leaf or self.is_empty or self.is_virtual_edge:
            # Node is already decommitted (of canonical form); no work to be done.
            return self

        # Need to read fact from storage to understand if (hash, 0, 0) represents a binary node,
        # or a committed edge node.
        # Note that a fact that was written in a previous combine while building this tree will
        # appear in cache (in case the FFC's storage is cached).
        root_node_fact = await self.read_bottom_node_fact(ffc=ffc, facts=facts)

        if isinstance(root_node_fact, BinaryNodeFact):
            return self
        if isinstance(root_node_fact, EdgeNodeFact):
            return VirtualPatriciaNode(
                bottom_node=root_node_fact.bottom_node,
                path=root_node_fact.edge_path,
                length=root_node_fact.edge_length,
                height=self.height,
            )

        raise NotImplementedError(f"Unexpected node fact type: {type(root_node_fact).__name__}.")

    @classmethod
    async def combine(
        cls,
        ffc: FactFetchingContext,
        left: "BinaryFactTreeNode",
        right: "BinaryFactTreeNode",
        facts: Optional[BinaryFactDict] = None,
    ) -> "VirtualPatriciaNode":
        """
        Gets two VirtualPatriciaNode objects left and right representing children nodes, and builds
        their parent node. Returns a new VirtualPatriciaNode.

        If facts argument is not None, this dictionary is filled with facts read from the DB.
        """
        # Downcast arguments.
        assert isinstance(left, VirtualPatriciaNode) and isinstance(right, VirtualPatriciaNode)

        assert (
            right.height == left.height
        ), f"Only trees of same height can be combined; got: {right.height} and {left.height}."

        parent_height = right.height + 1
        if left.is_empty and right.is_empty:
            return VirtualPatriciaNode.empty_node(height=parent_height)

        if not left.is_empty and not right.is_empty:
            return await cls._combine_to_binary_node(ffc=ffc, left=left, right=right, facts=facts)

        return await cls._combine_to_virtual_edge_node(ffc=ffc, left=left, right=right, facts=facts)

    async def get_children(
        self, ffc: FactFetchingContext, facts: Optional[BinaryFactDict] = None
    ) -> Tuple["VirtualPatriciaNode", "VirtualPatriciaNode"]:
        """
        Returns the two VirtualPatriciaNode objects which are the subtrees of the current
        VirtualPatriciaNode.

        If facts argument is not None, this dictionary is filled with facts read from the DB.
        """
        assert not self.is_leaf, "get_children() must not be called on leaves."

        children_height = self.height - 1
        if self.is_empty:
            empty_child = VirtualPatriciaNode.empty_node(height=children_height)
            return empty_child, empty_child

        if self.is_virtual_edge:
            return self._get_virtual_edge_node_children()

        # At this point the preimage of self.bottom_node must be read from the storage, to know
        # what kind of node it represents - a committed edge node, or a binary node.
        fact = await self.read_bottom_node_fact(ffc=ffc, facts=facts)

        if isinstance(fact, EdgeNodeFact):
            # A previously committed edge node.
            edge_node = VirtualPatriciaNode(
                bottom_node=fact.bottom_node,
                path=fact.edge_path,
                length=fact.edge_length,
                height=self.height,
            )
            return edge_node._get_virtual_edge_node_children()

        assert isinstance(fact, BinaryNodeFact)
        return (
            self.from_hash(hash_value=fact.left_node, height=children_height),
            self.from_hash(hash_value=fact.right_node, height=children_height),
        )

    # Internal utils.

    @classmethod
    async def _combine_to_binary_node(
        cls,
        ffc: FactFetchingContext,
        left: "VirtualPatriciaNode",
        right: "VirtualPatriciaNode",
        facts: Optional[BinaryFactDict],
    ) -> "VirtualPatriciaNode":
        """
        Combines two non-empty nodes to form a binary node.
        Writes the constructed node fact to the DB, as well as (up to) two other facts for the
        children if they were not previously committed.
        """
        left_node_hash, right_node_hash = await asyncio.gather(
            *(node.commit(ffc=ffc, facts=facts) for node in (left, right))
        )
        parent_node_fact = BinaryNodeFact(left_node=left_node_hash, right_node=right_node_hash)
        parent_fact_hash = await write_node_fact(
            ffc=ffc, inner_node_fact=parent_node_fact, facts=facts
        )

        return VirtualPatriciaNode(
            bottom_node=parent_fact_hash, path=0, length=0, height=right.height + 1
        )

    @classmethod
    async def _combine_to_virtual_edge_node(
        cls,
        ffc: FactFetchingContext,
        left: "VirtualPatriciaNode",
        right: "VirtualPatriciaNode",
        facts: Optional[BinaryFactDict],
    ) -> "VirtualPatriciaNode":
        """
        Combines an empty node and a non-empty node to form a virtual edge node.
        If the non-empty node is not known to be of canonical form, reads its fact from the DB
        in order to make it such (or make sure it is).
        """
        assert (
            left.is_empty != right.is_empty
        ), "_combine_to_virtual_edge_node() must be called on one empty and one non-empty nodes."

        non_empty_child = right if left.is_empty else left
        non_empty_child = await non_empty_child.decommit(ffc=ffc, facts=facts)

        parent_path = non_empty_child.path
        if left.is_empty:
            # Turn on the MSB bit if the non-empty child is on the right.
            parent_path += 1 << non_empty_child.length

        return VirtualPatriciaNode(
            bottom_node=non_empty_child.bottom_node,
            path=parent_path,
            length=non_empty_child.length + 1,
            height=non_empty_child.height + 1,
        )

    def _get_virtual_edge_node_children(
        self,
    ) -> Tuple["VirtualPatriciaNode", "VirtualPatriciaNode"]:
        """
        Returns the children of a virtual edge node: an empty node and a shorter-by-one virtual
        edge node, according to the direction embedded in the edge path.
        """
        children_height = self.height - 1
        children_length = self.length - 1
        non_empty_child = VirtualPatriciaNode(
            bottom_node=self.bottom_node,
            path=self.path & ((1 << children_length) - 1),  # Turn the MSB bit off.
            length=children_length,
            height=children_height,
        )

        edge_child_direction = self.path >> children_length
        empty_child = VirtualPatriciaNode.empty_node(height=children_height)
        if edge_child_direction == 0:
            # Non-empty on the left.
            return non_empty_child, empty_child
        else:
            # Non-empty on the right.
            return empty_child, non_empty_child

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VirtualPatriciaNode):
            return NotImplemented

        return (
            self.bottom_node == other.bottom_node
            and self.path == other.path
            and self.length == other.length
            and self.height == other.height
        )
