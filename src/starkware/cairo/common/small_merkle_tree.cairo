from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.dict import DictAccess
from starkware.cairo.common.merkle_multi_update import merkle_multi_update

# Performs an efficient update of multiple leaves in a Merkle tree, based on the given squashed
# dict, assuming the merkle tree is small enough to be loaded to the memory.
#
# This function computes the Merkle authentication paths internally and
# does not require any hint arguments, therefore it's usually easier to use.
# The input dict must be created using the higher-level dict functions (see dict.cairo), which add
# information about all the non-default leaves in the hints (not just the leaves that were changed).
#
# Usage example:
#   %{ initial_dict = {1: 2, 3: 4, 5: 6} %}
#   let (dict_ptr_start) = dict_new()
#   let dict_ptr = dict_ptr_start
#   let (dict_ptr) = dict_update(dict_ptr=dict_ptr, key=1, prev_value=2, new_value=20)
#   let (range_check_ptr, squashed_dict_start, squashed_dict_end) = dict_squash(
#       range_check_ptr=range_check_ptr,
#       dict_accesses_start=dict_ptr_start,
#       dict_accesses_end=dict_ptr)
#   const HEIGHT = 3
#   let (prev_root, new_root) = small_merkle_tree(
#        squashed_dict_start, squashed_dict_end, HEIGHT)
#
# In this example prev_root is the Merkle root of [0, 2, 0, 4, 0, 6, 0, 0], and new_root
# is the Merkle root of [0, 20, 0, 4, 0, 6, 0, 0].
# Note that from the point of view of the verifier, all it knows is that leaf 1 changed from 2 to
# 20 -- it doesn't know anything about the other leaves (except that they haven't changed).
#
# Arguments:
# squashed_dict, squashed_dict_end - a list of DictAccess instances sorted by key
# (e.g., the result of dict_squash).
# height - the height of the merkle tree.
#
# Implicit arguments:
# hash_ptr - hash builtin pointer.
#
# Returns:
# prev_root - the value of the root before the update.
# new_root - the value of the root after the update.
#
# Assumptions: The keys in the squashed_dict are unique and sorted.
#
# Prover assumptions:
# * squashed_dict was created using the higher-level API dict_squash() (rather than squash_dict()).
# * This function can be used for (relatively) small Merkle trees whose leaves can be loaded
#   to the memory.
func small_merkle_tree{hash_ptr : HashBuiltin*}(
        squashed_dict_start : DictAccess*, squashed_dict_end : DictAccess*, height : felt) -> (
        prev_root : felt, new_root : felt):
    %{ vm_enter_scope({'__dict_manager': __dict_manager}) %}
    alloc_locals
    # Allocate memory cells for the roots.
    local prev_root
    local new_root
    %{
        # Compute the roots and the preimage dictionary.
        from starkware.cairo.common.small_merkle_tree import get_preimage_dictionary
        from starkware.python.math_utils import safe_div

        new_dict = __dict_manager.get_dict(ids.squashed_dict_end.address_)

        DICT_ACCESS_SIZE = ids.DictAccess.SIZE
        squashed_dict_start = ids.squashed_dict_start.address_
        squashed_dict_size = ids.squashed_dict_end.address_ - squashed_dict_start
        assert squashed_dict_size >= 0 and squashed_dict_size % DICT_ACCESS_SIZE == 0, \
            f'squashed_dict size must be non-negative and divisible by DictAccess.SIZE. ' \
            f'Found: {squashed_dict_size}.'
        squashed_dict_length = safe_div(squashed_dict_size, DICT_ACCESS_SIZE)

        # Compute the modifications backwards: from the new values to the previous values.
        modifications = []
        for i in range(squashed_dict_length):
            key = memory[squashed_dict_start + i * DICT_ACCESS_SIZE + ids.DictAccess.key]
            prev_value = memory[
                squashed_dict_start + i * DICT_ACCESS_SIZE + ids.DictAccess.prev_value]
            new_value = memory[
                squashed_dict_start + i * DICT_ACCESS_SIZE + ids.DictAccess.new_value]
            assert new_dict[key] == new_value, \
                f'Inconsistent dictionary values. Expected new value: {new_dict[key]}, ' \
                f'found: {new_value}'
            modifications.append((key, prev_value))

        ids.new_root, ids.prev_root, preimage = get_preimage_dictionary(
            initial_leaves=new_dict.items(),
            modifications=modifications,
            tree_height=ids.height,
            default_leaf=0)
    %}

    # Call merkle_multi_update() to verify the two roots.
    merkle_multi_update(
        update_ptr=squashed_dict_start,
        n_updates=(squashed_dict_end - squashed_dict_start) / DictAccess.SIZE,
        height=height,
        prev_root=prev_root,
        new_root=new_root)
    %{ vm_exit_scope() %}
    return (prev_root=prev_root, new_root=new_root)
end
