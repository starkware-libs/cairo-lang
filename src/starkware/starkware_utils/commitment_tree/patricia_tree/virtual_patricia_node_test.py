import asyncio
from typing import Collection

import pytest

from starkware.cairo.common.patricia_utils import compute_patricia_from_leaves_for_test
from starkware.crypto.signature.fast_pedersen_hash import pedersen_hash, pedersen_hash_func
from starkware.python.utils import to_bytes
from starkware.starkware_utils.commitment_tree.patricia_tree.nodes import (
    BinaryNodeFact,
    EdgeNodeFact,
)
from starkware.starkware_utils.commitment_tree.patricia_tree.virtual_calculation_node import (
    VirtualCalculationNode,
)
from starkware.starkware_utils.commitment_tree.patricia_tree.virtual_patricia_node import (
    VirtualPatriciaNode,
)
from starkware.starkware_utils.commitment_tree.update_tree import update_tree
from starkware.storage.storage import FactFetchingContext
from starkware.storage.storage_utils import LeafFact
from starkware.storage.test_utils import MockStorage


@pytest.fixture
def ffc() -> FactFetchingContext:
    return FactFetchingContext(storage=MockStorage(), hash_func=pedersen_hash_func)


async def make_virtual_edge_non_canonical(
    ffc: FactFetchingContext, node: VirtualPatriciaNode
) -> VirtualPatriciaNode:
    """
    Returns the non-canonical form (hash, 0, 0) of a virtual edge node.
    """
    assert node.is_virtual_edge, "Node should be of canonical form."

    node_hash = await node.commit(ffc=ffc, facts=None)
    return VirtualPatriciaNode.from_hash(hash_value=node_hash, height=node.height)


def verify_root(leaves: Collection[int], expected_root_hash: bytes):
    root_hash, _preimage, _node_at_path = compute_patricia_from_leaves_for_test(
        leaves=leaves, hash_func=pedersen_hash
    )
    assert expected_root_hash == to_bytes(root_hash)


@pytest.mark.asyncio
async def test_get_children(ffc: FactFetchingContext):
    """
    Builds a Patricia tree of length 3 with the following values in the leaves: 1 -> 12, 6 -> 30.
    This is done using only "low-level" VirtualPatriciaNode methods, without _update().
    #              0
    #        0           0
    #     0     0     0     0
    #   0  12 0   0 0   0 30  0
    """
    # Create empty trees and write their facts to DB.
    await LeafFact(value=0).set_fact(ffc=ffc)
    empty_tree_0 = VirtualPatriciaNode.empty_node(height=0)
    empty_tree_1 = VirtualPatriciaNode.empty_node(height=1)
    assert await empty_tree_1.get_children(ffc=ffc) == (empty_tree_0, empty_tree_0)

    # Create leaves and write their facts to DB.
    leaf_hash_12, leaf_hash_30 = await asyncio.gather(
        *(leaf_fact.set_fact(ffc=ffc) for leaf_fact in (LeafFact(value=12), LeafFact(value=30)))
    )
    leaf_12 = VirtualPatriciaNode(bottom_node=leaf_hash_12, path=0, length=0, height=0)
    leaf_30 = VirtualPatriciaNode(bottom_node=leaf_hash_30, path=0, length=0, height=0)

    # Build left subtree and write its fact to DB.
    await EdgeNodeFact(bottom_node=leaf_hash_12, edge_path=1, edge_length=1).set_fact(ffc=ffc)
    left_tree_1 = VirtualPatriciaNode(bottom_node=leaf_hash_12, path=1, length=1, height=1)
    # Get children on both forms.
    expected_children = (empty_tree_0, leaf_12)
    assert await left_tree_1.get_children(ffc=ffc) == expected_children
    non_canonical_node = await make_virtual_edge_non_canonical(ffc=ffc, node=left_tree_1)
    assert await non_canonical_node.get_children(ffc=ffc) == expected_children

    # Combine left edge node and right empty tree. Write the result's fact to DB.
    await EdgeNodeFact(bottom_node=leaf_hash_12, edge_path=0b01, edge_length=2).set_fact(ffc=ffc)
    left_tree_2 = VirtualPatriciaNode(bottom_node=leaf_hash_12, path=0b01, length=2, height=2)
    # Get children on both forms.
    expected_children = (left_tree_1, empty_tree_1)
    assert await left_tree_2.get_children(ffc=ffc) == expected_children
    non_canonical_node = await make_virtual_edge_non_canonical(ffc=ffc, node=left_tree_2)
    assert await non_canonical_node.get_children(ffc=ffc) == expected_children

    # Build right subtree.
    # Combine left leaf and right empty tree. Write the result's fact to DB.
    await EdgeNodeFact(bottom_node=leaf_hash_30, edge_path=0, edge_length=1).set_fact(ffc=ffc)
    right_tree_1 = VirtualPatriciaNode(bottom_node=leaf_hash_30, path=0, length=1, height=1)
    # Get children on both forms.
    expected_children = (leaf_30, empty_tree_0)
    assert await right_tree_1.get_children(ffc=ffc) == expected_children
    non_canonical_node = await make_virtual_edge_non_canonical(ffc=ffc, node=right_tree_1)
    assert await non_canonical_node.get_children(ffc=ffc) == expected_children

    # Combine left empty tree and right edge node. Write the result's fact to DB.
    await EdgeNodeFact(bottom_node=leaf_hash_30, edge_path=0b10, edge_length=2).set_fact(ffc=ffc)
    right_tree_2 = VirtualPatriciaNode(bottom_node=leaf_hash_30, path=0b10, length=2, height=2)
    # Get children on both forms.
    expected_children = (empty_tree_1, right_tree_1)
    assert await right_tree_2.get_children(ffc=ffc) == expected_children
    non_canonical_node = await make_virtual_edge_non_canonical(ffc=ffc, node=right_tree_2)
    assert await non_canonical_node.get_children(ffc=ffc) == expected_children

    # Build whole tree and write its fact to DB.
    left_node, right_node = await asyncio.gather(
        *(node.commit(ffc=ffc, facts=None) for node in (left_tree_2, right_tree_2))
    )
    root_hash = await BinaryNodeFact(left_node=left_node, right_node=right_node).set_fact(ffc=ffc)

    tree = VirtualPatriciaNode(bottom_node=root_hash, path=0, length=0, height=3)
    left_edge_child, right_edge_child = await tree.get_children(ffc=ffc)
    assert (left_edge_child, right_edge_child) == (
        VirtualPatriciaNode(bottom_node=left_node, path=0, length=0, height=2),
        VirtualPatriciaNode(bottom_node=right_node, path=0, length=0, height=2),
    )

    # Test operations on the committed left tree.
    # Getting its children should return another edge with length shorter-by-one.
    assert await left_edge_child.get_children(ffc=ffc) == (left_tree_1, empty_tree_1)


@pytest.mark.asyncio
async def test_update_and_get_leaves(ffc: FactFetchingContext):
    """
    Builds a Patricia tree of length 3 with the following values in the leaves: 1 -> 12, 6 -> 30.
    This is the same tree as in the test above, but in this test built using _update().
    """
    # Done manually, since PatriciaTree.empty() is in charge of that and is not used here.
    await LeafFact(value=0).set_fact(ffc=ffc)

    # Build empty tree.
    tree = VirtualPatriciaNode.empty_node(height=3)

    # Compare empty root to test util result.
    leaves_range = range(8)
    verify_root(leaves=[0 for _ in leaves_range], expected_root_hash=tree.bottom_node)

    # Update leaf values.
    leaves = {1: LeafFact(value=12), 4: LeafFact(value=1000), 6: LeafFact(value=30)}
    tree = await update_tree(
        tree=tree,
        ffc=ffc,
        modifications=leaves.items(),
        calculation_node_cls=VirtualCalculationNode,
    )

    # Check get_leaves().
    expected_leaves = {
        leaf_id: leaves[leaf_id] if leaf_id in leaves else LeafFact(value=0)
        for leaf_id in leaves_range
    }
    assert (
        await tree._get_leaves(ffc=ffc, indices=leaves_range, fact_cls=LeafFact) == expected_leaves
    )

    # Compare to test util result.
    verify_root(
        leaves=[leaf.value for leaf in expected_leaves.values()],
        expected_root_hash=tree.bottom_node,
    )

    # Update leaf values again: new leaves contain addition, deletion and updating a key.
    updated_leaves = {
        0: LeafFact(value=2),
        1: LeafFact(value=20),
        3: LeafFact(value=6),
        6: LeafFact(value=0),
    }
    tree = await update_tree(
        tree=tree,
        ffc=ffc,
        modifications=updated_leaves.items(),
        calculation_node_cls=VirtualCalculationNode,
    )

    # Check get_leaves().
    updated_leaves = {**expected_leaves, **updated_leaves}
    assert (
        await tree._get_leaves(ffc=ffc, indices=leaves_range, fact_cls=LeafFact) == updated_leaves
    )

    # Compare to test util result.
    sorted_by_index_leaf_values = [updated_leaves[leaf_id].value for leaf_id in leaves_range]
    expected_root_hash = await tree.commit(ffc=ffc, facts=None)  # Root is an edge node.
    verify_root(leaves=sorted_by_index_leaf_values, expected_root_hash=expected_root_hash)
