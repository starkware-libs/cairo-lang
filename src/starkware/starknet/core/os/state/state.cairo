from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin, PoseidonBuiltin
from starkware.cairo.common.dict import DictAccess
from starkware.cairo.common.find_element import search_sorted
from starkware.cairo.common.patricia import patricia_update_constants_new
from starkware.cairo.common.patricia_utils import PatriciaUpdateConstants
from starkware.cairo.common.squash_dict import squash_dict
from starkware.starknet.core.os.constants import ALIAS_CONTRACT_ADDRESS
from starkware.starknet.core.os.state.aliases import allocate_aliases
from starkware.starknet.core.os.state.commitment import (
    MERKLE_HEIGHT,
    CommitmentUpdate,
    StateEntry,
    calculate_global_state_root,
    compute_class_commitment,
    compute_contract_state_commitment,
)
from starkware.starknet.core.os.state.squash import squash_class_changes, squash_state_changes

// Represents the changes in the state of the system.
struct OsStateUpdate {
    // A pointer to the beginning of the state changes dict.
    contract_state_changes_start: DictAccess*,
    // A pointer to the end of the state changes dict.
    contract_state_changes_end: DictAccess*,
    // A pointer to the beginning of the contract class changes dict.
    contract_class_changes_start: DictAccess*,
    // A pointer to the end of the contract class changes dict.
    contract_class_changes_end: DictAccess*,
}

struct SquashedOsStateUpdate {
    // A pointer to the beginning of the state changes dict.
    contract_state_changes: DictAccess*,
    // The size of the contract state changes dict.
    n_contract_state_changes: felt,
    // A pointer to the beginning of the contract class changes dict.
    contract_class_changes: DictAccess*,
    // The size of the contract class changes dict.
    n_class_updates: felt,
}

// Performs the commitment tree updates required for (validating and) updating the global state.
// Returns a CommitmentUpdate struct.
func state_update{poseidon_ptr: PoseidonBuiltin*, hash_ptr: HashBuiltin*, range_check_ptr}(
    os_state_update: OsStateUpdate
) -> (squashed_os_state_update: SquashedOsStateUpdate*, state_update_output: CommitmentUpdate*) {
    alloc_locals;

    // Create PatriciaUpdateConstants struct for patricia update.
    let (local patricia_update_constants: PatriciaUpdateConstants*) = patricia_update_constants_new(
        );

    // Allocate aliases and squash the final contract state tree.
    let (
        n_contract_state_changes, squashed_contract_state_changes_start
    ) = allocate_aliases_and_squash_state_changes(
        contract_state_changes_start=os_state_update.contract_state_changes_start,
        contract_state_changes_end=os_state_update.contract_state_changes_end,
    );

    // State is finalized.
    %{ commitment_info_by_address=execution_helper.compute_storage_commitments() %}

    // Compute the contract state commitment.
    let contract_state_tree_update_output = compute_contract_state_commitment(
        contract_state_changes_start=squashed_contract_state_changes_start,
        n_contract_state_changes=n_contract_state_changes,
        patricia_update_constants=patricia_update_constants,
    );

    // Squash the contract class tree.
    let (n_class_updates, squashed_class_changes) = squash_class_changes(
        class_changes_start=os_state_update.contract_class_changes_start,
        class_changes_end=os_state_update.contract_class_changes_end,
    );

    // Update the contract class tree.
    let (contract_class_tree_update_output) = compute_class_commitment(
        class_changes_start=squashed_class_changes,
        n_class_updates=n_class_updates,
        patricia_update_constants=patricia_update_constants,
    );

    // Compute the initial and final roots of the global state.
    let (local initial_global_root) = calculate_global_state_root(
        contract_state_root=contract_state_tree_update_output.initial_root,
        contract_class_root=contract_class_tree_update_output.initial_root,
    );
    let (local final_global_root) = calculate_global_state_root(
        contract_state_root=contract_state_tree_update_output.final_root,
        contract_class_root=contract_class_tree_update_output.final_root,
    );

    // Prepare the return values.
    tempvar squashed_os_state_update = new SquashedOsStateUpdate(
        contract_state_changes=squashed_contract_state_changes_start,
        n_contract_state_changes=n_contract_state_changes,
        contract_class_changes=squashed_class_changes,
        n_class_updates=n_class_updates,
    );

    tempvar state_update_output = new CommitmentUpdate(
        initial_root=initial_global_root, final_root=final_global_root
    );

    return (
        squashed_os_state_update=squashed_os_state_update, state_update_output=state_update_output
    );
}

// Allocates aliases and squashes the contract state changes (after alias allocation).
func allocate_aliases_and_squash_state_changes{range_check_ptr}(
    contract_state_changes_start: DictAccess*, contract_state_changes_end: DictAccess*
) -> (n_contract_state_changes: felt, squashed_contract_state_changes_start: DictAccess*) {
    alloc_locals;

    // Squash the contract state tree.
    let (n_contract_state_changes, squashed_contract_state_dict) = squash_state_changes(
        contract_state_changes_start=contract_state_changes_start,
        contract_state_changes_end=contract_state_changes_end,
    );

    // Allocate aliases.
    let aliases_storage_updates: DictAccess* = alloc();
    local aliases_storage_updates_start: DictAccess* = aliases_storage_updates;
    with aliases_storage_updates {
        allocate_aliases(
            n_contracts=n_contract_state_changes,
            contract_state_changes=squashed_contract_state_dict,
        );
    }

    // Verify that ALIAS_CONTRACT_ADDRESS is not included in the state diff (before the allocation).
    let (_, success) = search_sorted(
        array_ptr=squashed_contract_state_dict,
        elm_size=DictAccess.SIZE,
        n_elms=n_contract_state_changes,
        key=ALIAS_CONTRACT_ADDRESS,
    );
    assert success = 0;

    // Squash the storage updates of the alias contract.
    // The check above ensures that there was no access to this storage before, so it is enough to
    // squash it separately instead of running `squash_state_changes` again.
    local squashed_aliases_storage_start: DictAccess*;
    local prev_aliases_state_entry: StateEntry*;
    %{
        if state_update_pointers is None:
            ids.squashed_aliases_storage_start = segments.add()
            ids.prev_aliases_state_entry = segments.add()
        else:
            ids.prev_aliases_state_entry, ids.squashed_aliases_storage_start = (
                state_update_pointers.get_contract_state_entry_and_storage_ptr(
                    ids.ALIAS_CONTRACT_ADDRESS
                )
            )
    %}
    let (squashed_aliases_storage_end) = squash_dict(
        dict_accesses=aliases_storage_updates_start,
        dict_accesses_end=aliases_storage_updates,
        squashed_dict=squashed_aliases_storage_start,
    );

    // Add the aliases storage to squashed_contract_state_dict.
    assert [prev_aliases_state_entry] = StateEntry(
        class_hash=0, storage_ptr=squashed_aliases_storage_start, nonce=0
    );

    tempvar new_aliases_state_entry = new StateEntry(
        class_hash=0, storage_ptr=squashed_aliases_storage_end, nonce=0
    );
    %{
        if state_update_pointers is not None:
            state_update_pointers.contract_address_to_state_entry_and_storage_ptr[
                    ids.ALIAS_CONTRACT_ADDRESS
                ] = (
                    ids.new_aliases_state_entry.address_,
                    ids.squashed_aliases_storage_end.address_,
                )
    %}
    let squashed_contract_state_dict_end = (
        &squashed_contract_state_dict[n_contract_state_changes]
    );
    assert squashed_contract_state_dict_end[0] = DictAccess(
        key=ALIAS_CONTRACT_ADDRESS,
        prev_value=cast(prev_aliases_state_entry, felt),
        new_value=cast(new_aliases_state_entry, felt),
    );
    let squashed_contract_state_dict_end = &squashed_contract_state_dict_end[1];

    // Squash again just the outer contract dict (to sort the entries).
    local final_squashed_contract_state_changes_start: DictAccess*;
    %{
        if state_update_pointers is None:
            ids.final_squashed_contract_state_changes_start = segments.add()
        else:
            ids.final_squashed_contract_state_changes_start = (
                state_update_pointers.state_tree_ptr
            )
    %}

    let (final_squashed_contract_state_changes_end) = squash_dict(
        dict_accesses=squashed_contract_state_dict,
        dict_accesses_end=squashed_contract_state_dict_end,
        squashed_dict=final_squashed_contract_state_changes_start,
    );
    %{
        if state_update_pointers is not None:
            state_update_pointers.state_tree_ptr = (
                ids.final_squashed_contract_state_changes_end.address_
            )
    %}
    let final_n_contract_state_changes = (
        final_squashed_contract_state_changes_end - final_squashed_contract_state_changes_start
    ) / DictAccess.SIZE;

    return (
        n_contract_state_changes=final_n_contract_state_changes,
        squashed_contract_state_changes_start=final_squashed_contract_state_changes_start,
    );
}
