from typing import Any, Collection, Tuple


def build_update_tree(height, modifications: Collection[Tuple[int, Any]]):
    """
    Constructs a tree from leaf updates. This is not a full binary tree. It is just the subtree
    induced by the modification leaves.
    Returns a tree. A tree is either:
     * None
     * a pair of trees
     * A leaf, which is a pair (leaf_index, modification)
    """
    # Bottom layer. This will prefer the last modification to an index.
    if len(modifications) == 0:
        return None

    # A layer is a dictionary from index in current merkle layer (0 to 2**layer_height) to a tree.
    # A tree is either None, a leaf, or a pair of trees.
    layer = dict(modifications)

    for _ in range(height):
        parents = set(index // 2 for index in layer.keys())
        layer = {index: (layer.get(index * 2), layer.get(index * 2 + 1)) for index in parents}
    assert len(layer) == 1
    # We reached layer_height=0, the top layer with only the root (with index 0).
    return layer[0]
