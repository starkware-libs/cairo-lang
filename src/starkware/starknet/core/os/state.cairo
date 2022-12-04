from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.dict import DictAccess, squash_dict
from starkware.cairo.common.hash import hash2
from starkware.cairo.common.math import assert_nn_le
from starkware.cairo.common.patricia import (
    ParticiaGlobals,
    PatriciaUpdateConstants,
    patricia_update_constants_new,
    patricia_update_using_update_constants,
)
from starkware.cairo.common.segments import relocate_segment

const MERKLE_HEIGHT = 251;  // PRIME.bit_length() - 1.
const UNINITIALIZED_CLASS_HASH = 0;

// The on-chain data for contract state changes has the following format:
//
// * The number of affected contracts.
// * For each contract:
//   * The contract address (1 word).
//   * Number of entry updates and the new nonce (1 word):
//       +-----------+-------------+ LSB
//       | new nonce | n_updates   +
//       | 64 bits   | 64 bits     +
//       +-----------+-------------+
//   * For each entry update:
//       * key (1 word).
//       * new value (1 word).

// A bound on the number of storage entry updates in a contract.
const N_UPDATES_BOUND = 2 ** 64;
// A bound on the nonce of a contract.
const NONCE_BOUND = 2 ** 64;

struct CommitmentTreeUpdateOutput {
    initial_storage_root: felt,
    final_storage_root: felt,
}

struct StateEntry {
    class_hash: felt,
    storage_ptr: DictAccess*,
    nonce: felt,
}

// Represents an update of a storage entry of a contract.
struct StorageUpdateEntry {
    // The entry's key.
    key: felt,
    // The new value.
    value: felt,
}

func serialize_da_changes{storage_updates: StorageUpdateEntry*}(
    update_ptr: DictAccess*, n_updates: felt
) {
    if (n_updates == 0) {
        return ();
    }
    if (update_ptr.prev_value == update_ptr.new_value) {
        tempvar storage_updates = storage_updates;
    } else {
        assert [storage_updates] = StorageUpdateEntry(
            key=update_ptr.key, value=update_ptr.new_value
        );
        tempvar storage_updates = storage_updates + StorageUpdateEntry.SIZE;
    }
    return serialize_da_changes(update_ptr=update_ptr + DictAccess.SIZE, n_updates=n_updates - 1);
}

// Performs the commitment tree updates required for (validating and) updating the global state.
// Returns a CommitmentTreeUpdateOutput struct.
// Checks that [state_changes_dict, state_changes_dict_end) is a valid according to squash_dict.
// Writes the changed values into storage_updates_ptr, to make this data available on-chain.
func state_update{hash_ptr: HashBuiltin*, range_check_ptr, storage_updates_ptr: felt*}(
    state_changes_dict: DictAccess*, state_changes_dict_end: DictAccess*
) -> (commitment_tree_update_output: CommitmentTreeUpdateOutput*) {
    alloc_locals;
    let (local squashed_dict: DictAccess*) = alloc();

    // Squash the global dictionary to get a list of triples (addr, dict_begin, dict_end).
    let (squashed_dict_end) = squash_dict(
        dict_accesses=state_changes_dict,
        dict_accesses_end=state_changes_dict_end,
        squashed_dict=squashed_dict,
    );

    // Hash the entries of state_changes_dict to prepare the input for the commitment tree
    // multi-update.
    let (local hashed_state_changes: DictAccess*) = alloc();
    local n_state_changes = (squashed_dict_end - squashed_dict) / DictAccess.SIZE;
    // Make room for number of state updates.
    let output_n_updates = [storage_updates_ptr];
    let storage_updates_ptr = storage_updates_ptr + 1;
    let n_actual_state_changes = 0;
    // Creates PatriciaUpdateConstants struct for patricia update.
    let (local patricia_update_constants: PatriciaUpdateConstants*) = patricia_update_constants_new(
        );

    with n_actual_state_changes {
        hash_state_changes(
            n_state_changes=n_state_changes,
            state_changes=squashed_dict,
            hashed_state_changes=hashed_state_changes,
            patricia_update_constants=patricia_update_constants,
        );
    }
    // Write number of state updates.
    assert output_n_updates = n_actual_state_changes;

    // Compute the initial and final roots of the global state.
    let (local commitment_tree_update_output: CommitmentTreeUpdateOutput*) = alloc();

    %{
        from starkware.python.utils import from_bytes

        ids.commitment_tree_update_output.initial_storage_root = from_bytes(
            os_input.global_state_commitment_tree.root)
        new_tree, commitment_tree_facts = global_state_storage.commitment_update()
        ids.commitment_tree_update_output.final_storage_root = from_bytes(new_tree.root)
        preimage = {
            int(root): children
            for root, children in commitment_tree_facts.items()
        }
        assert global_state_storage.commitment_tree.height == ids.MERKLE_HEIGHT
    %}

    // Call patricia_update_using_update_constants() instead of patricia_update()
    // in order not to repeat globals_pow2 calculation.
    patricia_update_using_update_constants(
        patricia_update_constants=patricia_update_constants,
        update_ptr=hashed_state_changes,
        n_updates=n_state_changes,
        height=MERKLE_HEIGHT,
        prev_root=commitment_tree_update_output.initial_storage_root,
        new_root=commitment_tree_update_output.final_storage_root,
    );

    return (commitment_tree_update_output=commitment_tree_update_output);
}

func get_contract_state_hash{hash_ptr: HashBuiltin*}(
    class_hash: felt, storage_root: felt, nonce: felt
) -> (hash: felt) {
    const CONTRACT_STATE_HASH_VERSION = 0;
    if (class_hash == UNINITIALIZED_CLASS_HASH) {
        if (storage_root == 0) {
            if (nonce == 0) {
                return (hash=0);
            }
        }
    }

    // Set res = H(H(class_hash, storage_root), nonce).
    let (hash_value) = hash2(class_hash, storage_root);
    let (hash_value) = hash2(hash_value, nonce);

    // Return H(hash_value, CONTRACT_STATE_HASH_VERSION). CONTRACT_STATE_HASH_VERSION must be in the
    // outermost hash to guarantee unique "decoding".
    let (hash) = hash2(hash_value, CONTRACT_STATE_HASH_VERSION);
    return (hash=hash);
}

// Takes a dict of StateEntry structs and produces a dict of hashes by hashing
// every entry of the input dict. The output is written to 'hashed_state_changes'
//
// Writes all updates to the 'global_state_storage' hint variable.
//
// Writes all storage changes to output (storage_updates_ptr), 'n_actual_state_changes'
// will hold the number of contracts with storage changes.
func hash_state_changes{
    hash_ptr: HashBuiltin*, range_check_ptr, storage_updates_ptr: felt*, n_actual_state_changes
}(
    n_state_changes,
    state_changes: DictAccess*,
    hashed_state_changes: DictAccess*,
    patricia_update_constants: PatriciaUpdateConstants*,
) {
    if (n_state_changes == 0) {
        return ();
    }
    alloc_locals;

    local prev_state: StateEntry* = cast(state_changes.prev_value, StateEntry*);
    local new_state: StateEntry* = cast(state_changes.new_value, StateEntry*);
    local new_state_nonce = new_state.nonce;
    let (local squashed_storage_dict: DictAccess*) = alloc();
    local initial_storage_root;
    local final_storage_root;

    %{
        from starkware.python.utils import from_bytes

        storage = storage_by_address[ids.state_changes.key]
        ids.initial_storage_root = from_bytes(storage.commitment_tree.root)
        new_tree, commitment_tree_facts = storage.commitment_update()
        ids.final_storage_root = from_bytes(new_tree.root)
        preimage = {
            int(root): children
            for root, children in commitment_tree_facts.items()
        }
        assert storage.commitment_tree.height == ids.MERKLE_HEIGHT
    %}
    let (local squashed_storage_dict_end) = squash_dict(
        dict_accesses=prev_state.storage_ptr,
        dict_accesses_end=new_state.storage_ptr,
        squashed_dict=squashed_storage_dict,
    );

    local n_updates = (squashed_storage_dict_end - squashed_storage_dict) / DictAccess.SIZE;
    // Call patricia_update_using_update_constants() instead of patricia_update()
    // in order not to repeat globals_pow2 calculation.
    patricia_update_using_update_constants(
        patricia_update_constants=patricia_update_constants,
        update_ptr=squashed_storage_dict,
        n_updates=n_updates,
        height=MERKLE_HEIGHT,
        prev_root=initial_storage_root,
        new_root=final_storage_root,
    );

    let (prev_value) = get_contract_state_hash(
        class_hash=prev_state.class_hash, storage_root=initial_storage_root, nonce=prev_state.nonce
    );
    assert hashed_state_changes.prev_value = prev_value;
    let (new_value) = get_contract_state_hash(
        class_hash=new_state.class_hash, storage_root=final_storage_root, nonce=new_state_nonce
    );
    assert hashed_state_changes.new_value = new_value;
    assert hashed_state_changes.key = state_changes.key;

    %{ global_state_storage.write(address=ids.hashed_state_changes.key, value=ids.new_value) %}

    let hashed_state_changes = hashed_state_changes + DictAccess.SIZE;

    // Write storage updates to output (storage_updates_ptr).

    // Prepare updates.
    local storage_updates_start: StorageUpdateEntry*;
    %{ ids.storage_updates_start = segments.add_temp_segment() %}
    let storage_updates = storage_updates_start;
    with storage_updates {
        serialize_da_changes(update_ptr=squashed_storage_dict, n_updates=n_updates);
    }

    // Number of actual updates.
    local n_updates = (storage_updates - storage_updates_start) / StorageUpdateEntry.SIZE;

    if (n_updates == 0 and new_state_nonce == prev_state.nonce) {
        // Relocate the temporary segment even if it's empty (to fix the addresses written in
        // the memory).
        relocate_segment(src_ptr=storage_updates_start, dest_ptr=storage_updates_ptr);

        // There are no storage updates for this contract.
        return hash_state_changes(
            n_state_changes=n_state_changes - 1,
            state_changes=state_changes + DictAccess.SIZE,
            hashed_state_changes=hashed_state_changes,
            patricia_update_constants=patricia_update_constants,
        );
    }

    // Write contract address, nonce and number of updates.
    assert [storage_updates_ptr] = state_changes.key;
    assert_nn_le(n_updates, N_UPDATES_BOUND - 1);
    assert_nn_le(new_state_nonce, NONCE_BOUND - 1);
    assert [storage_updates_ptr + 1] = new_state_nonce * N_UPDATES_BOUND + n_updates;
    let storage_updates_ptr = storage_updates_ptr + 2;

    // Write the updates.
    relocate_segment(src_ptr=storage_updates_start, dest_ptr=storage_updates_ptr);
    let storage_updates_ptr = cast(storage_updates, felt*);

    let n_actual_state_changes = n_actual_state_changes + 1;

    return hash_state_changes(
        n_state_changes=n_state_changes - 1,
        state_changes=state_changes + DictAccess.SIZE,
        hashed_state_changes=hashed_state_changes,
        patricia_update_constants=patricia_update_constants,
    );
}
