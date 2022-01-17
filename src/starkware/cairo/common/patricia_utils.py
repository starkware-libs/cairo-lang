"""
Starkware's Merkle-Patricia tree is based on this representation:
Each node can be one of these:
1. Empty, with value of 0.
2. Edge node, with value of hash(bottom_node, edge_path) + edge_length.
3. Binary node, with value of hash(left, right).

An edge node represents a path in a maximal subtree with a single non-empty node.
for example, the following is encoded
#    0
#  0   0
# 0 h 0 0
as
(2, 1, h)

If that maximal subtree is trivial, it is encoded as (0, 0, h) where h is the value of
the leaf or the hash corresponding to that subtree.
"""

from typing import Any, Iterable, List, Optional, Tuple

from starkware.cairo.lang.vm.crypto import pedersen_hash
from starkware.python.math_utils import is_power_of_2
from starkware.starkware_utils.commitment_tree.update_tree import UpdateTree

Triplet = Tuple[int, int, int]

# Represents an empty node.
EMPTY = (0, 0, 0)


def compute_patricia_from_leaves_for_test(leaves, hash_func):
    """
    Computes the root of a Merkle-Patricia tree from the list of all the leaves.
    This function is not efficient, and should only be used for tests.
    Returns:
    * The hash of the root.
    * A preimage dict from hash to either (left, right) for binary nodes, or
        (edge_length, edge_path, bottom_node) for edge nodes.
    * node_at_path - a dictionary from height, path to a node encoding triplet.
    """
    assert is_power_of_2(len(leaves))
    preimage = {}
    node_at_path = {}

    def hash_node(e):
        length, path, bottom = e
        if length == 0:
            return bottom
        res = hash_func(bottom, path) + length
        preimage[res] = e
        return res

    # All the nodes are stored as edge nodes representation of non negative length:
    #   (length, path, hash of bottom node).
    layer = [(0, 0, x) for x in leaves]
    height = 0
    while len(layer) > 1:
        node_at_path.update({(height, i): x for i, x in enumerate(layer)})
        next_layer = []
        for left, right in zip(layer[::2], layer[1::2]):
            (l_len, l_path, l_bottom), (r_len, r_path, r_bottom) = left, right

            if left == EMPTY and right == EMPTY:
                next_node = EMPTY
            elif left == EMPTY:
                next_node = (r_len + 1, r_path + 2 ** r_len, r_bottom)
            elif right == EMPTY:
                next_node = (l_len + 1, l_path, l_bottom)
            else:
                next_node = (0, 0, hash_func(hash_node(left), hash_node(right)))
            next_layer.append(next_node)

        layer = next_layer
        height += 1
    (root,) = layer
    node_at_path[height, 0] = root
    return hash_node(root), preimage, node_at_path


def hash_node(e: Triplet) -> int:
    length, path, bottom = e
    if length == 0:
        return bottom
    return pedersen_hash(bottom, path) + length


def get_children(preimage, node: Triplet) -> Tuple[Triplet, Triplet]:
    """
    Retrieves the children of a node. Assumes canonic representation.
    """
    length, word, node_hash = node
    if length == 0:
        if node_hash == 0:
            left, right = 0, 0
        else:
            left, right = preimage[node_hash]
        return canonic(preimage, left), canonic(preimage, right)
    if word >> (length - 1) == 0:
        return ((length - 1, word, node_hash), EMPTY)
    return EMPTY, ((length - 1, word - (1 << (length - 1)), node_hash))


def preimage_tree(height: int, preimage: dict, node: Triplet):
    """
    Builds a tree structure similar to build_update_tree(), from a root hash, and a preimage
    dictionary.
    Returns a generator as follows:
    * if node is a leaf: [0]
    * Otherwise: [left, right] where each child is either None if empty or a generator defined
      recursively.
    Note that this does not necessarily traverse the entire tree. The caller may open the branches
    as they wish.
    """
    if height == 0:
        yield 0
        return
    left, right = get_children(preimage, node)
    yield None if left == EMPTY else preimage_tree(height - 1, preimage, left)
    yield None if right == EMPTY else preimage_tree(height - 1, preimage, right)


# NodeType should be Optional[Iterable[NodeType]], but mypy does not support recursion yet.
NodeType = Optional[Iterable[Any]]


def get_descents(height: int, path: int, nodes: List[NodeType]):
    """
    Builds a descent map given multiple trees.
    A descent is a maximal subpath s.t.
    1. In each tree, the authentication subpath consists of empty nodes.
    2. The subpath is longer than 1.

    Returns descents as a map: (height, path_to_upper_node) -> (subpath_length, subpath).
    The function does not return descents that begin at an empty node in the first tree.

    Note: This function will be called with 3 trees:
      The modifications tree, previous tree, new tree.

    Args:
    height - height of the current node. The length of a path from the node to a leaf.
    path - path from the root to the current node.
    nodes - a list of 'node' structures, similar to build_update_tree().
      In particular, it is assumed that a non empty node cannot have two empty children.
    """

    if nodes[0] is None:
        return {}

    # Find longest edge.
    orig_height = height
    orig_path = path

    # Traverse all the trees simultaneously, as long as they all satisfy the descent condition,
    # to find the maximal descent subpath.
    while height > 0:
        lefts = []
        rights = []
        for node in nodes:
            if node is None:
                node = None, None
            left, right = node
            lefts.append(left)
            rights.append(right)

        if all(left is None for left in lefts):
            nodes = rights
            path = path * 2 + 1
        elif all(right is None for right in rights):
            nodes = lefts
            path = path * 2
        else:
            break
        height -= 1

    length = orig_height - height
    res = {}
    # length <= 1 is not a descent.
    if length > 1:
        res[orig_height, orig_path] = length, path % 2 ** length

    if height > 0:
        res.update(get_descents(height - 1, path * 2, lefts))
        res.update(get_descents(height - 1, path * 2 + 1, rights))
    return res


def compute_siblings_from_tree(height, node: UpdateTree, node_at_path, descent_map, path=0):
    """
    Returns the encoding of the list of untraversed siblings. See the documentation in
    patricia.cairo for more details.
    """
    if not isinstance(node, tuple):
        assert height == 0
        # Leaf node.
        return []
    left, right = node
    if left is None:
        res = [hash_node(node_at_path[height - 1, path * 2])] + compute_siblings_from_tree(
            height - 1, right, node_at_path, descent_map, path * 2 + 1
        )
    elif right is None:
        res = [hash_node(node_at_path[height - 1, path * 2 + 1])] + compute_siblings_from_tree(
            height - 1, left, node_at_path, descent_map, path * 2
        )
    else:
        res = compute_siblings_from_tree(
            height - 1, left, node_at_path, descent_map, path * 2
        ) + compute_siblings_from_tree(height - 1, right, node_at_path, descent_map, path * 2 + 1)

    descend = descent_map.get((height, path))
    if descend is None:
        return res

    # If current node has a descent, siblings should be compressed.
    # A descent of length L, compresses L zeros into a single element, L.
    length, _ = descend
    assert res[:length] == [0] * length
    return [length] + res[length:]


def canonic(preimage: dict, node_hash: int) -> Triplet:
    """
    Returns the canonic encoding of a node hash as a triplet.
    This implies that if the returned encoding is (0, 0, node_hash), then node_hash is not an edge
    node.
    """
    back = preimage.get(node_hash, ())
    if len(back) == 3:
        return back
    else:
        return (0, 0, node_hash)


def patricia_guess_descents(height, node, preimage, prev_root, new_root):
    """
    Builds a descent map for a Patricia update. See get_descents().
    node - The modification tree for the patricia update, given by build_update_tree().
    """
    node_prev = preimage_tree(height, preimage, canonic(preimage, prev_root))
    node_new = preimage_tree(height, preimage, canonic(preimage, new_root))
    return get_descents(height, 0, [node, node_prev, node_new])
