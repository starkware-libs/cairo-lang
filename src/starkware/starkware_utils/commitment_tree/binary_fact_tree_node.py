import asyncio
from abc import ABC, abstractmethod
from typing import (
    Any,
    AsyncIterator,
    Collection,
    Dict,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

from starkware.starkware_utils.commitment_tree.binary_fact_tree import BinaryFactDict, TFact
from starkware.starkware_utils.commitment_tree.merkle_tree.traverse_tree import traverse_tree
from starkware.storage.storage import Fact, FactFetchingContext

TBinaryFactTreeNode = TypeVar("TBinaryFactTreeNode", bound="BinaryFactTreeNode")
UpdateTree = Optional[Union[Tuple[Any, Any], Fact]]
NodeType = NamedTuple(
    "NodeType", [("index", int), ("tree", "BinaryFactTreeNode"), ("update", UpdateTree)]
)


class BinaryFactTreeNode(ABC):
    """
    Represents a binary node in a binary fact tree.
    Contains methods that allow traversal downwards the tree this node is a part of, as well as
    building new subtrees according to modified leaf information.
    """

    @property
    def is_leaf(self) -> bool:
        return self.get_height_in_tree() == 0

    @property
    def leaf_hash(self) -> bytes:
        """
        Returns the hash of self, which must be a leaf to use this property.
        """
        assert self.is_leaf, (
            f"leaf_hash property must only be called on leaf nodes; got: height "
            f"{self.get_height_in_tree()}."
        )

        return self._leaf_hash

    @abstractmethod
    def get_height_in_tree(self) -> int:
        """
        Returns the height of the node in a tree.
        """

    @property
    @abstractmethod
    def _leaf_hash(self) -> bytes:
        pass

    @classmethod
    @abstractmethod
    def create_leaf(cls: Type[TBinaryFactTreeNode], hash_value: bytes) -> TBinaryFactTreeNode:
        pass

    @classmethod
    @abstractmethod
    async def combine(
        cls: Type[TBinaryFactTreeNode],
        ffc: FactFetchingContext,
        left: "BinaryFactTreeNode",
        right: "BinaryFactTreeNode",
        facts: Optional[BinaryFactDict] = None,
    ) -> TBinaryFactTreeNode:
        """
        Gets two BinaryFactTreeNode objects left and right representing children nodes, and builds
        their parent node. Returns a new BinaryFactTreeNode.

        If facts argument is not None, this dictionary is filled with facts read from the DB.
        """

    @abstractmethod
    async def get_children(
        self, ffc: FactFetchingContext, facts: Optional[BinaryFactDict] = None
    ) -> Tuple["BinaryFactTreeNode", "BinaryFactTreeNode"]:
        """
        Returns the two BinaryFactTreeNode objects which are the roots of the subtrees of the
        current BinaryFactTreeNode.

        If facts argument is not None, this dictionary is filled with facts read from the DB.
        """

    async def _get_leaves(
        self,
        ffc: FactFetchingContext,
        indices: Collection[int],
        fact_cls: Type[TFact],
        facts: Optional[BinaryFactDict] = None,
    ) -> Dict[int, TFact]:
        """
        Returns the values of the leaves whose indices are given.

        If facts argument is not None, this dictionary is filled during traversal through the tree
        by the facts of their paths from the root down.

        This method is to be called by a get_leaves() method of a specific tree implementation
        (derived class of BinaryFactTree).
        """
        assert not issubclass(fact_cls, InnerNodeFact), (
            f"Leaf fact class object {fact_cls.__name__} must not inherit from "
            f"{InnerNodeFact.__name__}."
        )

        def unify_leaves(
            left_leaves: Dict[int, TFact], right_leaves: Dict[int, TFact]
        ) -> Dict[int, TFact]:
            return {**left_leaves, **{x + mid: y for x, y in right_leaves.items()}}

        if len(indices) == 0:
            return {}

        if self.is_leaf:
            assert set(indices) == {0}, f"Merkle tree indices out of range: {indices}."
            leaf = await get_node_fact_or_fail(
                ffc=ffc, node_fact_cls=fact_cls, fact_hash=self.leaf_hash
            )

            return {0: leaf}

        mid = 2 ** (self.get_height_in_tree() - 1)
        left_indices = [index for index in indices if index < mid]
        right_indices = [(index - mid) for index in indices if index >= mid]

        left_child, right_child = await self.get_children(ffc=ffc, facts=facts)

        # Optimizations in order to avoid a redundant asyncio.gather call that postpones the
        # execution of the recursive task.
        if len(left_indices) == 0:
            right_leaves = await right_child._get_leaves(
                ffc=ffc, indices=right_indices, fact_cls=fact_cls, facts=facts
            )
            return unify_leaves(right_leaves=right_leaves, left_leaves={})

        if len(right_indices) == 0:
            left_leaves = await left_child._get_leaves(
                ffc=ffc, indices=left_indices, fact_cls=fact_cls, facts=facts
            )
            return unify_leaves(right_leaves={}, left_leaves=left_leaves)

        left_leaves, right_leaves = await asyncio.gather(
            left_child._get_leaves(ffc=ffc, indices=left_indices, fact_cls=fact_cls, facts=facts),
            right_child._get_leaves(ffc=ffc, indices=right_indices, fact_cls=fact_cls, facts=facts),
        )

        return unify_leaves(left_leaves=left_leaves, right_leaves=right_leaves)

    async def _update(
        self: TBinaryFactTreeNode,
        ffc: FactFetchingContext,
        modifications: Collection[Tuple[int, Fact]],
        facts: Optional[BinaryFactDict] = None,
    ) -> TBinaryFactTreeNode:
        """
        Updates the tree with the given list of modifications, writes all the new facts to the
        storage and returns a new BinaryFactTree representing the fact of the root of the new tree.

        If facts argument is not None, this dictionary is filled during building the new tree
        by the facts of their paths from the leaves up.

        This method is to be called by a update() method of a specific tree implementation
        (derived class of BinaryFactTree).
        """
        # A map from node index to the updated binary fact subtree.
        # This map is populated when we traverse a node and know it's value in the updated tree.
        # This happens when either of these happens:
        # 1. The node has no updates => value remains the same.
        # 2. Node is a leaf update, and we just updated the leaf value.
        # 3. When its two children are already updated (happens in update_necessary()).
        updated_nodes: Dict[int, BinaryFactTreeNode] = {}

        async def update_necessary(node_index: int):
            """
            Checks if there are merkle nodes that are not updated, but all of its children are.
            Starts at node_index, and goes up to the root.
            """
            # Xoring by 1 switch between 2k <-> 2k + 1, which are sibilings in the tree.
            # The parent of these sibilings is k = floor(n/2) for n = 2k, 2k+1.
            while node_index ^ 1 in updated_nodes:
                node_index //= 2
                updated_nodes[node_index] = await self.combine(
                    ffc=ffc,
                    left=updated_nodes[2 * node_index],
                    right=updated_nodes[2 * node_index + 1],
                    facts=facts,
                )

                del updated_nodes[2 * node_index]
                del updated_nodes[2 * node_index + 1]

        async def traverse_node(node: NodeType) -> AsyncIterator[NodeType]:
            """
            Callback function for traverse_tree().
            If the current node has leaf updates, get its children, and traverse them.
            If the current node has no updates, do nothing.
            If the current node is a leaf, update the leaf.
            """
            node_index, binary_fact_tree_node, update_subtree = node

            if update_subtree is None:
                # No update to subtree.
                updated_nodes[node_index] = binary_fact_tree_node
                await update_necessary(node_index=node_index)
                return

            if binary_fact_tree_node.is_leaf:
                # Leaf update.
                new_fact = update_subtree
                assert isinstance(new_fact, Fact)

                leaf_hash = await new_fact.set_fact(ffc=ffc)
                updated_nodes[node_index] = self.create_leaf(hash_value=leaf_hash)
                await update_necessary(node_index=node_index)
                return

            # Inner node with updates.
            assert isinstance(update_subtree, tuple)
            left, right = await binary_fact_tree_node.get_children(ffc, facts=facts)
            yield NodeType(index=2 * node_index, tree=left, update=update_subtree[0])
            yield NodeType(index=2 * node_index + 1, tree=right, update=update_subtree[1])

        update_tree = build_update_tree(
            height=self.get_height_in_tree(), modifications=modifications
        )
        first_node = NodeType(index=1, tree=self, update=update_tree)
        await traverse_tree(
            get_children_callback=traverse_node, root=first_node, n_workers=ffc.n_workers
        )

        # Since the updated_nodes dictionary cleans itself, we expect only the new root to be
        # present, at node index 1.
        assert len(updated_nodes) == 1 and 1 in updated_nodes
        return cast(TBinaryFactTreeNode, updated_nodes[1])


class InnerNodeFact(Fact):
    """
    Represents the fact of an inner node in a binary fact tree.
    """

    @abstractmethod
    def to_tuple(self) -> Tuple[bytes, ...]:
        """
        Returns a representation of the fact's preimage as a tuple.
        """


TInnerNodeFact = TypeVar("TInnerNodeFact", bound=InnerNodeFact)


async def get_node_fact_or_fail(
    ffc: FactFetchingContext, node_fact_cls: Type[TFact], fact_hash: bytes
) -> TFact:
    node_fact = await node_fact_cls.get(storage=ffc.storage, suffix=fact_hash)
    assert node_fact is not None, f"Fact missing from DB: 0x{fact_hash.hex()}."

    return node_fact


async def read_node_fact(
    ffc: FactFetchingContext,
    inner_node_fact_cls: Type[TInnerNodeFact],
    fact_hash: bytes,
    facts: Optional[BinaryFactDict],
) -> TInnerNodeFact:
    node_fact = await get_node_fact_or_fail(
        ffc=ffc, node_fact_cls=inner_node_fact_cls, fact_hash=fact_hash
    )

    if facts is not None:
        facts[fact_hash] = node_fact.to_tuple()

    return node_fact


async def write_node_fact(
    ffc: FactFetchingContext, inner_node_fact: InnerNodeFact, facts: Optional[BinaryFactDict]
) -> bytes:
    fact_hash = await inner_node_fact.set_fact(ffc=ffc)

    if facts is not None:
        facts[fact_hash] = inner_node_fact.to_tuple()

    return fact_hash


def build_update_tree(height: int, modifications: Collection[Tuple[int, TFact]]) -> UpdateTree:
    """
    Constructs a tree from leaf updates. This is not a full binary tree. It is just the subtree
    induced by the modification leaves.
    Returns a tree. A tree is either:
     * None
     * a pair of trees
     * A leaf
    """
    # Bottom layer. This will prefer the last modification to an index.
    if len(modifications) == 0:
        return None

    # A layer is a dictionary from index in current merkle layer [0, 2**layer_height) to a tree.
    # A tree is either None, a leaf, or a pair of trees.
    layer: Dict[int, UpdateTree] = dict(modifications)

    for _ in range(height):
        parents = set(index // 2 for index in layer.keys())
        # Note that dictionary.get(key) is None if the the key is not in the dictionary.
        layer = {index: (layer.get(index * 2), layer.get(index * 2 + 1)) for index in parents}

    # We reached layer_height=0, the top layer with only the root (with index 0).
    assert len(layer) == 1
    return layer[0]
