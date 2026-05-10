from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.math import (
    assert_in_range,
    assert_le,
    assert_lt_felt,
    assert_nn,
    assert_nn_le,
    assert_not_zero,
)
from starkware.cairo.common.patricia_utils import (
    MAX_LENGTH,
    NodeEdge,
    ParticiaGlobals,
    PatriciaUpdateConstants,
    Sibling,
    split_reads_writes,
)
from starkware.cairo.common.sponge_as_hash import SpongeHashBuiltin as HashBuiltin
from starkware.cairo.common.sponge_as_hash import sponge_hash2 as hash2

// Given an edge node hash, opens the hash using the preimage hint, and returns a NodeEdge object.
func open_edge{hash_ptr: HashBuiltin*, range_check_ptr}(globals: ParticiaGlobals*, node: felt) -> (
    edge: NodeEdge*
) {
    alloc_locals;
    local edge: NodeEdge*;

    %{
        ids.edge = segments.add()
        ids.edge.length, ids.edge.path, ids.edge.bottom = preimage[ids.node]
        ids.hash_ptr.result = ids.node - ids.edge.length
        if __patricia_skip_validation_runner is not None:
            # Skip validation of the preimage dict to speed up the VM. When this flag is set,
            # mistakes in the preimage dict will be discovered only in the prover.
            __patricia_skip_validation_runner.verified_addresses.add(
                ids.hash_ptr + ids.HashBuiltin.result)
    %}
    // Validity checks.
    assert_in_range(edge.length, 1, MAX_LENGTH + 1);
    assert_lt_felt(edge.path, globals.pow2[edge.length]);
    // Note: we do not explicitly verify that bottom_hash is binary or leaf here, since it will be
    // verified later in the algorithm if necessary.
    assert hash_ptr.x = edge.bottom;
    assert hash_ptr.y = edge.path;
    assert hash_ptr.c_in = 2;
    assert node = hash_ptr.result + edge.length;
    let hash_ptr = hash_ptr + HashBuiltin.SIZE;
    return (edge=edge);
}

// Traversal:
// See patricia_utils.py for details about the node representation.
// The patricia updates algorithm is composed of 2 traversals: on the previous and the new trees.
// Each traversal outputs:
// 1. update_ptr - Sorted list of leaf indices and values of the traversal.
// 2. siblings - A list of Sibling structs for the untraversed siblings of nodes we traversed:
//      For every node in the underlying merkle tree (in-order), if we only traverse one of its
//      children, the other child is encoded as a Sibling entry in this list.
//      The entry represents either a descent of a certain length or
//      a plain sibling with the given hash/leaf value (0 means empty subtree).
// If the tree traversals output the same leaf indices, and the same siblings, it is guaranteed
// that all the non traversed leaves have the same value.
// All traversal functions do at least one leaf update in the given subtree.
//
// Args:
// * height - The height of the subtree rooted at this node.
// * path - The path from the root to this node.
//
// Hint args:
// * node - The current traversal node update tree. See build_update_tree() for more info.
// * descent_map - A map from for all the nodes on which we should descend. See get_descents()
//     in patricia_utils.py.
// * common_args - Contains itself and other relevant hint variables in the context of a traversal.

// Traverses an empty subtree.
func traverse_empty{update_ptr: DictAccess*, range_check_ptr, siblings: Sibling*}(
    globals: ParticiaGlobals*, height: felt, path: felt
) {
    if (height == 0) {
        assert update_ptr.key = path;
        let value = [cast(update_ptr, felt*) + globals.access_offset];
        assert value = 0;
        let update_ptr = update_ptr + DictAccess.SIZE;
        return ();
    }

    // Decide non deterministically if we should traverse both children or just one.
    // This is more efficient that trying to determine it from update_ptr.
    %{
        from starkware.python.merkle_tree import decode_node
        left_child, right_child, case = decode_node(node)
        memory[ap] = 1 if case != 'both' else 0
    %}
    jmp skip_both if [ap] != 0, ap++;

    // Traverse both children.
    %{ vm_enter_scope(dict(node=left_child, **common_args)) %}
    traverse_empty(globals=globals, height=height - 1, path=path * 2);
    %{ vm_exit_scope() %}

    %{ vm_enter_scope(dict(node=right_child, **common_args)) %}
    traverse_empty(globals=globals, height=height - 1, path=path * 2 + 1);
    %{ vm_exit_scope() %}
    return ();

    skip_both:
    %{
        descend = descent_map.get((ids.height, ids.path))
        memory[ap] = 0 if descend is None else 1
    %}
    jmp skip_single if [ap] != 0, ap++;

    // Single.
    let child_bit = [ap];
    %{
        ids.child_bit = 0 if case == 'left' else 1
        new_node = left_child if case == 'left' else right_child
        vm_enter_scope(dict(node=new_node, **common_args))
    %}
    child_bit = child_bit * child_bit, ap++;
    assert siblings[0] = Sibling(type=0, value=0);
    let siblings = &siblings[1];
    traverse_empty(globals=globals, height=height - 1, path=path * 2 + child_bit);
    %{ vm_exit_scope() %}
    return ();

    skip_single:
    // Descend.
    tempvar length;
    tempvar word;
    %{ ids.length, ids.word = descend %}
    assert siblings[0] = Sibling(type=1, value=length);
    let siblings = &siblings[1];

    assert_in_range(length, 2, height + 1);
    tempvar length_pow2 = globals.pow2[length];
    assert_lt_felt(word, length_pow2);
    %{
        new_node = node
        for i in range(ids.length - 1, -1, -1):
            new_node = new_node[(ids.word >> i) & 1]
        vm_enter_scope(dict(node=new_node, **common_args))
    %}
    traverse_empty(globals=globals, height=height - length, path=path * length_pow2 + word);
    %{ vm_exit_scope() %}
    return ();
}

// Traverses a subtree rooted at the given NodeEdge.
func traverse_edge{
    hash_ptr: HashBuiltin*, range_check_ptr, update_ptr: DictAccess*, siblings: Sibling*
}(globals: ParticiaGlobals*, height: felt, path: felt, edge: NodeEdge) {
    if (edge.length == 0) {
        return traverse_binary_or_leaf(globals=globals, height=height, path=path, node=edge.bottom);
    }

    alloc_locals;

    %{
        descend = descent_map.get((ids.height, ids.path))
        memory[ap] = 0 if descend is None else 1
    %}
    jmp descend if [ap] != 0, ap++;

    // Extract one bit from the edge. edge.length is guaranteed to be >= 1.
    local new_length = edge.length - 1;
    local bound = globals.pow2[new_length];
    local bit;
    %{ ids.bit = (ids.edge.path >> ids.new_length) & 1 %}
    bit * bit = bit;
    local new_path = edge.path - bit * bound;
    assert_lt_felt(new_path, bound);
    local new_edge: NodeEdge = NodeEdge(length=new_length, path=new_path, bottom=edge.bottom);

    // Decide case.
    %{
        from starkware.python.merkle_tree import decode_node
        left_child, right_child, case = decode_node(node)
        memory[ap] = int(case != 'both')
    %}
    jmp skip_both if [ap] != 0, ap++;

    // Traverse edge regular.

    // Case 1: the updates are in both subtrees.
    //
    // (1) traverse both children.
    // (2) No sibling.

    // Traverse both children.
    if (bit == 0) {
        %{ vm_enter_scope(dict(node=left_child, **common_args)) %}
        traverse_edge(globals=globals, height=height - 1, path=path * 2, edge=new_edge);
        %{ vm_exit_scope() %}
        local hash_ptr: HashBuiltin* = hash_ptr;

        %{ vm_enter_scope(dict(node=right_child, **common_args)) %}
        traverse_empty(globals=globals, height=height - 1, path=path * 2 + 1);
        %{ vm_exit_scope() %}
        return ();
    } else {
        %{ vm_enter_scope(dict(node=left_child, **common_args)) %}
        traverse_empty(globals=globals, height=height - 1, path=path * 2);
        %{ vm_exit_scope() %}

        %{ vm_enter_scope(dict(node=right_child, **common_args)) %}
        traverse_edge(globals=globals, height=height - 1, path=path * 2 + 1, edge=new_edge);
        %{ vm_exit_scope() %}
        return ();
    }

    skip_both:
    %{ memory[ap] = int(case == 'right') ^ ids.bit %}
    jmp skip_non_empty_child if [ap] != 0, ap++;

    // Case 2: all the updates are in one of the two subtrees and the other subtree is zero
    //   (in particular, all the updates are in the direction of the edge).
    //
    // (1) traverse the non-empty child.
    // (2) sibling is zero.

    // Traverse the non-empty child.
    assert siblings[0] = Sibling(type=0, value=0);
    let siblings = &siblings[1];
    %{
        new_node = left_child if ids.bit == 0 else right_child
        vm_enter_scope(dict(node=new_node, **common_args))
    %}
    traverse_edge(globals=globals, height=height - 1, path=path * 2 + bit, edge=new_edge);
    %{ vm_exit_scope() %}
    return ();

    skip_non_empty_child:
    // Case 3: all the updates are in one of the two subtrees and that subtree is zero
    //   (in particular, all the updates have zero values).
    //
    // (1) Traverse the empty child to visit the updates.
    // (2) Its sibling is:
    //   (a) If edge.length > 1, an edge of length smaller by 1:
    //       H(edge.bottom, new_path) + (edge.length - 1)
    //   (b) If edge.length = 1, the sibling is edge.bottom.
    //
    // We require height == 1 => edge.length = 1, for the following to be true:
    // If edge.length > 1, then height > 1 => sibling is not a leaf.
    // In this case the sibling `H(edge.bottom, new_path) + (edge.length - 1)` represents
    // a proper edge. Since it's the sibling, it is identical in both prev and new trees, and
    // therefore (as it appears in the prev tree), it must be a valid edge
    // (its length is <= height and its bottom is not empty and not an edge).

    if (height == 1) {
        assert edge.length = 1;
    }

    // Traverse the empty child.
    local range_check_ptr = range_check_ptr;
    local new_hash_ptr: HashBuiltin*;

    // Reserve a spot for the sibling. It is more efficient to compute it after the recursive
    // traversal.
    let current_sibling = &siblings[0];
    let siblings = &siblings[1];

    // Traverse empty side.
    %{
        new_node = left_child if ids.bit == 1 else right_child
        vm_enter_scope(dict(node=new_node, **common_args))
    %}
    traverse_empty(globals=globals, height=height - 1, path=path * 2 + 1 - bit);
    %{ vm_exit_scope() %}

    // Check that the resulting topology is valid.
    //
    // To illustrate, consider the following example: an edge A->B of length L, children C,X of B,
    // and a deleted child D of C (D may be a deleted leaf, or a subtree that becomes empty):
    //
    //     A                A
    //      \                \
    //       \ L              \
    //        \                \ L+1
    //         B        ->      \
    //       /   \               \
    //      C     X               X
    //       \
    //        D
    //
    // By the traversal of the previous tree, we know X is a valid node, but we do not guarantee the
    // type of node X is - it could potentially be an edge node, in which case the above drawing is
    // an invalid tree topology (if X is the bottom of an edge A->X, then X cannot be an edge, as
    // two consecutive edges is illegal in a Patricia tree).
    // Without the following check, a malicious prover could inject an invalid edge node starting at
    // X. This is especially important for allowing escape-hatch mechanisms: if a user only has the
    // data-availability (state of the leaves), in order to prove the state of any leaf the user
    // must rely on the tree being well-formed.
    if (edge.length == 1) {
        // In this case, the sibling is the bottom of our edge.
        // Make sure edge.bottom is binary or a non-zero leaf.
        assert [current_sibling] = Sibling(type=0, value=edge.bottom);
        if (height != 1) {
            // This check should only be done on the new tree.
            if (globals.access_offset == 2) {
                assert hash_ptr.c_in = 2;
                hash_ptr.result = edge.bottom;
                %{
                    ids.hash_ptr.x, ids.hash_ptr.y = preimage[ids.edge.bottom]
                    if __patricia_skip_validation_runner:
                        # Skip validation of the preimage dict to speed up the VM. When this flag is
                        # set, mistakes in the preimage dict will be discovered only in the prover.
                        __patricia_skip_validation_runner.verified_addresses.add(
                            ids.hash_ptr + ids.HashBuiltin.result)
                %}
                let hash_ptr = hash_ptr + HashBuiltin.SIZE;
                return ();
            } else {
                return ();
            }
        } else {
            // As `height = edge.length = 1`, edge.bottom is a leaf and we only need to check that
            // it is not zero.
            assert_not_zero(edge.bottom);
        }
        return ();
    }

    // This is the case where we split an edge.
    let (hash) = hash2(edge.bottom, new_edge.path);
    assert [current_sibling] = Sibling(type=0, value=hash + new_edge.length);
    return ();

    descend:
    // Descent: descend `length` (>= 2) levels along the edge in a single step.
    // `word` represents the next `length` bits of the path.
    //
    // (1) Recurse on the truncated edge.
    // (2) Record `length` as a Sibling entry in the siblings list.

    local length;
    local word;
    %{ ids.length, ids.word = descend %}
    assert siblings[0] = Sibling(type=1, value=length);
    let siblings = &siblings[1];

    // Check that the descend is valid.
    assert_in_range(length, 2, edge.length + 1);
    tempvar length_pow2 = globals.pow2[length];
    tempvar new_length = edge.length - length;
    tempvar new_length_pow2 = globals.pow2[new_length];
    tempvar new_path = edge.path - word * new_length_pow2;
    assert_lt_felt(word, length_pow2);
    assert_lt_felt(new_path, new_length_pow2);

    let new_edge: NodeEdge = NodeEdge(length=new_length, path=new_path, bottom=edge.bottom);
    %{
        new_node = node
        for i in range(ids.length - 1, -1, -1):
            new_node = new_node[(ids.word >> i) & 1]
        vm_enter_scope(dict(node=new_node, **common_args))
    %}
    traverse_edge(
        globals=globals, height=height - length, path=path * length_pow2 + word, edge=new_edge
    );
    %{ vm_exit_scope() %}

    return ();
}

// Traverses a subtree rooted at the given binary or leaf node with given hash/value.
func traverse_binary_or_leaf{
    hash_ptr: HashBuiltin*, range_check_ptr, update_ptr: DictAccess*, siblings: Sibling*
}(globals: ParticiaGlobals*, height: felt, path: felt, node: felt) {
    if (height == 0) {
        // Leaf.
        assert update_ptr.key = path;
        tempvar value = [cast(update_ptr, felt*) + globals.access_offset];
        assert value = node;
        assert_not_zero(value);
        let update_ptr = update_ptr + DictAccess.SIZE;
        return ();
    }

    alloc_locals;

    // Binary.
    let current_hash = hash_ptr;
    let hash_ptr = hash_ptr + HashBuiltin.SIZE;
    assert current_hash.c_in = 2;
    assert current_hash.result = node;

    %{
        from starkware.python.merkle_tree import decode_node
        left_child, right_child, case = decode_node(node)
        left_hash, right_hash = preimage[ids.node]

        # Fill non deterministic hashes.
        hash_ptr = ids.current_hash.address_
        memory[hash_ptr + ids.HashBuiltin.x] = left_hash
        memory[hash_ptr + ids.HashBuiltin.y] = right_hash

        if __patricia_skip_validation_runner:
            # Skip validation of the preimage dict to speed up the VM. When this flag is set,
            # mistakes in the preimage dict will be discovered only in the prover.
            __patricia_skip_validation_runner.verified_addresses.add(
                hash_ptr + ids.HashBuiltin.result)

        memory[ap] = int(case != 'both')
    %}
    jmp skip_both if [ap] != 0, ap++;

    // Case 1: the updates are in both subtrees.
    //
    // (1) Traverse both children.
    // (2) No sibling.

    // Traverse both children.
    %{ vm_enter_scope(dict(node=left_child, **common_args)) %}
    traverse_non_empty(globals=globals, height=height - 1, path=path * 2, node=current_hash.x);
    %{ vm_exit_scope() %}
    tempvar left_child = path * 2;
    %{ vm_enter_scope(dict(node=right_child, **common_args)) %}
    traverse_non_empty(
        globals=globals, height=height - 1, path=left_child + 1, node=current_hash.y
    );
    %{ vm_exit_scope() %}
    return ();

    skip_both:
    %{ memory[ap] = int(case != 'left') %}
    jmp skip_left if [ap] != 0, ap++;

    // Case 2: the updates are only in the left subtree.
    //
    // (1) Traverse the left child.
    // (2) The sibling is the right child (must be non-zero).

    // Left.
    tempvar sib = current_hash.y;
    assert_not_zero(sib);
    assert siblings[0] = Sibling(type=0, value=sib);
    let siblings = &siblings[1];
    %{ vm_enter_scope(dict(node=left_child, **common_args)) %}
    traverse_non_empty(globals=globals, height=height - 1, path=path * 2, node=current_hash.x);
    %{ vm_exit_scope() %}
    return ();

    skip_left:
    %{ assert case == 'right' %}

    // Case 3: the updates are only in the right subtree.
    //
    // (1) Traverse the right child.
    // (2) The sibling is the left child (must be non-zero).

    // Right.
    tempvar sib = current_hash.x;
    assert_not_zero(sib);
    assert siblings[0] = Sibling(type=0, value=sib);
    let siblings = &siblings[1];
    %{ vm_enter_scope(dict(node=right_child, **common_args)) %}
    traverse_non_empty(globals=globals, height=height - 1, path=path * 2 + 1, node=current_hash.y);
    %{ vm_exit_scope() %}
    return ();
}

// Traverses some of the leaves in the subtree rooted at node.
func traverse_node{
    hash_ptr: HashBuiltin*, range_check_ptr, update_ptr: DictAccess*, siblings: Sibling*
}(globals: ParticiaGlobals*, height: felt, path: felt, node: felt) {
    if (node == 0) {
        // Empty:
        traverse_empty(globals=globals, height=height, path=path);
        return ();
    }

    return traverse_non_empty(globals=globals, height=height, path=path, node=node);
}

// Same as traverse_node, but disallows empty nodes.
func traverse_non_empty{
    hash_ptr: HashBuiltin*, range_check_ptr, update_ptr: DictAccess*, siblings: Sibling*
}(globals: ParticiaGlobals*, height: felt, path: felt, node: felt) {
    %{ memory[ap] = 1 if ids.height == 0 or len(preimage[ids.node]) == 2 else 0 %}
    jmp binary if [ap] != 0, ap++;
    // Edge.
    let (edge) = open_edge(globals=globals, node=node);
    traverse_edge(globals=globals, height=height, path=path, edge=[edge]);
    return ();

    // Binary.
    binary:
    return traverse_binary_or_leaf(globals=globals, height=height, path=path, node=node);
}

// Computes a power of 2 array. In other words, writes the sequence 1, 2, 4, 8, ... to the given
// pointer (with the given length).
func compute_pow2_array(pow2_ptr: felt*, cur: felt, n: felt) {
    if (n == 0) {
        return ();
    }
    assert [pow2_ptr] = cur;
    return compute_pow2_array(pow2_ptr=pow2_ptr + 1, cur=cur * 2, n=n - 1);
}

// Performs an efficient update of multiple leaves in a Patricia Merkle tree.
//
// Arguments:
// update_ptr - a list of DictAccess instances sorted by key (e.g., the result of squash_dict).
// height - the height of the merkle tree.
// prev_root - the value of the root before the update.
// new_root - the value of the root after the update.
//
// Hint arguments:
// preimage - a dictionary from the hash value of a Patricia node to either
//   1. a pair of children values, for binary nodes.
//   2. a triplet of (length, path, bottom), for edge nodes.
//
// Implicit arguments:
// hash_ptr - hash builtin pointer.
//
// Assumptions: The keys in the update_ptr list are unique and sorted.
// Guarantees: All the keys in the update_ptr list are < 2**height.
func patricia_update{hash_ptr: HashBuiltin*, range_check_ptr}(
    update_ptr: DictAccess*, n_updates: felt, height: felt, prev_root: felt, new_root: felt
) {
    let (patricia_update_constants: PatriciaUpdateConstants*) = patricia_update_constants_new();
    patricia_update_using_update_constants(
        patricia_update_constants=patricia_update_constants,
        update_ptr=update_ptr,
        n_updates=n_updates,
        height=height,
        prev_root=prev_root,
        new_root=new_root,
    );

    return ();
}

func patricia_update_constants_new() -> (patricia_update_constants: PatriciaUpdateConstants*) {
    // Compute power-of-2 array for patricia updates.
    alloc_locals;
    let (local globals_pow2: felt*) = alloc();
    compute_pow2_array(pow2_ptr=globals_pow2, cur=1, n=MAX_LENGTH + 1);
    return (patricia_update_constants=new PatriciaUpdateConstants(globals_pow2=globals_pow2));
}

func patricia_update_using_update_constants{hash_ptr: HashBuiltin*, range_check_ptr}(
    patricia_update_constants: PatriciaUpdateConstants*,
    update_ptr: DictAccess*,
    n_updates: felt,
    height: felt,
    prev_root: felt,
    new_root: felt,
) {
    if (n_updates == 0) {
        prev_root = new_root;
        return ();
    }

    let update_end = &update_ptr[n_updates];

    alloc_locals;

    // Traverse prev tree.
    let (local original_siblings: Sibling*) = alloc();
    let siblings = original_siblings;
    with siblings {
        traverse_prev_tree(
            patricia_update_constants=patricia_update_constants,
            update_ptr=update_ptr,
            n_updates=n_updates,
            height=height,
            prev_root=prev_root,
            new_root=new_root,
        );
    }
    local siblings_end: Sibling* = siblings;

    // Traverse new tree.
    let siblings = original_siblings;
    %{ vm_enter_scope(dict(node=node, **common_args)) %}
    // Note: the height is enforced to be smaller or equal to MAX_LENGTH in `traverse_prev_tree`.
    with update_ptr, siblings {
        traverse_node(
            globals=new ParticiaGlobals(
                pow2=patricia_update_constants.globals_pow2, access_offset=DictAccess.new_value
            ),
            height=height,
            path=0,
            node=new_root,
        );
    }
    %{ vm_exit_scope() %}
    assert update_ptr = update_end;
    assert siblings = siblings_end;
    return ();
}

// Traverses the previous (pre-update) tree during a Patricia Merkle tree update operation.
//
// Guarantees:
// * After execution, update_ptr will have advanced by n_updates entries.
// * The siblings list will be populated with the sibling encoding from the previous tree.
func traverse_prev_tree{hash_ptr: HashBuiltin*, range_check_ptr, siblings: Sibling*}(
    patricia_update_constants: PatriciaUpdateConstants*,
    update_ptr: DictAccess*,
    n_updates: felt,
    height: felt,
    prev_root: felt,
    new_root: felt,
) {
    %{
        from starkware.cairo.common.patricia_utils import canonic, patricia_guess_descents
        from starkware.python.merkle_tree import build_update_tree

        # Build modifications list.
        modifications = []
        DictAccess_key = ids.DictAccess.key
        DictAccess_new_value = ids.DictAccess.new_value
        DictAccess_SIZE = ids.DictAccess.SIZE
        for i in range(ids.n_updates):
            curr_update_ptr = ids.update_ptr.address_ + i * DictAccess_SIZE
            modifications.append((
                memory[curr_update_ptr + DictAccess_key],
                memory[curr_update_ptr + DictAccess_new_value]))

        node = build_update_tree(ids.height, modifications)
        descent_map = patricia_guess_descents(
            ids.height, node, preimage, ids.prev_root, ids.new_root)
        del modifications
        __patricia_skip_validation_runner = globals().get(
            '__patricia_skip_validation_runner')

        common_args = dict(
            preimage=preimage, descent_map=descent_map,
            __patricia_skip_validation_runner=__patricia_skip_validation_runner)
        common_args['common_args'] = common_args
    %}

    let update_end: DictAccess* = &update_ptr[n_updates];

    // Traverse prev tree.
    assert_le(height, MAX_LENGTH);
    %{ vm_enter_scope(dict(node=node, **common_args)) %}
    with update_ptr {
        traverse_node(
            globals=new ParticiaGlobals(
                pow2=patricia_update_constants.globals_pow2, access_offset=DictAccess.prev_value
            ),
            height=height,
            path=0,
            node=prev_root,
        );
    }
    %{ vm_exit_scope() %}
    assert update_ptr = update_end;
    return ();
}

// A variant of patricia_update that is optimized for read-heavy workloads.
//
// Performs the same verification as patricia_update_using_update_constants, but with the following
// change: it splits the updates into reads and writes, then processes them differently:
//
// 1. Calls patricia_update_using_update_constants() with ONLY the
//    writes. This is the expensive operation that traverses both prev and new trees.
//
// 2. For reads, only traverses the PREVIOUS tree (not both trees).
//    Since reads don't change the tree structure, we only need to verify that the claimed values
//    exist in the previous tree. We don't need to traverse the new tree because it's identical
//    to the previous tree at these positions.
//
// Assumptions: Same as patricia_update_using_update_constants.
func patricia_update_read_optimized{hash_ptr: HashBuiltin*, range_check_ptr}(
    patricia_update_constants: PatriciaUpdateConstants*,
    update_ptr: DictAccess*,
    n_updates: felt,
    height: felt,
    prev_root: felt,
    new_root: felt,
) {
    if (n_updates == 0) {
        prev_root = new_root;
        return ();
    }

    alloc_locals;

    // Split updates into reads and writes.
    let (
        local n_reads: felt, local reads: DictAccess*, n_writes: felt, writes: DictAccess*
    ) = split_reads_writes(n_updates=n_updates, update_ptr=update_ptr);

    // Traverse both trees using only the writes.
    patricia_update_using_update_constants(
        patricia_update_constants=patricia_update_constants,
        update_ptr=writes,
        n_updates=n_writes,
        height=height,
        prev_root=prev_root,
        new_root=new_root,
    );

    if (n_reads == 0) {
        return ();
    }

    // Traverse the previous tree using the reads to verify their values.
    let (siblings: Sibling*) = alloc();
    traverse_prev_tree{siblings=siblings}(
        patricia_update_constants=patricia_update_constants,
        update_ptr=reads,
        n_updates=n_reads,
        height=height,
        prev_root=prev_root,
        new_root=new_root,
    );
    return ();
}
