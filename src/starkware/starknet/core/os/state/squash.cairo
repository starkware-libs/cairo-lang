from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.dict import DictAccess, squash_dict
from starkware.starknet.core.os.state.commitment import StateEntry

// Takes a dict of `StateEntry` structs and produces a new dict by squashing the outer dictionary
// and inner dictionaries in `StateEntry::storage_ptr`.
func squash_state_changes{range_check_ptr}(
    contract_state_changes_start: DictAccess*, contract_state_changes_end: DictAccess*
) -> (n_contract_state_changes: felt, squashed_contract_state_dict: DictAccess*) {
    alloc_locals;

    // State changes after squashing the outer dictionary.
    let (local squashed_dict: DictAccess*) = alloc();

    // Squash the global dictionary to get a list of triples (addr, dict_begin, dict_end).
    let (squashed_dict_end) = squash_dict(
        dict_accesses=contract_state_changes_start,
        dict_accesses_end=contract_state_changes_end,
        squashed_dict=squashed_dict,
    );

    local n_contract_state_changes = (squashed_dict_end - squashed_dict) / DictAccess.SIZE;

    // State changes after squashing the outer dictionary and the inner dictionaries.
    let (local fully_squashed_dict: DictAccess*) = alloc();
    squash_state_changes_inner(
        n_contract_state_changes=n_contract_state_changes,
        state_changes=squashed_dict,
        squashed_state_changes=fully_squashed_dict,
    );

    return (
        n_contract_state_changes=n_contract_state_changes,
        squashed_contract_state_dict=fully_squashed_dict,
    );
}

// Takes a dict of `StateEntry` structs and produces a new dict by squashing the inner dicts in
// `StateEntry::storage_ptr`.
func squash_state_changes_inner{range_check_ptr}(
    n_contract_state_changes: felt, state_changes: DictAccess*, squashed_state_changes: DictAccess*
) {
    if (n_contract_state_changes == 0) {
        return ();
    }
    alloc_locals;

    local prev_state: StateEntry* = cast(state_changes.prev_value, StateEntry*);
    local new_state: StateEntry* = cast(state_changes.new_value, StateEntry*);
    local squashed_storage_ptr: DictAccess*;
    local squashed_prev_state: StateEntry*;
    %{
        if state_update_pointers is None:
            ids.squashed_storage_ptr = segments.add()
            ids.squashed_prev_state = segments.add()
        else:
            ids.squashed_prev_state, ids.squashed_storage_ptr = (
                state_update_pointers.get_contract_state_entry_and_storage_ptr(
                    contract_address=ids.state_changes.key
                )
            )
    %}

    let (local squashed_storage_ptr_end) = squash_dict(
        dict_accesses=prev_state.storage_ptr,
        dict_accesses_end=new_state.storage_ptr,
        squashed_dict=squashed_storage_ptr,
    );

    assert [squashed_prev_state] = StateEntry(
        class_hash=prev_state.class_hash, storage_ptr=squashed_storage_ptr, nonce=prev_state.nonce
    );

    local squashed_new_state: StateEntry* = new StateEntry(
        class_hash=new_state.class_hash, storage_ptr=squashed_storage_ptr_end, nonce=new_state.nonce
    );

    %{
        if state_update_pointers is not None:
            state_update_pointers.contract_address_to_state_entry_and_storage_ptr[
                ids.state_changes.key
            ] = (
                ids.squashed_new_state.address_,
                ids.squashed_storage_ptr_end.address_,
            )
    %}

    assert squashed_state_changes[0] = DictAccess(
        key=state_changes.key,
        prev_value=cast(squashed_prev_state, felt),
        new_value=cast(squashed_new_state, felt),
    );

    return squash_state_changes_inner(
        n_contract_state_changes=n_contract_state_changes - 1,
        state_changes=&state_changes[1],
        squashed_state_changes=&squashed_state_changes[1],
    );
}

// Takes a dict of the class changes and produces a squashed dict.
func squash_class_changes{range_check_ptr}(
    class_changes_start: DictAccess*, class_changes_end: DictAccess*
) -> (n_class_updates: felt, squashed_contract_state_dict: DictAccess*) {
    alloc_locals;

    local squashed_dict: DictAccess*;
    %{
        if state_update_pointers is None:
            ids.squashed_dict = segments.add()
        else:
            ids.squashed_dict = state_update_pointers.class_tree_ptr
    %}
    let (local squashed_dict_end) = squash_dict(
        dict_accesses=class_changes_start,
        dict_accesses_end=class_changes_end,
        squashed_dict=squashed_dict,
    );

    %{
        if state_update_pointers is not None:
            state_update_pointers.class_tree_ptr = ids.squashed_dict_end.address_
    %}

    return (
        n_class_updates=(squashed_dict_end - squashed_dict) / DictAccess.SIZE,
        squashed_contract_state_dict=squashed_dict,
    );
}
