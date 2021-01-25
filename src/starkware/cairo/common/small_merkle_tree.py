from typing import Collection, Dict, Tuple

from starkware.cairo.lang.vm.crypto import pedersen_hash


class MerkleTree:
    def __init__(self, tree_height: int, default_leaf: int):
        self.tree_height = tree_height
        self.default_leaf = default_leaf
        # A map from node indices to their values.
        self.node_values: Dict[int, int] = {}
        # A map from node hash to its two children.
        self.preimage: Dict[int, Tuple[int, int]] = {}

    def compute_merkle_root(self, modifications: Collection[Tuple[int, int]]):
        """
        Applies the given modifications (a list of (leaf index, value)) to the tree and returns
        the Merkle root.
        """
        default_node = self.default_leaf
        indices = set()
        leaves_offset = 2 ** self.tree_height
        for index, value in modifications:
            node_index = leaves_offset + index
            self.node_values[node_index] = value
            indices.add(node_index // 2)
        for _ in range(self.tree_height):
            new_indices = set()
            while len(indices) > 0:
                index = indices.pop()
                left = self.node_values.get(2 * index, default_node)
                right = self.node_values.get(2 * index + 1, default_node)
                self.node_values[index] = node_hash = pedersen_hash(left, right)
                self.preimage[node_hash] = (left, right)
                new_indices.add(index // 2)
            default_node = pedersen_hash(default_node, default_node)
            indices = new_indices
        assert indices == {0}
        return self.node_values[1]


def get_preimage_dictionary(
        initial_leaves: Collection[Tuple[int, int]], modifications: Collection[Tuple[int, int]],
        tree_height: int, default_leaf: int) -> Tuple[int, int, Dict[int, Tuple[int, int]]]:
    """
    Given a set of initial leaves and a set of modifications
    (both are maps from leaf index to value, where all the leaves in `modifications` appear
    in `initial_leaves`).
    Constructs two merkle trees, before and after the modifications.
    Returns (root_before, root_after, preimage) where preimage is a dictionary from a node to
    its two children.
    """

    merkle_tree = MerkleTree(tree_height=tree_height, default_leaf=default_leaf)

    root_before = merkle_tree.compute_merkle_root(modifications=initial_leaves)
    root_after = merkle_tree.compute_merkle_root(modifications=modifications)

    return root_before, root_after, merkle_tree.preimage
