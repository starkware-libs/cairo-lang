from dataclasses import field
from typing import Collection, Dict, Optional, Tuple, Type

import marshmallow_dataclass

from starkware.starkware_utils.commitment_tree.binary_fact_tree import (
    BinaryFactDict,
    BinaryFactTree,
    TFact,
)
from starkware.starkware_utils.commitment_tree.patricia_tree.nodes import EmptyNodeFact
from starkware.starkware_utils.commitment_tree.patricia_tree.virtual_patricia_node import (
    VirtualPatriciaNode,
)
from starkware.starkware_utils.validated_fields import bytes_as_hex_metadata
from starkware.storage.storage import Fact, FactFetchingContext


@marshmallow_dataclass.dataclass(frozen=True)
class PatriciaTree(BinaryFactTree):
    """
    An immutable Patricia-Merkle tree backed by an immutable fact storage.
    """

    root: bytes = field(metadata=bytes_as_hex_metadata(validated_field=None))
    height: int

    @classmethod
    async def empty_tree(
        cls, ffc: FactFetchingContext, height: int, leaf_fact: Fact
    ) -> "PatriciaTree":
        """
        Initializes an empty PatriciaTree of the given height.
        """
        empty_leaf_fact_hash = await leaf_fact.set_fact(ffc=ffc)
        assert empty_leaf_fact_hash == EmptyNodeFact.EMPTY_NODE_HASH, (
            f"The hash value of an empty leaf fact must be {EmptyNodeFact.EMPTY_NODE_HASH.hex()}; "
            f"got: {empty_leaf_fact_hash.hex()}."
        )

        return PatriciaTree(root=EmptyNodeFact.EMPTY_NODE_HASH, height=height)

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
        virtual_root_node = VirtualPatriciaNode.from_hash(hash_value=self.root, height=self.height)
        return await virtual_root_node._get_leaves(
            ffc=ffc, indices=indices, fact_cls=fact_cls, facts=facts
        )

    async def update(
        self,
        ffc: FactFetchingContext,
        modifications: Collection[Tuple[int, Fact]],
        facts: Optional[BinaryFactDict] = None,
    ) -> "PatriciaTree":
        """
        Updates the tree with the given list of modifications, writes all the new facts to the
        storage and returns a new PatriciaTree representing the fact of the root of the new tree.
        """
        virtual_root_node = VirtualPatriciaNode.from_hash(hash_value=self.root, height=self.height)
        updated_virtual_root_node = await virtual_root_node._update(
            ffc=ffc, modifications=modifications, facts=facts
        )

        # In case root is an edge node, its fact must be explicitly written to DB.
        root_hash = await updated_virtual_root_node.commit(ffc=ffc, facts=facts)
        return PatriciaTree(root=root_hash, height=updated_virtual_root_node.height)
