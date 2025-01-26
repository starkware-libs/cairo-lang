from starkware.cairo.common.dict import DictAccess
from starkware.cairo.common.math import assert_nn_le
from starkware.cairo.common.math_cmp import is_not_zero
from starkware.starknet.core.os.state.commitment import StateEntry

// The packed on-chain data for contract state changes has the following format:
//
// * The number of affected contracts.
// * For each contract:
//   * Header:
//     * The contract address (1 word).
//     * 1 word with the following info:
//       * A flag indicating whether the class hash was updated,
//       * A flag indicating whether the number of updates is small (< 256),
//       * the number of entry updates (packed according to the previous flag),
//       * the new nonce (if it was updated),
//          +-------------+----------------+------------+ LSB
//          | n_updates   | n_updates_flag | class_flag |
//          | 8 or 64 bit | 1 bit          | 1 bit      |
//          +-------------+----------------+------------+
//         OR (if the nonce was updated)
//          +-----------+-------------+----------------+------------+ LSB
//          | new_nonce | n_updates   | n_updates_flag | class_flag |
//          | 64 bits   | 8 or 64 bit | 1 bit          | 1 bit      |
//          +-----------+-------------+----------------+------------+
//
//   * The new class hash for this contract (1 word, if it was updated).
//   * For each entry update:
//       * key (1 word).
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

struct FullContractHeader {
    address: felt,
    prev_nonce: felt,
    new_nonce: felt,
    prev_class_hash: felt,
    new_class_hash: felt,
    n_storage_diffs: felt,
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

// Gets the output of `serialize_full_contract_state_diff` and applies the following modifications:
//   * Packs the header (See documentation in the beginning of the file for more information).
//   * Maps FullStateUpdateEntries into StateUpdateEntries - i.e., drops the previous values.
// The result is written to `res`.
//
// Assumption: `contract_state_diff` came from `serialize_full_contract_state_diff`, and
// therefore does not contain trivial updates.
func pack_contract_state_diff{range_check_ptr, res: felt*}(contract_state_diff: felt*) {
    alloc_locals;
    local n_contracts = contract_state_diff[0];
    res[0] = n_contracts;
    let res = &res[1];
    return pack_contract_state_diff_inner(
        n_contracts=n_contracts, contract_state_diff=&contract_state_diff[1]
    );
}

// Helper function for `pack_contract_state_diff()`.
func pack_contract_state_diff_inner{range_check_ptr, res: felt*}(
    n_contracts: felt, contract_state_diff: felt*
) {
    if (n_contracts == 0) {
        return ();
    }
    alloc_locals;
    let contract_header: FullContractHeader* = cast(contract_state_diff, FullContractHeader*);

    // Write the contract address.
    assert res[0] = contract_header.address;

    // Write the packed info of the contract in the next word.
    // Handle the nonce.
    local new_nonce = contract_header.new_nonce;
    if (contract_header.prev_nonce != new_nonce) {
        assert_nn_le(new_nonce, NONCE_BOUND - 1);
        tempvar packed_info = new_nonce;
    } else {
        tempvar range_check_ptr = range_check_ptr;
        tempvar packed_info = 0;
    }

    // Add the number of updates.
    local n_updates = contract_header.n_storage_diffs;
    local is_n_updates_small;
    %{ ids.is_n_updates_small = ids.n_updates < ids.N_UPDATES_SMALL_PACKING_BOUND %}
    // Verify that the guessed value is 0 or 1.
    assert is_n_updates_small * is_n_updates_small = is_n_updates_small;
    if (is_n_updates_small != 0) {
        tempvar n_updates_bound = N_UPDATES_SMALL_PACKING_BOUND;
    } else {
        tempvar n_updates_bound = N_UPDATES_BOUND;
    }
    assert_nn_le(n_updates, n_updates_bound - 1);
    let packed_info = packed_info * n_updates_bound + n_updates;

    // Add 'is_n_updates_small' flag.
    let packed_info = packed_info * 2 + is_n_updates_small;

    // Add 'was class updated' flag.
    local new_class_hash = contract_header.new_class_hash;
    let was_class_updated = is_not_zero(contract_header.prev_class_hash - new_class_hash);
    let packed_info = packed_info * 2 + was_class_updated;

    assert res[1] = packed_info;

    // Handle the class hash.
    if (was_class_updated != 0) {
        // Write the new class hash.
        assert res[2] = new_class_hash;
        tempvar res = &res[3];
    } else {
        tempvar res = &res[2];
    }

    // Write the storage diff.
    let storage_diff = cast(&contract_state_diff[FullContractHeader.SIZE], FullStateUpdateEntry*);
    let state_updates = cast(res, StateUpdateEntry*);
    map_full_entries_to_entries{full_entries=storage_diff, entries=state_updates}(
        n_entries=n_updates
    );

    // Cast back.
    let res = cast(state_updates, felt*);
    let contract_state_diff = cast(storage_diff, felt*);
    return pack_contract_state_diff_inner(
        n_contracts=n_contracts - 1, contract_state_diff=contract_state_diff
    );
}

// Maps `full_entries` (FullStateUpdateEntry*) into `entries` (StateUpdateEntry*).
func map_full_entries_to_entries{full_entries: FullStateUpdateEntry*, entries: StateUpdateEntry*}(
    n_entries: felt
) {
    if (n_entries == 0) {
        return ();
    }
    let full_entry = full_entries[0];
    assert entries[0] = StateUpdateEntry(key=full_entry.key, value=full_entry.new_value);
    let full_entries = &full_entries[1];
    let entries = &entries[1];
    return map_full_entries_to_entries(n_entries=n_entries - 1);
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

// Writes the contract state diff into `res`, in the following format:
//   * Number of modified contracts,
//   * For each modified contract, write the FullContractHeader followed by the
//     full contract storage diff (FullStateUpdateEntries).
//
// The terminology is "diff" instead of "updates" since this function drops trivial storage and
// contract updates (e.g., storage reads are removed).
//
// Assumption: The dictionary `contract_state_changes` is squashed - but not necessarily sorted:
// this can happen when it has aliases instead of keys (the original dict was sorted by keys).
func serialize_full_contract_state_diff{range_check_ptr, res: felt*}(
    n_contracts: felt, contract_state_changes: DictAccess*
) {
    alloc_locals;

    // Make room for number of modified contracts.
    let output_n_modified_contracts = res[0];
    let res = &res[1];
    // The number of contracts with a non-trivial diff.
    let n_modified_contracts = 0;

    with n_modified_contracts {
        serialize_full_contract_state_diff_inner(
            n_contracts=n_contracts, state_changes=contract_state_changes
        );
    }
    // Write number of modified contracts.
    assert output_n_modified_contracts = n_modified_contracts;

    return ();
}

// Helper function for `serialize_full_contract_state_diff()`.
//
// Increases `n_modified_contracts` by the number of contracts with actual diff.
func serialize_full_contract_state_diff_inner{range_check_ptr, res: felt*, n_modified_contracts}(
    n_contracts: felt, state_changes: DictAccess*
) {
    if (n_contracts == 0) {
        return ();
    }
    alloc_locals;

    local prev_state: StateEntry* = cast(state_changes.prev_value, StateEntry*);
    local new_state: StateEntry* = cast(state_changes.new_value, StateEntry*);

    local storage_dict_start: DictAccess* = prev_state.storage_ptr;
    let storage_dict_end: DictAccess* = new_state.storage_ptr;
    local n_updates = (storage_dict_end - storage_dict_start) / DictAccess.SIZE;

    // Write the full storage diff.
    let storage_diff_ptr: felt* = &res[FullContractHeader.SIZE];
    let n_storage_diffs = serialize_da_changes{state_updates_ptr=storage_diff_ptr}(
        update_ptr=storage_dict_start, n_updates=n_updates, full_output=1
    );
    if (n_storage_diffs == 0 and prev_state.nonce == new_state.nonce and
        prev_state.class_hash == new_state.class_hash) {
        // There are no updates for this contract.
        return serialize_full_contract_state_diff_inner(
            n_contracts=n_contracts - 1, state_changes=&state_changes[1]
        );
    }

    // Write the full contract header.
    let contract_header = cast(res, FullContractHeader*);
    assert [contract_header] = FullContractHeader(
        address=state_changes.key,
        prev_nonce=prev_state.nonce,
        new_nonce=new_state.nonce,
        prev_class_hash=prev_state.class_hash,
        new_class_hash=new_state.class_hash,
        n_storage_diffs=n_storage_diffs,
    );

    let res = cast(storage_diff_ptr, felt*);
    let n_modified_contracts = n_modified_contracts + 1;
    return serialize_full_contract_state_diff_inner(
        n_contracts=n_contracts - 1, state_changes=&state_changes[1]
    );
}
