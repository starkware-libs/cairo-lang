from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.hash import hash2
from starkware.cairo.common.math import (
    assert_in_range, assert_le, assert_lt_felt, assert_nn, assert_nn_le, assert_not_zero)

# Maximum length of an edge.
const MAX_LENGTH = 251

# A struct of globals that are passed throughout the algorithm.
struct ParticiaGlobals:
    # An array of size MAX_LENGTH, where pow2[i] = 2**i.
    member pow2 : felt*
    # Offset of the relevant value field in DictAccess.
    # 1 if the previous tree is traversed and 2 if the new tree is traversed.
    member access_offset : felt
end

# Represents an edge node: a subtree with a path, s.t. all leaves not under that path are 0.
struct NodeEdge:
    member length : felt
    member path : felt
    member bottom : felt
end

# Given an edge node hash, opens the hash using the preimage hint, and returns a NodeEdge object.
func open_edge{hash_ptr : HashBuiltin*, range_check_ptr}(
        globals : ParticiaGlobals*, node : felt) -> (edge : NodeEdge*):
    alloc_locals
    local edge : NodeEdge*

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
    # Validity checks.
    assert_in_range(edge.length, 1, MAX_LENGTH + 1)
    assert_lt_felt(edge.path, globals.pow2[edge.length])
    # Note: we do not explicitly verify that bottom_hash is binary or leaf here, since it will be
    # verified later in the algorithm if necessary.
    assert hash_ptr.x = edge.bottom
    assert hash_ptr.y = edge.path
    assert node = hash_ptr.result + edge.length
    let hash_ptr = hash_ptr + HashBuiltin.SIZE
    return (edge=edge)
end

# Traversal:
# See patricia_utils.py for details about the node representation.
# The patricia updates algorithm is composed of 2 traversals: on the previous and the new trees.
# Each traversal outputs:
# 1. update_ptr - Sorted list of leaf indices and values of the traversal.
# 2. siblings - An encoding of the list of untraversed siblings of the nodes we traversed:
#      For every node in the underlying merkle tree (in-order), if we only traverse one of its
#      children, the other child will be encoded in this list.
#      The encoding is as follows:
#      * A value of 0 means a 0-sibling - empty subtree.
#      * A value of n, for 2 <= n <= MAX_LENGTH means n non leaf 0-siblings.
#      * Otherwise, the value is the sibling value.
#          It may be a hash (which we assume to be > MAX_LENGTH) for an inner node or a value
#          (any felt) for a leaf sibling.
# If the tree traversals output the same leaf indices, and the same siblings, it is guaranteed
# that all the non traversed leaves have the same value.
# All traversal functions do at least one leaf update in the given subtree.
#
# Args:
# * height - The height of the subtree rooted at this node.
# * path - The path from the root to this node.
#
# Hint args:
# * node - The current traversal node update tree. See build_update_tree() for more info.
# * descent_map - A map from for all the nodes on which we should descend. See get_descents()
#     in patricia_utils.py.
# * common_args - Contains itself and other relevant hint variables in the context of a traversal.

# Traverses an empty subtree.
func traverse_empty{update_ptr : DictAccess*, range_check_ptr, siblings : felt*}(
        globals : ParticiaGlobals*, height : felt, path : felt):
    if height == 0:
        assert update_ptr.key = path
        let value = [cast(update_ptr, felt*) + globals.access_offset]
        assert value = 0
        let update_ptr = update_ptr + DictAccess.SIZE
        return ()
    end

    # Decide non deterministically if we should traverse both children or just one.
    # This is more efficient that trying to determine it from update_ptr.
    %{
        from starkware.python.merkle_tree import decode_node
        left_child, right_child, case = decode_node(node)
        memory[ap] = 1 if case != 'both' else 0
    %}
    jmp skip_both if [ap] != 0; ap++

    # Traverse both children.
    %{ vm_enter_scope(dict(node=left_child, **common_args)) %}
    traverse_empty(globals=globals, height=height - 1, path=path * 2)
    %{ vm_exit_scope() %}

    %{ vm_enter_scope(dict(node=right_child, **common_args)) %}
    traverse_empty(globals=globals, height=height - 1, path=path * 2 + 1)
    %{ vm_exit_scope() %}
    return ()

    skip_both:
    %{
        descend = descent_map.get((ids.height, ids.path))
        memory[ap] = 0 if descend is None else 1
    %}
    jmp skip_single if [ap] != 0; ap++

    # Single.
    let child_bit = [ap]
    %{
        ids.child_bit = 0 if case == 'left' else 1
        new_node = left_child if case == 'left' else right_child
        vm_enter_scope(dict(node=new_node, **common_args))
    %}
    child_bit = child_bit * child_bit; ap++
    assert [siblings] = 0
    let siblings = siblings + 1
    traverse_empty(globals=globals, height=height - 1, path=path * 2 + child_bit)
    %{ vm_exit_scope() %}
    return ()

    skip_single:
    # Descend.
    tempvar word
    %{ memory[ids.siblings], ids.word = descend %}
    tempvar length = [siblings]
    let siblings = siblings + 1

    assert_in_range(length, 2, height + 1)
    tempvar length_pow2 = globals.pow2[length]
    assert_lt_felt(word, length_pow2)
    %{
        new_node = node
        for i in range(ids.length - 1, -1, -1):
            new_node = new_node[(ids.word >> i) & 1]
        vm_enter_scope(dict(node=new_node, **common_args))
    %}
    traverse_empty(globals=globals, height=height - length, path=path * length_pow2 + word)
    %{ vm_exit_scope() %}
    return ()
end

# Traverses a subtree rooted at the given NodeEdge.
func traverse_edge{
        hash_ptr : HashBuiltin*, range_check_ptr, update_ptr : DictAccess*, siblings : felt*}(
        globals : ParticiaGlobals*, height : felt, path : felt, edge : NodeEdge):
    if edge.length == 0:
        return traverse_binary_or_leaf(globals=globals, height=height, path=path, node=edge.bottom)
    end

    alloc_locals

    %{
        descend = descent_map.get((ids.height, ids.path))
        memory[ap] = 0 if descend is None else 1
    %}
    jmp descend if [ap] != 0; ap++

    # Extract one bit from the edge. edge.length is guaranteed to be >= 1.
    local new_length = edge.length - 1
    local bound = globals.pow2[new_length]
    local bit
    %{ ids.bit = (ids.edge.path >> ids.new_length) & 1 %}
    bit * bit = bit
    local new_path = edge.path - bit * bound
    assert_lt_felt(new_path, bound)
    local new_edge : NodeEdge = NodeEdge(length=new_length, path=new_path, bottom=edge.bottom)

    # Decide case.
    %{
        from starkware.python.merkle_tree import decode_node
        left_child, right_child, case = decode_node(node)
        memory[ap] = int(case != 'both')
    %}
    jmp skip_both if [ap] != 0; ap++

    # Traverse both children.
    if bit == 0:
        %{ vm_enter_scope(dict(node=left_child, **common_args)) %}
        traverse_edge(globals=globals, height=height - 1, path=path * 2, edge=new_edge)
        %{ vm_exit_scope() %}
        local hash_ptr : HashBuiltin* = hash_ptr

        %{ vm_enter_scope(dict(node=right_child, **common_args)) %}
        traverse_empty(globals=globals, height=height - 1, path=path * 2 + 1)
        %{ vm_exit_scope() %}
        return ()
    else:
        %{ vm_enter_scope(dict(node=left_child, **common_args)) %}
        traverse_empty(globals=globals, height=height - 1, path=path * 2)
        %{ vm_exit_scope() %}
        ap += 0

        %{ vm_enter_scope(dict(node=right_child, **common_args)) %}
        traverse_edge(globals=globals, height=height - 1, path=path * 2 + 1, edge=new_edge)
        %{ vm_exit_scope() %}
        return ()
    end

    skip_both:
    %{ memory[ap] = int(case == 'right') ^ ids.bit %}
    jmp skip_non_empty_child if [ap] != 0; ap++

    # Traverse the non-empty child.
    assert [siblings] = 0
    let siblings = siblings + 1
    %{
        new_node = left_child if ids.bit == 0 else right_child
        vm_enter_scope(dict(node=new_node, **common_args))
    %}
    traverse_edge(globals=globals, height=height - 1, path=path * 2 + bit, edge=new_edge)
    %{ vm_exit_scope() %}
    return ()

    skip_non_empty_child:
    # Traverse the empty child.
    local range_check_ptr = range_check_ptr
    local new_hash_ptr : HashBuiltin*

    # Reserve a spot for the sibling. It is more efficient to compute it after the recursive
    # traversal.
    let current_sibling = siblings
    let siblings = siblings + 1

    # Traverse empty side.
    %{
        new_node = left_child if ids.bit == 1 else right_child
        vm_enter_scope(dict(node=new_node, **common_args))
    %}
    traverse_empty(globals=globals, height=height - 1, path=path * 2 + 1 - bit)
    %{ vm_exit_scope() %}

    if edge.length == 1:
        # In this case, the sibling is the bottom of our edge.
        # Make sure edge.bottom is binary or leaf.
        assert [current_sibling] = edge.bottom
        if height != 1:
            # This check should only be done on the new tree.
            if globals.access_offset == 2:
                hash_ptr.result = edge.bottom
                %{
                    ids.hash_ptr.x, ids.hash_ptr.y = preimage[ids.edge.bottom]
                    if __patricia_skip_validation_runner:
                        # Skip validation of the preimage dict to speed up the VM. When this flag is
                        # set, mistakes in the preimage dict will be discovered only in the prover.
                        __patricia_skip_validation_runner.verified_addresses.add(
                            ids.hash_ptr + ids.HashBuiltin.result)
                %}
                let hash_ptr = hash_ptr + HashBuiltin.SIZE
                return ()
            else:
                return ()
            end
        end
        return ()
    end

    # This is the case where we split an edge.
    let (hash) = hash2(edge.bottom, new_edge.path)
    assert [current_sibling] = hash + new_edge.length
    return ()

    # Descend.
    descend:
    local length
    local word
    %{ ids.length, ids.word = descend %}
    assert [siblings] = length
    let siblings = siblings + 1

    # Check that the descend is valid.
    assert_in_range(length, 2, edge.length + 1)
    tempvar length_pow2 = globals.pow2[length]
    tempvar new_length = edge.length - length
    tempvar new_length_pow2 = globals.pow2[new_length]
    tempvar new_path = edge.path - word * new_length_pow2
    assert_lt_felt(word, length_pow2)
    assert_lt_felt(new_path, new_length_pow2)

    let new_edge : NodeEdge = NodeEdge(length=new_length, path=new_path, bottom=edge.bottom)
    %{
        new_node = node
        for i in range(ids.length - 1, -1, -1):
            new_node = new_node[(ids.word >> i) & 1]
        vm_enter_scope(dict(node=new_node, **common_args))
    %}
    traverse_edge(
        globals=globals, height=height - length, path=path * length_pow2 + word, edge=new_edge)
    %{ vm_exit_scope() %}

    return ()
end

# Traverses a subtree rooted at the given binary or leaf node with given hash/value.
func traverse_binary_or_leaf{
        hash_ptr : HashBuiltin*, range_check_ptr, update_ptr : DictAccess*, siblings : felt*}(
        globals : ParticiaGlobals*, height : felt, path : felt, node : felt):
    if height == 0:
        # Leaf.
        assert update_ptr.key = path
        tempvar value = [cast(update_ptr, felt*) + globals.access_offset]
        assert value = node
        assert_not_zero(value)
        let update_ptr = update_ptr + DictAccess.SIZE
        return ()
    end

    alloc_locals

    # Binary.
    let current_hash = hash_ptr
    let hash_ptr = hash_ptr + HashBuiltin.SIZE
    assert current_hash.result = node

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
    jmp skip_both if [ap] != 0; ap++

    # Traverse both children.
    %{ vm_enter_scope(dict(node=left_child, **common_args)) %}
    traverse_non_empty(globals=globals, height=height - 1, path=path * 2, node=current_hash.x)
    %{ vm_exit_scope() %}
    tempvar left_child = path * 2
    %{ vm_enter_scope(dict(node=right_child, **common_args)) %}
    traverse_non_empty(globals=globals, height=height - 1, path=left_child + 1, node=current_hash.y)
    %{ vm_exit_scope() %}
    return ()

    skip_both:
    %{ memory[ap] = int(case != 'left') %}
    jmp skip_left if [ap] != 0; ap++

    # Left.
    tempvar sib = current_hash.y
    assert_not_zero(sib)
    assert [siblings] = sib
    let siblings = siblings + 1
    %{ vm_enter_scope(dict(node=left_child, **common_args)) %}
    traverse_non_empty(globals=globals, height=height - 1, path=path * 2, node=current_hash.x)
    %{ vm_exit_scope() %}
    return ()

    skip_left:
    %{ assert case == 'right' %}
    # Right.
    tempvar sib = current_hash.x
    assert_not_zero(sib)
    assert [siblings] = sib
    let siblings = siblings + 1
    %{ vm_enter_scope(dict(node=right_child, **common_args)) %}
    traverse_non_empty(globals=globals, height=height - 1, path=path * 2 + 1, node=current_hash.y)
    %{ vm_exit_scope() %}
    return ()
end

# Traverses some of the leaves in the subtree rooted at node.
func traverse_node{
        hash_ptr : HashBuiltin*, range_check_ptr, update_ptr : DictAccess*, siblings : felt*}(
        globals : ParticiaGlobals*, height : felt, path : felt, node : felt):
    if node == 0:
        # Empty:
        traverse_empty(globals=globals, height=height, path=path)
        return ()
    end

    return traverse_non_empty(globals=globals, height=height, path=path, node=node)
end

# Same as traverse_node, but disallows empty nodes.
func traverse_non_empty{
        hash_ptr : HashBuiltin*, range_check_ptr, update_ptr : DictAccess*, siblings : felt*}(
        globals : ParticiaGlobals*, height : felt, path : felt, node : felt):
    %{ memory[ap] = 1 if ids.height == 0 or len(preimage[ids.node]) == 2 else 0 %}
    jmp binary if [ap] != 0; ap++
    # Edge.
    let (edge) = open_edge(globals=globals, node=node)
    traverse_edge(globals=globals, height=height, path=path, edge=[edge])
    return ()

    # Binary.
    binary:
    return traverse_binary_or_leaf(globals=globals, height=height, path=path, node=node)
end

# Computes a power of 2 array. In other words, writes the sequence 1, 2, 4, 8, ... to the given
# pointer (with the given length).
func compute_pow2_array(pow2_ptr : felt*, cur : felt, n : felt):
    if n == 0:
        return ()
    end
    assert [pow2_ptr] = cur
    return compute_pow2_array(pow2_ptr=pow2_ptr + 1, cur=cur * 2, n=n - 1)
end

# Performs an efficient update of multiple leaves in a Patricia Merkle tree.
#
# Arguments:
# update_ptr - a list of DictAccess instances sorted by key (e.g., the result of squash_dict).
# height - the height of the merkle tree.
# prev_root - the value of the root before the update.
# new_root - the value of the root after the update.
#
# Hint arguments:
# preimage - a dictionary from the hash value of a Patricia node to either
#   1. a pair of children values, for binary nodes.
#   2. a triplet of (length, path, bottom), for edge nodes.
#
# Implicit arguments:
# hash_ptr - hash builtin pointer.
#
# Assumptions: The keys in the update_ptr list are unique and sorted.
# Guarantees: All the keys in the update_ptr list are < 2**height.
func patricia_update{hash_ptr : HashBuiltin*, range_check_ptr}(
        update_ptr : DictAccess*, n_updates : felt, height : felt, prev_root : felt,
        new_root : felt):
    if n_updates == 0:
        prev_root = new_root
        return ()
    end

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
    alloc_locals
    local update_end : DictAccess* = update_ptr + n_updates * DictAccess.SIZE

    # Compute globals.
    let (local globals_pow2 : felt*) = alloc()
    compute_pow2_array(globals_pow2, 1, MAX_LENGTH + 1)

    # Traverse prev tree.
    let (local siblings) = alloc()
    let original_update_ptr = update_ptr
    let original_siblings = siblings
    let (local globals_prev : ParticiaGlobals*) = alloc()
    assert [globals_prev] = ParticiaGlobals(pow2=globals_pow2, access_offset=DictAccess.prev_value)

    assert_le(height, MAX_LENGTH)
    %{ vm_enter_scope(dict(node=node, **common_args)) %}
    with update_ptr, siblings:
        traverse_node(globals=globals_prev, height=height, path=0, node=prev_root)
    end
    %{ vm_exit_scope() %}
    assert update_ptr = update_end
    local siblings_end : felt* = siblings

    # Traverse new tree.
    let update_ptr = original_update_ptr
    let siblings = original_siblings
    let (local globals_new : ParticiaGlobals*) = alloc()
    assert [globals_new] = ParticiaGlobals(pow2=globals_pow2, access_offset=DictAccess.new_value)

    %{ vm_enter_scope(dict(node=node, **common_args)) %}
    with update_ptr, siblings:
        traverse_node(globals=globals_new, height=height, path=0, node=new_root)
    end
    %{ vm_exit_scope() %}
    assert update_ptr = update_end
    assert siblings = siblings_end
    return ()
end
