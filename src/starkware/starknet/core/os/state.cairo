from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.builtin_poseidon.poseidon import poseidon_hash, poseidon_hash_many
from starkware.cairo.common.cairo_builtins import HashBuiltin, PoseidonBuiltin
from starkware.cairo.common.dict import DictAccess, squash_dict
from starkware.cairo.common.hash import hash2
from starkware.cairo.common.math import assert_nn_le
from starkware.cairo.common.math_cmp import is_not_zero
from starkware.cairo.common.patricia import (
    patricia_update_constants_new,
    patricia_update_using_update_constants,
)
from starkware.cairo.common.patricia_utils import PatriciaUpdateConstants
from starkware.cairo.common.patricia_with_poseidon import (
    patricia_update_using_update_constants as patricia_update_using_update_constants_with_poseidon,
)
from starkware.cairo.common.segments import relocate_segment

const MERKLE_HEIGHT = 251;  // PRIME.bit_length() - 1.
const UNINITIALIZED_CLASS_HASH = 0;
const GLOBAL_STATE_VERSION = 'STARKNET_STATE_V0';
const CONTRACT_CLASS_LEAF_VERSION = 'CONTRACT_CLASS_LEAF_V0';

// The on-chain data for contract state changes has the following format:
//
// * The number of affected contracts.
// * For each contract:
//   * Header:
//     * The contract address (1 word).
//     * 1 word with the following info:
//       * A flag indicating whether the class hash was updated,
//       * the number of entry updates,
//       * and the new nonce:
//          +-------+-----------+-----------+ LSB
//          | flag  | new nonce | n_updates |
//          | 1 bit | 64 bits   | 64 bits   |
//          +-------+-----------+-----------+
//   * The class hash for this contract (if it was updated) (0 or 1 word).
//   * For each entry update:
//       * key (1 word).
//       * new value (1 word).

// The on-chain data for contract class changes has the following format:
// * The number of classes that have been declared.
// * For each contract class:
//   * The class hash (1 word).
//   * The compiled class hash (casm, 1 word).

// A bound on the number of contract state entry updates in a contract.
const N_UPDATES_BOUND = 2 ** 64;
// A bound on the nonce of a contract.
const NONCE_BOUND = 2 ** 64;

struct StateChanges {
    // A dictionary from address to StateEntry.
    contract_state_changes_start: DictAccess*,
    contract_state_changes_end: DictAccess*,
    // A dictionary from class hash to compiled class hash.
    class_changes_start: DictAccess*,
    class_changes_end: DictAccess*,
}

struct StateUpdateOutput {
    initial_root: felt,
    final_root: felt,
}

struct StateEntry {
    class_hash: felt,
    storage_ptr: DictAccess*,
    nonce: felt,
}

// Represents an update of a state entry; Either a contract state entry of a contract or a
// contract class entry in the contract class hash mapping.
struct StateUpdateEntry {
    // The entry's key.
    key: felt,
    // The new value.
    value: felt,
}

func serialize_da_changes{state_updates: StateUpdateEntry*}(
    update_ptr: DictAccess*, n_updates: felt
) {
    if (n_updates == 0) {
        return ();
    }
    if (update_ptr.prev_value == update_ptr.new_value) {
        tempvar state_updates = state_updates;
    } else {
        assert [state_updates] = StateUpdateEntry(key=update_ptr.key, value=update_ptr.new_value);
        tempvar state_updates = state_updates + StateUpdateEntry.SIZE;
    }
    return serialize_da_changes(update_ptr=update_ptr + DictAccess.SIZE, n_updates=n_updates - 1);
}

// Serializes changes in the contract class tree into 'state_updates_ptr'.
func serialize_contract_class_da_changes{state_updates_ptr: felt*}(
    update_ptr: DictAccess*, n_updates: felt
) {
    alloc_locals;

    // Allocate space for the number of changes.
    let n_diffs_output_placeholder = state_updates_ptr[0];
    let state_updates_ptr = &state_updates_ptr[1];

    // Write the updates.
    local state_updates: StateUpdateEntry* = cast(state_updates_ptr, StateUpdateEntry*);
    let state_updates_start = state_updates;
    with state_updates {
        serialize_da_changes(update_ptr=update_ptr, n_updates=n_updates);
    }
    let state_updates_ptr = cast(state_updates, felt*);

    // Write the number of updates.
    let n_diffs = (state_updates - state_updates_start) / StateUpdateEntry.SIZE;
    assert n_diffs_output_placeholder = n_diffs;

    return ();
}

// Calculates and returns the global state root given the contract state root and
// the contract class state root.
// If both the contract class and contract state trees are empty, the global root is set to 0.
// If the contract class tree is empty, the global state root is equal to the
// contract state root (for backward compatibility);
// Otherwise, the global root is obtained by:
//     global_root = H(GLOBAL_STATE_VERSION, contract_state_root, contract_class_root).
func calculate_global_state_root{poseidon_ptr: PoseidonBuiltin*, range_check_ptr}(
    contract_state_root: felt, contract_class_root: felt
) -> (global_root: felt) {
    if (contract_state_root == 0 and contract_class_root == 0) {
        // The state is empty.
        return (global_root=0);
    }

    // Backward compatibility; Used during the migration from a state without a
    // contract class tree to a state with a contract class tree.
    if (contract_class_root == 0) {
        // The contract classes' state is empty.
        return (global_root=contract_state_root);
    }

    tempvar elements: felt* = new (GLOBAL_STATE_VERSION, contract_state_root, contract_class_root);
    let (global_root) = poseidon_hash_many(n=3, elements=elements);
    return (global_root=global_root);
}

// Performs the commitment tree updates required for (validating and) updating the global state.
// Returns a StateUpdateOutput struct.
// Writes the changed values (contract storage and declared class hashes) into state_updates_ptr.
func state_update{
    poseidon_ptr: PoseidonBuiltin*,
    hash_ptr: HashBuiltin*,
    range_check_ptr,
    state_updates_ptr: felt*,
}(state_changes: StateChanges*) -> (state_update_output: StateUpdateOutput*) {
    alloc_locals;

    // Create PatriciaUpdateConstants struct for patricia update.
    let (local patricia_update_constants: PatriciaUpdateConstants*) = patricia_update_constants_new(
        );

    // Update the contract state tree.
    let (contract_state_tree_update_output) = contract_state_update(
        contract_state_changes_start=state_changes.contract_state_changes_start,
        contract_state_changes_end=state_changes.contract_state_changes_end,
        patricia_update_constants=patricia_update_constants,
    );

    // Update the contract class tree.
    let (contract_class_tree_update_output) = contract_class_update(
        class_changes_start=state_changes.class_changes_start,
        class_changes_end=state_changes.class_changes_end,
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

    return (
        state_update_output=new StateUpdateOutput(
            initial_root=initial_global_root, final_root=final_global_root
        ),
    );
}

// Performs the commitment tree updates required for (validating and) updating the
// contract class tree.
// Returns a StateUpdateOutput struct for the tree.
// Checks that [class_changes_start, class_changes_end) is a valid dictionary according to
// squash_dict.
// Writes the changed values into state_updates_ptr, to make this data available on-chain.
func contract_class_update{
    poseidon_ptr: PoseidonBuiltin*, range_check_ptr, state_updates_ptr: felt*
}(
    class_changes_start: DictAccess*,
    class_changes_end: DictAccess*,
    patricia_update_constants: PatriciaUpdateConstants*,
) -> (contract_class_tree_update_output: StateUpdateOutput) {
    alloc_locals;

    // Guess the initial and final roots of the contract class tree.
    local initial_root;
    local final_root;
    %{
        ids.initial_root = os_input.contract_class_commitment_info.previous_root
        ids.final_root = os_input.contract_class_commitment_info.updated_root
        preimage = {
            int(root): children
            for root, children in os_input.contract_class_commitment_info.commitment_facts.items()
        }
        assert os_input.contract_class_commitment_info.tree_height == ids.MERKLE_HEIGHT
    %}

    let (local squashed_dict: DictAccess*) = alloc();
    let (local squashed_dict_end) = squash_dict(
        dict_accesses=class_changes_start,
        dict_accesses_end=class_changes_end,
        squashed_dict=squashed_dict,
    );

    local n_class_updates = (squashed_dict_end - squashed_dict) / DictAccess.SIZE;

    // Create a dictionary mapping class hash to the contract class leaf hash,
    // to prepare the input for the commitment tree update.
    let (local hashed_class_changes: DictAccess*) = alloc();
    hash_class_changes(
        n_class_updates=n_class_updates,
        class_changes=squashed_dict,
        hashed_class_changes=hashed_class_changes,
    );

    // Call patricia_update_using_update_constants() instead of patricia_update()
    // in order not to repeat globals_pow2 calculation.
    patricia_update_using_update_constants_with_poseidon(
        patricia_update_constants=patricia_update_constants,
        update_ptr=hashed_class_changes,
        n_updates=n_class_updates,
        height=MERKLE_HEIGHT,
        prev_root=initial_root,
        new_root=final_root,
    );

    serialize_contract_class_da_changes(update_ptr=squashed_dict, n_updates=n_class_updates);

    return (
        contract_class_tree_update_output=StateUpdateOutput(
            initial_root=initial_root, final_root=final_root
        ),
    );
}

// Takes a dict mapping class hash to compiled class hash and produces
// a dict mapping class hash to the corresponding leaf hash input dict.
// The output is written to 'hashed_state_changes'.
func hash_class_changes{poseidon_ptr: PoseidonBuiltin*}(
    n_class_updates: felt, class_changes: DictAccess*, hashed_class_changes: DictAccess*
) {
    if (n_class_updates == 0) {
        return ();
    }

    alloc_locals;

    let (local prev_value) = get_contract_class_leaf_hash(
        compiled_class_hash=class_changes.prev_value
    );
    let (new_value) = get_contract_class_leaf_hash(compiled_class_hash=class_changes.new_value);
    assert hashed_class_changes[0] = DictAccess(
        key=class_changes.key, prev_value=prev_value, new_value=new_value
    );

    return hash_class_changes(
        n_class_updates=n_class_updates - 1,
        class_changes=&class_changes[1],
        hashed_class_changes=&hashed_class_changes[1],
    );
}

// Hashes a contract class leaf.
// A contract class leaf contains a compiled class hash and the leaf version.
// Returns H(compiled_class_hash, leaf_version).
func get_contract_class_leaf_hash{poseidon_ptr: PoseidonBuiltin*}(compiled_class_hash: felt) -> (
    hash: felt
) {
    if (compiled_class_hash == UNINITIALIZED_CLASS_HASH) {
        return (hash=0);
    }

    // Return H(CONTRACT_CLASS_LEAF_VERSION, compiled_class_hash).
    let (hash_value) = poseidon_hash(CONTRACT_CLASS_LEAF_VERSION, compiled_class_hash);
    return (hash=hash_value);
}

// Performs the commitment tree updates required for (validating and) updating the global state of
// the contracts.
// Returns a StateUpdateOutput struct regarding the global contracts' state.
// Checks that [contract_state_changes_start, contract_state_changes_end) is a valid dictionary
// according to squash_dict.
// Writes the changed values into state_updates_ptr, to make this data available on-chain.
func contract_state_update{hash_ptr: HashBuiltin*, range_check_ptr, state_updates_ptr: felt*}(
    contract_state_changes_start: DictAccess*,
    contract_state_changes_end: DictAccess*,
    patricia_update_constants: PatriciaUpdateConstants*,
) -> (contract_state_tree_update_output: StateUpdateOutput) {
    alloc_locals;
    let (local squashed_dict: DictAccess*) = alloc();

    // Squash the global dictionary to get a list of triples (addr, dict_begin, dict_end).
    let (squashed_dict_end) = squash_dict(
        dict_accesses=contract_state_changes_start,
        dict_accesses_end=contract_state_changes_end,
        squashed_dict=squashed_dict,
    );

    // Hash the entries of the contract state changes to prepare the input for the commitment tree
    // multi-update.
    let (local hashed_state_changes: DictAccess*) = alloc();
    local n_contract_state_changes = (squashed_dict_end - squashed_dict) / DictAccess.SIZE;
    // Make room for number of state updates.
    let output_n_updates = [state_updates_ptr];
    let state_updates_ptr = state_updates_ptr + 1;
    let n_actual_state_changes = 0;

    with n_actual_state_changes {
        hash_state_changes(
            n_contract_state_changes=n_contract_state_changes,
            state_changes=squashed_dict,
            hashed_state_changes=hashed_state_changes,
            patricia_update_constants=patricia_update_constants,
        );
    }
    // Write number of state updates.
    assert output_n_updates = n_actual_state_changes;

    // Compute the initial and final roots of the contracts' state tree.
    local initial_root;
    local final_root;

    %{
        ids.initial_root = os_input.contract_state_commitment_info.previous_root
        ids.final_root = os_input.contract_state_commitment_info.updated_root
        preimage = {
            int(root): children
            for root, children in os_input.contract_state_commitment_info.commitment_facts.items()
        }
        assert os_input.contract_state_commitment_info.tree_height == ids.MERKLE_HEIGHT
    %}

    // Call patricia_update_using_update_constants() instead of patricia_update()
    // in order not to repeat globals_pow2 calculation.
    patricia_update_using_update_constants(
        patricia_update_constants=patricia_update_constants,
        update_ptr=hashed_state_changes,
        n_updates=n_contract_state_changes,
        height=MERKLE_HEIGHT,
        prev_root=initial_root,
        new_root=final_root,
    );

    return (
        contract_state_tree_update_output=StateUpdateOutput(
            initial_root=initial_root, final_root=final_root
        ),
    );
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
// Writes all contract state changes to output (state_updates_ptr), 'n_actual_state_changes'
// will hold the number of contracts with state changes.
func hash_state_changes{
    hash_ptr: HashBuiltin*, range_check_ptr, state_updates_ptr: felt*, n_actual_state_changes
}(
    n_contract_state_changes: felt,
    state_changes: DictAccess*,
    hashed_state_changes: DictAccess*,
    patricia_update_constants: PatriciaUpdateConstants*,
) {
    if (n_contract_state_changes == 0) {
        return ();
    }
    alloc_locals;

    local prev_state: StateEntry* = cast(state_changes.prev_value, StateEntry*);
    local new_state: StateEntry* = cast(state_changes.new_value, StateEntry*);
    local new_state_nonce = new_state.nonce;
    let (local squashed_contract_state_dict: DictAccess*) = alloc();
    local initial_contract_state_root;
    local final_contract_state_root;

    %{
        storage = storage_by_address[ids.state_changes.key]
        ids.initial_contract_state_root = storage.commitment_info.previous_root
        ids.final_contract_state_root = storage.commitment_info.updated_root
        preimage = {
            int(root): children
            for root, children in storage.commitment_info.commitment_facts.items()
        }
        assert storage.commitment_info.tree_height == ids.MERKLE_HEIGHT
    %}
    let (local squashed_contract_state_dict_end) = squash_dict(
        dict_accesses=prev_state.storage_ptr,
        dict_accesses_end=new_state.storage_ptr,
        squashed_dict=squashed_contract_state_dict,
    );

    local n_updates = (squashed_contract_state_dict_end - squashed_contract_state_dict) /
        DictAccess.SIZE;
    // Call patricia_update_using_update_constants() instead of patricia_update()
    // in order not to repeat globals_pow2 calculation.
    patricia_update_using_update_constants(
        patricia_update_constants=patricia_update_constants,
        update_ptr=squashed_contract_state_dict,
        n_updates=n_updates,
        height=MERKLE_HEIGHT,
        prev_root=initial_contract_state_root,
        new_root=final_contract_state_root,
    );

    let (prev_value) = get_contract_state_hash(
        class_hash=prev_state.class_hash,
        storage_root=initial_contract_state_root,
        nonce=prev_state.nonce,
    );
    assert hashed_state_changes.prev_value = prev_value;
    let (new_value) = get_contract_state_hash(
        class_hash=new_state.class_hash,
        storage_root=final_contract_state_root,
        nonce=new_state_nonce,
    );
    assert hashed_state_changes.new_value = new_value;
    assert hashed_state_changes.key = state_changes.key;

    let hashed_state_changes = hashed_state_changes + DictAccess.SIZE;

    // Write contract state updates to output (state_updates_ptr).

    // Prepare updates.
    local contract_state_updates_start: StateUpdateEntry*;
    %{ ids.contract_state_updates_start = segments.add_temp_segment() %}
    let contract_state_updates = contract_state_updates_start;
    serialize_da_changes{state_updates=contract_state_updates}(
        update_ptr=squashed_contract_state_dict, n_updates=n_updates
    );

    let was_class_updated = is_not_zero(prev_state.class_hash - new_state.class_hash);

    // Number of actual updates.
    local n_updates = (contract_state_updates - contract_state_updates_start) /
        StateUpdateEntry.SIZE;

    if (n_updates == 0 and new_state_nonce == prev_state.nonce and was_class_updated == 0) {
        // Relocate the temporary segment even if it's empty (to fix the addresses written in
        // the memory).
        relocate_segment(src_ptr=contract_state_updates_start, dest_ptr=state_updates_ptr);

        // There are no updates for this contract.
        return hash_state_changes(
            n_contract_state_changes=n_contract_state_changes - 1,
            state_changes=state_changes + DictAccess.SIZE,
            hashed_state_changes=hashed_state_changes,
            patricia_update_constants=patricia_update_constants,
        );
    }

    // Write contract address.
    assert [state_updates_ptr] = state_changes.key;
    let state_updates_ptr = state_updates_ptr + 1;

    // Write the second word of the header.
    // Write 'was class update' flag.
    let value = was_class_updated;
    // Write the nonce.
    assert_nn_le(new_state_nonce, NONCE_BOUND - 1);
    let value = value * NONCE_BOUND + new_state_nonce;
    // Write the number of updates.
    assert_nn_le(n_updates, N_UPDATES_BOUND - 1);
    let value = value * N_UPDATES_BOUND + n_updates;
    assert [state_updates_ptr] = value;
    let state_updates_ptr = state_updates_ptr + 1;

    if (was_class_updated != 0) {
        // Write the new class hash.
        assert [state_updates_ptr] = new_state.class_hash;
        tempvar state_updates_ptr = state_updates_ptr + 1;
    } else {
        tempvar state_updates_ptr = state_updates_ptr;
    }

    // Write the updates.
    relocate_segment(src_ptr=contract_state_updates_start, dest_ptr=state_updates_ptr);
    let state_updates_ptr = cast(contract_state_updates, felt*);

    let n_actual_state_changes = n_actual_state_changes + 1;

    return hash_state_changes(
        n_contract_state_changes=n_contract_state_changes - 1,
        state_changes=state_changes + DictAccess.SIZE,
        hashed_state_changes=hashed_state_changes,
        patricia_update_constants=patricia_update_constants,
    );
}
