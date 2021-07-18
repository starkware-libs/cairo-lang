from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.dict import DictAccess, squash_dict
from starkware.cairo.common.hash import hash2
from starkware.cairo.common.merkle_multi_update import merkle_multi_update
from starkware.cairo.common.segments import relocate_segment

const MERKLE_HEIGHT = %[ PRIME.bit_length() - 1 %]

struct MerkleUpdateOutput:
    member initial_storage_root : felt
    member final_storage_root : felt
end

struct StateEntry:
    member contract_hash : felt
    member storage_ptr : DictAccess*
end

func serialize_da_changes{da_output_ptr : felt*}(update_ptr : DictAccess*, n_updates : felt):
    if n_updates == 0:
        return ()
    end
    assert [da_output_ptr] = update_ptr.key
    assert [da_output_ptr + 1] = update_ptr.new_value
    let da_output_ptr = da_output_ptr + 2
    return serialize_da_changes(update_ptr=update_ptr + DictAccess.SIZE, n_updates=n_updates - 1)
end

# Performs the Merkle updates required for (validating and) updating the global state.
# Returns a MerkleUpdateOutput struct.
# Checks that [state_changes_dict, state_changes_dict_end) is a valid according to squash_dict.
func state_update{hash_ptr : HashBuiltin*, range_check_ptr, da_output_ptr : felt*}(
        state_changes_dict : DictAccess*, state_changes_dict_end : DictAccess*) -> (
        merkle_update_output : MerkleUpdateOutput*):
    alloc_locals
    let (local squashed_dict : DictAccess*) = alloc()

    # Squash the global dictionary to get a list of triples (addr, dict_begin, dict_end).
    let (squashed_dict_end) = squash_dict(
        dict_accesses=state_changes_dict,
        dict_accesses_end=state_changes_dict_end,
        squashed_dict=squashed_dict)

    # Hash the entries of state_changes_dict to prepare the input for the Merkle multi update.
    let (local hashed_state_changes : DictAccess*) = alloc()
    local n_state_changes = (squashed_dict_end - squashed_dict) / DictAccess.SIZE
    assert [da_output_ptr] = n_state_changes
    let da_output_ptr = da_output_ptr + 1
    hash_state_changes(
        n_state_changes=n_state_changes,
        state_changes=squashed_dict,
        hashed_state_changes=hashed_state_changes)
    local range_check_ptr = range_check_ptr
    local da_output_ptr : felt* = da_output_ptr

    # Compute the initial and final roots of the global state.
    let (local merkle_update_output : MerkleUpdateOutput*) = alloc()

    %{
        def as_int(x):
            return int.from_bytes(x, 'big')

        ids.merkle_update_output.initial_storage_root = as_int(
            os_input.global_state_merkle.root)
        new_tree, merkle_facts = global_state_storage.merkle_update()
        ids.merkle_update_output.final_storage_root = as_int(new_tree.root)
        preimage = {
            as_int(root): (as_int(left_child), as_int(right_child))
            for root, (left_child, right_child) in merkle_facts.items()
        }
        assert global_state_storage.merkle_tree.height == ids.MERKLE_HEIGHT
    %}

    merkle_multi_update(
        update_ptr=hashed_state_changes,
        n_updates=n_state_changes,
        height=MERKLE_HEIGHT,
        prev_root=merkle_update_output.initial_storage_root,
        new_root=merkle_update_output.final_storage_root)

    return (merkle_update_output=merkle_update_output)
end

# Takes a dict of StateEntry structs and produces a dict of hashes by hashing
# every entry of the input dict. The output is written to 'hashed_state_changes'
#
# Additionally, all the updates are written to the 'global_state_storage' hint variable.
func hash_state_changes{hash_ptr : HashBuiltin*, range_check_ptr, da_output_ptr : felt*}(
        n_state_changes, state_changes : DictAccess*, hashed_state_changes : DictAccess*):
    if n_state_changes == 0:
        return ()
    end
    alloc_locals

    local prev_state : StateEntry* = cast(state_changes.prev_value, StateEntry*)
    local new_state : StateEntry* = cast(state_changes.new_value, StateEntry*)
    let (local squashed_storage_dict : DictAccess*) = alloc()
    local initial_storage_root
    local final_storage_root

    %{
        def as_int(x):
            return int.from_bytes(x, 'big')

        storage = storage_by_address[ids.state_changes.key]
        ids.initial_storage_root = as_int(storage.merkle_tree.root)
        new_tree, merkle_facts = storage.merkle_update()
        ids.final_storage_root = as_int(new_tree.root)
        preimage = {
            as_int(root): (as_int(left_child), as_int(right_child))
            for root, (left_child, right_child) in merkle_facts.items()
        }
        assert storage.merkle_tree.height == ids.MERKLE_HEIGHT
    %}
    let (local squashed_storage_dict_end) = squash_dict(
        dict_accesses=prev_state.storage_ptr,
        dict_accesses_end=new_state.storage_ptr,
        squashed_dict=squashed_storage_dict)
    local range_check_ptr = range_check_ptr

    local n_updates = (squashed_storage_dict_end - squashed_storage_dict) / DictAccess.SIZE
    let vault_merkle_multi_update_ret = merkle_multi_update(
        update_ptr=squashed_storage_dict,
        n_updates=n_updates,
        height=MERKLE_HEIGHT,
        prev_root=initial_storage_root,
        new_root=final_storage_root)

    # Write contract address.
    assert [da_output_ptr] = state_changes.key
    # Write n_updates.
    assert [da_output_ptr + 1] = n_updates
    let da_output_ptr = da_output_ptr + 2
    # Write updates.
    local hash_ptr : HashBuiltin* = hash_ptr
    serialize_da_changes(update_ptr=squashed_storage_dict, n_updates=n_updates)

    let (prev_value) = hash2(prev_state.contract_hash, initial_storage_root)
    let (new_value) = hash2(new_state.contract_hash, final_storage_root)
    assert hashed_state_changes.key = state_changes.key
    assert hashed_state_changes.prev_value = prev_value
    assert hashed_state_changes.new_value = new_value

    %{ global_state_storage.write(address=ids.hashed_state_changes.key, value=ids.new_value) %}

    return hash_state_changes(
        n_state_changes=n_state_changes - 1,
        state_changes=state_changes + DictAccess.SIZE,
        hashed_state_changes=hashed_state_changes + DictAccess.SIZE)
end
