import asyncio
from typing import Collection

import pytest

from starkware.cairo.common.patricia_utils import compute_patricia_from_leaves_for_test
from starkware.crypto.signature.fast_pedersen_hash import async_pedersen_hash_func, pedersen_hash
from starkware.python.utils import to_bytes
from starkware.starkware_utils.commitment_tree.patricia_tree.nodes import (
    BinaryNodeFact,
    EmptyNodeFact,
)
from starkware.starkware_utils.commitment_tree.patricia_tree.virtual_patricia_node import (
    VirtualPatriciaNode,
)
from starkware.starkware_utils.commitment_tree.test_utils import LeafFact
from starkware.storage.storage import FactFetchingContext
from starkware.storage.test_utils import MockStorage


@pytest.fixture
def ffc() -> FactFetchingContext:
    return FactFetchingContext(storage=MockStorage(), hash_func=async_pedersen_hash_func)


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
async def test_combine_and_get_children(ffc: FactFetchingContext):
    """
    Builds a Patricia tree of length 3 with the following values in the leaves: 1 -> 12, 6 -> 30.
    This is done using only "low-level" VirtualPatriciaNode methods, without _update().
    #              0
    #        0           0
    #     0     0     0     0
    #   0  12 0   0 0   0 30  0
    """
    leaf_hash_12, leaf_hash_30, _ = await asyncio.gather(
        *(
            leaf_fact.set_fact(ffc=ffc)
            for leaf_fact in (LeafFact(value=12), LeafFact(value=30), LeafFact(value=0))
        )
    )

    # Combine two empty trees.
    empty_tree_0 = VirtualPatriciaNode.empty_node(height=0)
    empty_tree_1 = await VirtualPatriciaNode.combine(ffc=ffc, left=empty_tree_0, right=empty_tree_0)
    assert empty_tree_1 == VirtualPatriciaNode(
        bottom_node=EmptyNodeFact.EMPTY_NODE_HASH, path=0, length=0, height=1
    )
    assert await empty_tree_1.get_children(ffc=ffc) == (empty_tree_0, empty_tree_0)

    # Build left subtree.
    # Combine left empty tree and right leaf.
    left_12 = VirtualPatriciaNode(bottom_node=leaf_hash_12, path=0, length=0, height=0)
    left_tree_1 = await VirtualPatriciaNode.combine(ffc=ffc, left=empty_tree_0, right=left_12)
    assert left_tree_1 == VirtualPatriciaNode(bottom_node=leaf_hash_12, path=1, length=1, height=1)

    # Get children on both forms.
    expected_children = (empty_tree_0, left_12)
    assert await left_tree_1.get_children(ffc=ffc) == expected_children
    non_canonical_node = await make_virtual_edge_non_canonical(ffc=ffc, node=left_tree_1)
    assert await non_canonical_node.get_children(ffc=ffc) == expected_children

    # Combine left edge node and right empty tree.
    left_tree_2 = await VirtualPatriciaNode.combine(ffc=ffc, left=left_tree_1, right=empty_tree_1)
    assert left_tree_2 == VirtualPatriciaNode(
        bottom_node=leaf_hash_12, path=int("01", 2), length=2, height=2
    )

    # Get children on both forms.
    expected_children = (left_tree_1, empty_tree_1)
    assert await left_tree_2.get_children(ffc=ffc) == expected_children
    non_canonical_node = await make_virtual_edge_non_canonical(ffc=ffc, node=left_tree_2)
    assert await non_canonical_node.get_children(ffc=ffc) == expected_children

    # Build right subtree.
    # Combine left leaf and right empty tree.
    leaf_30 = VirtualPatriciaNode(bottom_node=leaf_hash_30, path=0, length=0, height=0)
    right_tree_1 = await VirtualPatriciaNode.combine(ffc=ffc, left=leaf_30, right=empty_tree_0)
    assert right_tree_1 == VirtualPatriciaNode(bottom_node=leaf_hash_30, path=0, length=1, height=1)

    # Get children on both forms.
    expected_children = (leaf_30, empty_tree_0)
    assert await right_tree_1.get_children(ffc=ffc) == expected_children
    non_canonical_node = await make_virtual_edge_non_canonical(ffc=ffc, node=right_tree_1)
    assert await non_canonical_node.get_children(ffc=ffc) == expected_children

    # Combine left empty tree and right edge node.
    right_tree_2 = await VirtualPatriciaNode.combine(ffc=ffc, left=empty_tree_1, right=right_tree_1)
    assert right_tree_2 == VirtualPatriciaNode(
        bottom_node=leaf_hash_30, path=int("10", 2), length=2, height=2
    )

    # Get children on both forms.
    expected_children = (empty_tree_1, right_tree_1)
    assert await right_tree_2.get_children(ffc=ffc) == expected_children
    non_canonical_node = await make_virtual_edge_non_canonical(ffc=ffc, node=right_tree_2)
    assert await non_canonical_node.get_children(ffc=ffc) == expected_children

    # Build whole tree.
    # Combine left edge and right edge.
    left_node, right_node = await asyncio.gather(
        *(node.commit(ffc=ffc, facts=None) for node in (left_tree_2, right_tree_2))
    )
    binary_node_fact = BinaryNodeFact(left_node=left_node, right_node=right_node)
    root_hash = await binary_node_fact._hash(hash_func=ffc.hash_func)

    tree = await VirtualPatriciaNode.combine(ffc=ffc, left=left_tree_2, right=right_tree_2)
    assert tree == VirtualPatriciaNode(bottom_node=root_hash, path=0, length=0, height=3)
    left_edge_child, right_edge_child = await tree.get_children(ffc=ffc)
    assert (left_edge_child, right_edge_child) == (
        VirtualPatriciaNode(bottom_node=left_node, path=0, length=0, height=2),
        VirtualPatriciaNode(bottom_node=right_node, path=0, length=0, height=2),
    )

    # Test operations on the original edge children (now non-canonical).
    # Combining with an empty node yields another edge with length longer-by-one.
    parent_edge = await VirtualPatriciaNode.combine(
        ffc=ffc, left=left_edge_child, right=VirtualPatriciaNode.empty_node(height=2)
    )
    assert parent_edge == VirtualPatriciaNode(
        bottom_node=left_tree_2.bottom_node, path=int("001", 2), length=3, height=3
    )

    # Getting their children returns another edge with length shorter-by-one.
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
    tree = await tree._update(ffc=ffc, modifications=leaves.items())

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
    tree = await tree._update(ffc=ffc, modifications=updated_leaves.items())

    # Check get_leaves().
    updated_leaves = {**expected_leaves, **updated_leaves}
    assert (
        await tree._get_leaves(ffc=ffc, indices=leaves_range, fact_cls=LeafFact) == updated_leaves
    )

    # Compare to test util result.
    sorted_by_index_leaf_values = [updated_leaves[leaf_id].value for leaf_id in leaves_range]
    expected_root_hash = await tree.commit(ffc=ffc, facts=None)  # Root is an edge node.
    verify_root(leaves=sorted_by_index_leaf_values, expected_root_hash=expected_root_hash)
