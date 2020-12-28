from starkware.cairo.common.cairo_builtins import HashBuiltin

# Performs an update for a single leaf (index) in a Merkle tree (where 0 <= index < 2^height).
# Updates the leaf from prev_leaf to new_leaf, and returns the previous and new roots of the
# Merkle tree resulting from the change.
# In particular, given a secret authentication path (of the siblings of the nodes in the path from
# the root to the leaf), this function computes the roots twice - once with prev_leaf and once with
# new_leaf, where the verifier is guaranteed that the same authentication path is used.
func merkle_update(hash_ptr, height, prev_leaf, new_leaf, index) -> (prev_root, new_root, hash_ptr):
    if height == 0:
        # Assert that index is 0.
        index = 0
        # Return the two leaves and the Pedersen pointer.
        %{
            # Check that auth_path had the right number of elements.
            assert len(auth_path) == 0, 'Got too many values in auth_path.'
        %}
        return (prev_root=prev_leaf, new_root=new_leaf, hash_ptr=hash_ptr)
    end

    %{ memory[ap] = ids.index % 2 %}
    jmp update_right if [ap] != 0; ap++

    update_left:
    %{
        # Hash hints.
        sibling = auth_path.pop()
        memory[ids.hash_ptr + 0 * ids.HashBuiltin.SIZE + ids.HashBuiltin.y] = sibling
        memory[ids.hash_ptr + 1 * ids.HashBuiltin.SIZE + ids.HashBuiltin.y] = sibling
    %}
    prev_leaf = [hash_ptr + 0 * HashBuiltin.SIZE + HashBuiltin.x]
    new_leaf = [hash_ptr + 1 * HashBuiltin.SIZE + HashBuiltin.x]

    # Make sure the same authentication path is used.
    let right_sibling = ap
    [right_sibling] = [hash_ptr + 0 * HashBuiltin.SIZE + HashBuiltin.y]
    [right_sibling] = [hash_ptr + 1 * HashBuiltin.SIZE + HashBuiltin.y]; ap++

    # Call merkle_update recursively.
    [ap] = hash_ptr + 2 * HashBuiltin.SIZE; ap++  # hash_ptr.
    [ap] = height - 1; ap++  # height.
    [ap] = [hash_ptr + 0 * HashBuiltin.SIZE + HashBuiltin.result]; ap++  # prev_leaf.
    [ap] = [hash_ptr + 1 * HashBuiltin.SIZE + HashBuiltin.result]; ap++  # new_leaf.

    let update_left_index = ap
    %{ memory[ap] = ids.index // 2 %}
    index = [update_left_index] * 2; ap++  # index.
    merkle_update(...)  # Tail recursion.
    return (...)

    update_right:
    %{
        # Hash hints.
        sibling = auth_path.pop()
        memory[ids.hash_ptr + 0 * ids.HashBuiltin.SIZE + ids.HashBuiltin.x] = sibling
        memory[ids.hash_ptr + 1 * ids.HashBuiltin.SIZE + ids.HashBuiltin.x] = sibling
    %}
    prev_leaf = [hash_ptr + 0 * HashBuiltin.SIZE + HashBuiltin.y]
    new_leaf = [hash_ptr + 1 * HashBuiltin.SIZE + HashBuiltin.y]

    # Make sure the same authentication path is used.
    let left_sibling = ap
    [left_sibling] = [hash_ptr + 0 * HashBuiltin.SIZE + HashBuiltin.x]
    [left_sibling] = [hash_ptr + 1 * HashBuiltin.SIZE + HashBuiltin.x]; ap++

    # Compute index - 1.
    tempvar index_minus_one = index - 1

    # Call merkle_update recursively.
    [ap] = hash_ptr + 2 * HashBuiltin.SIZE; ap++  # hash_ptr.
    [ap] = height - 1; ap++  # height.
    [ap] = [hash_ptr + 0 * HashBuiltin.SIZE + HashBuiltin.result]; ap++  # prev_leaf.
    [ap] = [hash_ptr + 1 * HashBuiltin.SIZE + HashBuiltin.result]; ap++  # new_leaf.

    let update_right_index = ap
    %{ memory[ap] = ids.index // 2 %}
    # Compute (index - 1) / 2.
    index_minus_one = [update_right_index] * 2; ap++  # index.
    merkle_update(...)  # Tail recursion.
    return (...)
end
