from starkware.cairo.common.dict import DictAccess
from starkware.cairo.common.math import assert_nn_le
from starkware.cairo.common.math_cmp import is_not_zero
from starkware.starknet.core.os.state.commitment import StateEntry

// The on-chain data for contract state changes has the following format:
//
// * The number of affected contracts.
// * For each contract:
//   * Header:
//     * The contract address (1 word).
//     * 1 word with the following info:
//       * A flag indicating whether the class hash was updated,
//       * A flag indicating whether the number of updates is small (< 256),
//       * the number of entry updates (packed according to the previous flag),
//       * the new nonce (if `full_output` is used or if it was updated),
//       * the old nonce (if `full_output` is used),
//          +-------------+----------------+------------+ LSB
//          | n_updates   | n_updates_flag | class_flag |
//          | 8 or 64 bit | 1 bit          | 1 bit      |
//          +-------------+----------------+------------+
//         OR (if the nonce was updated)
//          +-----------+-------------+----------------+------------+ LSB
//          | new_nonce | n_updates   | n_updates_flag | class_flag |
//          | 64 bits   | 8 or 64 bit | 1 bit          | 1 bit      |
//          +-----------+-------------+----------------+------------+
//         OR (if `full_output` is used)
//          +-----------+-----------+-------------+----------------+------------+ LSB
//          | old_nonce | new_nonce | n_updates   | n_updates_flag | class_flag |
//          | 64 bits   | 64 bits   | 8 or 64 bit | 1 bit          | 1 bit      |
//          +-----------+-----------+-------------+----------------+------------+
//
//   * The old class hash for this contract (1 word, if `full_output` is used).
//   * The new class hash for this contract (1 word, if it was updated or `full_output` is used).
//   * For each entry update:
//       * key (1 word).
//       * old value (1 word, only when `full_output` is used).
//       * new value (1 word).
//
// The on-chain data for contract class changes has the following format:
// * The number of classes that have been declared.
// * For each contract class:
//   * The class hash (1 word).
//   * The old compiled class hash (1 word, only when `full_output` is used).
//   * The compiled class hash (casm, 1 word).

// A bound on the number of contract state entry updates in a contract.
const N_UPDATES_BOUND = 2 ** 64;
// Number of updates that is lower than this bound will be packed more efficiently in the header.
const N_UPDATES_SMALL_PACKING_BOUND = 2 ** 8;
// A bound on the nonce of a contract.
const NONCE_BOUND = 2 ** 64;

// Represents an update of a state entry; Either a contract state entry of a contract or a
// contract class entry in the contract class hash mapping.
struct StateUpdateEntry {
    // The entry's key.
    key: felt,
    // The new value.
    value: felt,
}

struct FullStateUpdateEntry {
    // The entry's key.
    key: felt,
    // The previous value.
    prev_value: felt,
    // The new value.
    new_value: felt,
}

// Outputs the entries that were changed in `update_ptr` into `state_updates_ptr`.
// Returns the number of such entries.
func serialize_da_changes{state_updates_ptr: felt*}(
    update_ptr: DictAccess*, n_updates: felt, full_output: felt
) -> felt {
    if (full_output == 0) {
        // Keep a pointer to the start of the array.
        let state_updates_start = state_updates_ptr;
        // Cast `state_updates_ptr` to `StateUpdateEntry*`.
        let state_updates = cast(state_updates_ptr, StateUpdateEntry*);

        serialize_da_changes_inner{state_updates=state_updates}(
            update_ptr=update_ptr, n_updates=n_updates
        );

        // Cast back to `felt*`.
        let state_updates_ptr = cast(state_updates, felt*);
        return (state_updates_ptr - state_updates_start) / StateUpdateEntry.SIZE;
    } else {
        // Keep a pointer to the start of the array.
        let state_updates_start = state_updates_ptr;
        // Cast `state_updates_ptr` to `FullStateUpdateEntry*`.
        let state_updates_full = cast(state_updates_ptr, FullStateUpdateEntry*);

        serialize_da_changes_inner_full{state_updates=state_updates_full}(
            update_ptr=update_ptr, n_updates=n_updates
        );

        // Cast back to `felt*`.
        let state_updates_ptr = cast(state_updates_full, felt*);
        return (state_updates_ptr - state_updates_start) / FullStateUpdateEntry.SIZE;
    }
}

// Helper function for `serialize_da_changes` for the case `full_output == 0`.
func serialize_da_changes_inner{state_updates: StateUpdateEntry*}(
    update_ptr: DictAccess*, n_updates: felt
) {
    if (n_updates == 0) {
        return ();
    }
    if (update_ptr.prev_value == update_ptr.new_value) {
        tempvar state_updates = state_updates;
    } else {
        assert state_updates[0] = StateUpdateEntry(key=update_ptr.key, value=update_ptr.new_value);
        tempvar state_updates = &state_updates[1];
    }
    return serialize_da_changes_inner(update_ptr=&update_ptr[1], n_updates=n_updates - 1);
}

// Helper function for `serialize_da_changes` for the case `full_output == 1`.
func serialize_da_changes_inner_full{state_updates: FullStateUpdateEntry*}(
    update_ptr: DictAccess*, n_updates: felt
) {
    if (n_updates == 0) {
        return ();
    }
    if (update_ptr.prev_value == update_ptr.new_value) {
        tempvar state_updates = state_updates;
    } else {
        assert state_updates[0] = FullStateUpdateEntry(
            key=update_ptr.key, prev_value=update_ptr.prev_value, new_value=update_ptr.new_value
        );
        tempvar state_updates = &state_updates[1];
    }
    return serialize_da_changes_inner_full(update_ptr=&update_ptr[1], n_updates=n_updates - 1);
}

// Writes the changed values in the contract state into `state_updates_ptr`
// to make this data available on-chain.
// See documentation in the beginning of the file for more information.
//
// Assumption: The dictionary `contract_state_changes_start` is squashed.
func output_contract_state{range_check_ptr, state_updates_ptr: felt*}(
    contract_state_changes_start: DictAccess*, n_contract_state_changes: felt, full_output: felt
) {
    alloc_locals;

    // Make room for number of modified contracts.
    let output_n_modified_contracts = [state_updates_ptr];
    let state_updates_ptr = state_updates_ptr + 1;
    let n_modified_contracts = 0;

    with n_modified_contracts {
        output_contract_state_inner(
            n_contract_state_changes=n_contract_state_changes,
            state_changes=contract_state_changes_start,
            full_output=full_output,
        );
    }
    // Write number of modified contracts.
    assert output_n_modified_contracts = n_modified_contracts;

    return ();
}

// Helper function for `output_contract_state()`.
//
// Increases `n_modified_contracts` by the number of contracts with state changes.
func output_contract_state_inner{range_check_ptr, state_updates_ptr: felt*, n_modified_contracts}(
    n_contract_state_changes: felt, state_changes: DictAccess*, full_output: felt
) {
    if (n_contract_state_changes == 0) {
        return ();
    }
    alloc_locals;

    local prev_state: StateEntry* = cast(state_changes.prev_value, StateEntry*);
    local new_state: StateEntry* = cast(state_changes.new_value, StateEntry*);
    local prev_state_nonce = prev_state.nonce;
    local new_state_nonce = new_state.nonce;

    local storage_dict_start: DictAccess* = prev_state.storage_ptr;
    let storage_dict_end: DictAccess* = new_state.storage_ptr;
    local n_updates = (storage_dict_end - storage_dict_start) / DictAccess.SIZE;

    // Write contract state updates to output (state_updates_ptr).

    // Prepare updates.
    let contract_header = state_updates_ptr;

    // Class hash.
    local was_class_updated = is_not_zero(prev_state.class_hash - new_state.class_hash);
    const BASE_HEADER_SIZE = 2;
    if (full_output != 0) {
        // Write the previous and new class hash.
        assert contract_header[BASE_HEADER_SIZE] = prev_state.class_hash;
        assert contract_header[BASE_HEADER_SIZE + 1] = new_state.class_hash;
        // The offset of the storage diff from the header.
        tempvar storage_diff_offset = BASE_HEADER_SIZE + 2;
    } else {
        if (was_class_updated != 0) {
            // Write the new class hash.
            assert contract_header[BASE_HEADER_SIZE] = new_state.class_hash;
            // The offset of the storage diff from the header.
            tempvar storage_diff_offset = BASE_HEADER_SIZE + 1;
        } else {
            tempvar storage_diff_offset = BASE_HEADER_SIZE;
        }
    }

    let storage_diff: felt* = contract_header + storage_diff_offset;
    let n_actual_updates = serialize_da_changes{state_updates_ptr=storage_diff}(
        update_ptr=storage_dict_start, n_updates=n_updates, full_output=full_output
    );

    if (full_output == 0 and n_actual_updates == 0 and new_state_nonce == prev_state_nonce and
        was_class_updated == 0) {
        // There are no updates for this contract.
        return output_contract_state_inner(
            n_contract_state_changes=n_contract_state_changes - 1,
            state_changes=&state_changes[1],
            full_output=full_output,
        );
    }

    // Complete the header; Write contract address.
    assert contract_header[0] = state_changes.key;

    // Write the second word of the header.
    // Handle the nonce.
    assert_nn_le(new_state_nonce, NONCE_BOUND - 1);
    if (full_output == 0) {
        if (prev_state_nonce != new_state_nonce) {
            tempvar value = new_state_nonce;
        } else {
            tempvar value = 0;
        }
        tempvar range_check_ptr = range_check_ptr;
    } else {
        // Full output - write the new and old nonces.
        assert_nn_le(prev_state_nonce, NONCE_BOUND - 1);
        tempvar value = prev_state_nonce * NONCE_BOUND + new_state_nonce;
        tempvar range_check_ptr = range_check_ptr;
    }

    // Write the number of updates.
    local is_n_updates_small;
    %{ ids.is_n_updates_small = ids.n_actual_updates < ids.N_UPDATES_SMALL_PACKING_BOUND %}
    // Verify that the guessed value is 0 or 1.
    assert is_n_updates_small * is_n_updates_small = is_n_updates_small;
    if (is_n_updates_small != 0) {
        tempvar n_updates_bound = N_UPDATES_SMALL_PACKING_BOUND;
    } else {
        tempvar n_updates_bound = N_UPDATES_BOUND;
    }
    assert_nn_le(n_actual_updates, n_updates_bound - 1);
    let value = value * n_updates_bound + n_actual_updates;

    // Write 'is_n_updates_small' flag.
    let value = value * 2 + is_n_updates_small;

    // Write 'was class updated' flag.
    let value = value * 2 + was_class_updated;

    assert contract_header[1] = value;

    let state_updates_ptr = cast(storage_diff, felt*);
    let n_modified_contracts = n_modified_contracts + 1;

    return output_contract_state_inner(
        n_contract_state_changes=n_contract_state_changes - 1,
        state_changes=&state_changes[1],
        full_output=full_output,
    );
}

// Serializes changes in the contract class tree into 'state_updates_ptr'.
func output_contract_class_da_changes{state_updates_ptr: felt*}(
    update_ptr: DictAccess*, n_updates: felt, full_output: felt
) {
    alloc_locals;

    // Allocate space for the number of changes.
    let n_diffs_output_placeholder = state_updates_ptr[0];
    let state_updates_ptr = &state_updates_ptr[1];

    // Write the updates.
    with state_updates_ptr {
        let n_actual_updates = serialize_da_changes(
            update_ptr=update_ptr, n_updates=n_updates, full_output=full_output
        );
    }

    // Write the number of updates.
    assert n_diffs_output_placeholder = n_actual_updates;

    return ();
}
