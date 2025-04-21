from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE, TRUE
from starkware.cairo.common.dict import DictAccess
from starkware.cairo.common.find_element import find_element, search_sorted_lower
from starkware.cairo.common.math import assert_le_felt, assert_nn_le
from starkware.cairo.common.memcpy import memcpy
from starkware.cairo.common.squash_dict import squash_dict
from starkware.starknet.core.os.constants import ALIAS_CONTRACT_ADDRESS
from starkware.starknet.core.os.state.commitment import StateEntry
from starkware.starknet.core.os.state.output import (
    FullContractHeader,
    FullStateUpdateEntry,
    serialize_full_contract_state_diff,
)

// The maximal contract address for which aliases are not used and all keys are serialized as is,
// without compression.
const MAX_NON_COMPRESSED_CONTRACT_ADDRESS = 15;
// The minimal value for a key to be allocated an alias. Smaller keys are serialized as is (their
// alias is the key).
const MIN_VALUE_FOR_ALIAS_ALLOC = 128;
// The first alias to allocate.
const INITIAL_AVAILABLE_ALIAS = MIN_VALUE_FOR_ALIAS_ALLOC;
// The storage key of the alias counter in the alias contract.
const ALIAS_COUNTER_STORAGE_KEY = 0;

// Finalized, read-only aliases.
struct Aliases {
    len: felt,
    ptr: DictAccess*,
}

// Alias allocation functions.

// Allocates, if needed, an alias for the given key or reads it from the alias contract storage.
// Skips keys smaller than `MIN_VALUE_FOR_ALIAS_ALLOC`.
func maybe_allocate_alias_for_key{
    aliases_storage_updates: DictAccess*, next_available_alias: felt, range_check_ptr
}(key: felt) {
    // No need to allocate an alias for keys < MIN_VALUE_FOR_ALIAS_ALLOC.
    if (nondet %{ ids.key < ids.MIN_VALUE_FOR_ALIAS_ALLOC %} != FALSE) {
        assert_nn_le(a=key, b=MIN_VALUE_FOR_ALIAS_ALLOC - 1);
        return ();
    }

    // Verify the guess above.
    assert_le_felt(a=MIN_VALUE_FOR_ALIAS_ALLOC, b=key);
    maybe_allocate_alias_for_big_key(key=key);
    return ();
}

// Allocates, if needed, an alias for the given key or reads it from the alias contract storage.
// Assumes the given key is at least MIN_VALUE_FOR_ALIAS_ALLOC.
func maybe_allocate_alias_for_big_key{
    aliases_storage_updates: DictAccess*, next_available_alias: felt, range_check_ptr
}(key: felt) {
    alloc_locals;
    // Sanity check.
    %{ assert ids.key >= ids.MIN_VALUE_FOR_ALIAS_ALLOC, f"Key {ids.key} is too small." %}

    // Guess the existing alias for the key (0 is it was not assigned yet). The guess is verified
    // by the storage write below.
    local prev_value: felt = nondet %{ aliases.read(key=ids.key) %};
    if (prev_value == 0) {
        // Allocate a new alias.
        tempvar new_value = next_available_alias;
        %{ aliases.write(key=ids.key, value=ids.next_available_alias) %}
        tempvar next_available_alias = next_available_alias + 1;
    } else {
        tempvar new_value = prev_value;
        tempvar next_available_alias = next_available_alias;
    }
    assert aliases_storage_updates[0] = DictAccess(
        key=key, prev_value=prev_value, new_value=new_value
    );
    let aliases_storage_updates = &aliases_storage_updates[1];
    return ();
}

// Returns the next available alias.
// Deploys the stateful compression feature if needed.
func get_next_available_alias{aliases_storage_updates: DictAccess*, range_check_ptr}() -> felt {
    tempvar next_available_alias = nondet %{ aliases.read(key=ids.ALIAS_COUNTER_STORAGE_KEY) %};
    assert aliases_storage_updates[0] = DictAccess(
        key=ALIAS_COUNTER_STORAGE_KEY,
        prev_value=next_available_alias,
        new_value=next_available_alias,
    );
    let aliases_storage_updates = &aliases_storage_updates[1];

    // First time an alias is created.
    if (next_available_alias == 0) {
        %{ aliases.write(key=ids.ALIAS_COUNTER_STORAGE_KEY, value=ids.INITIAL_AVAILABLE_ALIAS) %}
        assert aliases_storage_updates[0] = DictAccess(
            key=ALIAS_COUNTER_STORAGE_KEY, prev_value=0, new_value=INITIAL_AVAILABLE_ALIAS
        );
        let aliases_storage_updates = &aliases_storage_updates[1];
        return INITIAL_AVAILABLE_ALIAS;
    } else {
        return next_available_alias;
    }
}

// Allocates aliases for storage diff, which is expected to contain only modified storage keys,
// without trivial updates.
func allocate_aliases_for_storage_diff{
    aliases_storage_updates: DictAccess*, next_available_alias: felt, range_check_ptr
}(storage_diff_start: FullStateUpdateEntry*, storage_diff_end: FullStateUpdateEntry*) {
    // Skip keys which are smaller than MIN_VALUE_FOR_ALIAS_ALLOC.
    let storage_diff_big_keys_start = get_storage_diff_big_keys_start(
        storage_diff_start=storage_diff_start, storage_diff_end=storage_diff_end
    );
    return allocate_aliases_for_storage_diff_big_keys(
        storage_diff_start=storage_diff_big_keys_start, storage_diff_end=storage_diff_end
    );
}

// Same as `allocate_aliases_for_storage_diff`, but assumes all keys are at least
// MIN_VALUE_FOR_ALIAS_ALLOC.
func allocate_aliases_for_storage_diff_big_keys{
    aliases_storage_updates: DictAccess*, next_available_alias: felt, range_check_ptr
}(storage_diff_start: FullStateUpdateEntry*, storage_diff_end: FullStateUpdateEntry*) {
    if (storage_diff_start == storage_diff_end) {
        return ();
    }
    maybe_allocate_alias_for_big_key(key=storage_diff_start[0].key);
    return allocate_aliases_for_storage_diff_big_keys(
        storage_diff_start=&storage_diff_start[1], storage_diff_end=storage_diff_end
    );
}

// Allocates aliases for contract state changes.
// New aliases are written to and existing aliases are read from `aliases_storage_updates`.
// (That way, `aliases_storage_updates` will contain all relevant aliases and could be
// used (after squashing) in the replacement phase).
//
// The allocation is done for each contract (sorted by address) in the following order:
//   * Modified storage keys (sorted),
//   * Contract address (if the contract was modified).
//
// Assumption: The dictionary `contract_state_changes` is squashed.
func allocate_aliases{aliases_storage_updates: DictAccess*, range_check_ptr}(
    n_contracts: felt, contract_state_changes: DictAccess*
) {
    alloc_locals;
    // Compute the full contract state diff.
    let contract_state_diff = get_full_contract_state_diff(
        n_contracts=n_contracts, contract_state_changes=contract_state_changes
    );

    // Allocate.
    let next_available_alias = get_next_available_alias();
    local prev_available_alias: felt = next_available_alias;
    with next_available_alias {
        let n_modified_contracts = contract_state_diff[0];
        allocate_aliases_for_contract_state_diff(
            n_contracts=n_modified_contracts, contract_state_diff=&contract_state_diff[1]
        );
    }

    // Update the counter.
    %{ aliases.write(key=ids.ALIAS_COUNTER_STORAGE_KEY, value=ids.next_available_alias) %}
    assert aliases_storage_updates[0] = DictAccess(
        key=ALIAS_COUNTER_STORAGE_KEY,
        prev_value=prev_available_alias,
        new_value=next_available_alias,
    );
    let aliases_storage_updates = &aliases_storage_updates[1];
    return ();
}

// Allocates aliases for contract state diff, which is expected to contain only modified
// contracts and storage keys, without trivial updates.
func allocate_aliases_for_contract_state_diff{
    aliases_storage_updates: DictAccess*, next_available_alias: felt, range_check_ptr
}(n_contracts: felt, contract_state_diff: felt*) {
    if (n_contracts == 0) {
        return ();
    }
    alloc_locals;

    let contract_header = cast(contract_state_diff, FullContractHeader*);
    local contract_address = contract_header.address;
    local storage_diff: FullStateUpdateEntry* = cast(
        &contract_state_diff[FullContractHeader.SIZE], FullStateUpdateEntry*
    );
    local storage_diff_end: FullStateUpdateEntry* = &storage_diff[contract_header.n_storage_diffs];
    let skip_contract = should_skip_contract(contract_address=contract_address);
    if (skip_contract != FALSE) {
        return allocate_aliases_for_contract_state_diff(
            n_contracts=n_contracts - 1, contract_state_diff=storage_diff_end
        );
    }

    // Allocate for the storage diff.
    allocate_aliases_for_storage_diff(
        storage_diff_start=storage_diff, storage_diff_end=storage_diff_end
    );
    // Allocate for the contract address.
    maybe_allocate_alias_for_key(key=contract_address);

    return allocate_aliases_for_contract_state_diff(
        n_contracts=n_contracts - 1, contract_state_diff=storage_diff_end
    );
}

// Alias replacement functions.

// Same as `serialize_full_contract_state_diff`, but replaces contract addresses and storage keys
// with their aliases. Writes the result into `res`.
// Note that this function should be called only after calling `allocate_aliases`.
//
// Assumption: The dictionary `contract_state_changes` is squashed and must be sorted.
func replace_aliases_and_serialize_full_contract_state_diff{range_check_ptr, res: felt*}(
    n_contracts: felt, contract_state_changes: DictAccess*
) {
    alloc_locals;

    // Compute the full contract state diff.
    let contract_state_diff = get_full_contract_state_diff(
        n_contracts=n_contracts, contract_state_changes=contract_state_changes
    );

    // Extract the final aliases - all aliases that were accessed during the execution
    // (both existing and newly allocated - see `allocate_aliases` documentation).
    let (aliases_entry: DictAccess*) = find_element(
        array_ptr=contract_state_changes,
        elm_size=DictAccess.SIZE,
        n_elms=n_contracts,
        key=ALIAS_CONTRACT_ADDRESS,
    );

    let prev_aliases_state_entry = cast(aliases_entry.prev_value, StateEntry*);
    let new_aliases_state_entry = cast(aliases_entry.new_value, StateEntry*);
    let n_aliases = (new_aliases_state_entry.storage_ptr - prev_aliases_state_entry.storage_ptr) /
        DictAccess.SIZE;
    let aliases_ptr = cast(prev_aliases_state_entry.storage_ptr, DictAccess*);

    // Copy the number of modified contracts.
    tempvar n_modified_contracts = contract_state_diff[0];
    assert res[0] = n_modified_contracts;
    let res = &res[1];
    // Write the contract state diff with replaced aliases.
    return replace_contract_state_diff(
        aliases=Aliases(len=n_aliases, ptr=aliases_ptr),
        n_contracts=n_modified_contracts,
        contract_state_diff=&contract_state_diff[1],
    );
}

// Writes the contract state diff with replaced aliases into `res`.
func replace_contract_state_diff{range_check_ptr, res: felt*}(
    aliases: Aliases, n_contracts: felt, contract_state_diff: felt*
) {
    if (n_contracts == 0) {
        return ();
    }
    alloc_locals;

    let contract_header = cast(contract_state_diff, FullContractHeader*);
    local contract_address = contract_header.address;
    local storage_diff: FullStateUpdateEntry* = cast(
        &contract_state_diff[FullContractHeader.SIZE], FullStateUpdateEntry*
    );
    local n_storage_diffs = contract_header.n_storage_diffs;
    local storage_diff_end: FullStateUpdateEntry* = &storage_diff[n_storage_diffs];
    let skip_contract = should_skip_contract(contract_address=contract_address);
    if (skip_contract != FALSE) {
        // No aliases for this contract - copy the diff and continue.
        tempvar diff_len = cast(storage_diff_end, felt*) - contract_state_diff;
        memcpy(dst=res, src=contract_state_diff, len=diff_len);
        let res = &res[diff_len];
        return replace_contract_state_diff(
            aliases=aliases, n_contracts=n_contracts - 1, contract_state_diff=storage_diff_end
        );
    }

    // Replace the contract address.
    let address_alias = get_alias(aliases=aliases, key=contract_address);
    // Write the header.
    let replaced_contract_header = cast(res, FullContractHeader*);
    assert [replaced_contract_header] = FullContractHeader(
        address=address_alias,
        prev_nonce=contract_header.prev_nonce,
        new_nonce=contract_header.new_nonce,
        prev_class_hash=contract_header.prev_class_hash,
        new_class_hash=contract_header.new_class_hash,
        n_storage_diffs=n_storage_diffs,
    );
    let res = &res[FullContractHeader.SIZE];

    // Replace the storage diff.
    replace_storage_diff(
        aliases=aliases, storage_diff_start=storage_diff, storage_diff_end=storage_diff_end
    );
    return replace_contract_state_diff(
        aliases=aliases, n_contracts=n_contracts - 1, contract_state_diff=storage_diff_end
    );
}

// Writes the storage diff with replaced aliases into `res`.
func replace_storage_diff{range_check_ptr, res: felt*}(
    aliases: Aliases,
    storage_diff_start: FullStateUpdateEntry*,
    storage_diff_end: FullStateUpdateEntry*,
) {
    alloc_locals;
    // Copy (without replacing) entries with keys which are smaller than MIN_VALUE_FOR_ALIAS_ALLOC.
    let storage_diff_big_keys_start = get_storage_diff_big_keys_start(
        storage_diff_start=storage_diff_start, storage_diff_end=storage_diff_end
    );
    local small_keys_len = storage_diff_big_keys_start - storage_diff_start;
    memcpy(dst=res, src=storage_diff_start, len=small_keys_len);
    let res = &res[small_keys_len];
    return replace_storage_diff_big_keys(
        aliases=aliases,
        storage_diff_start=storage_diff_big_keys_start,
        storage_diff_end=storage_diff_end,
    );
}

// Same as `replace_storage_diff`, but assumes all keys are at least MIN_VALUE_FOR_ALIAS_ALLOC.
func replace_storage_diff_big_keys{range_check_ptr, res: felt*}(
    aliases: Aliases,
    storage_diff_start: FullStateUpdateEntry*,
    storage_diff_end: FullStateUpdateEntry*,
) {
    if (storage_diff_start == storage_diff_end) {
        return ();
    }

    let current_entry = storage_diff_start[0];
    let key_alias = get_alias_of_big_key(aliases=aliases, key=current_entry.key);
    let replaced_entry = cast(res, FullStateUpdateEntry*);
    assert [replaced_entry] = FullStateUpdateEntry(
        key=key_alias, prev_value=current_entry.prev_value, new_value=current_entry.new_value
    );
    let res = &res[FullStateUpdateEntry.SIZE];
    return replace_storage_diff_big_keys(
        aliases=aliases,
        storage_diff_start=&storage_diff_start[1],
        storage_diff_end=storage_diff_end,
    );
}

// Returns the alias of the given key.
func get_alias{range_check_ptr}(aliases: Aliases, key: felt) -> felt {
    if (nondet %{ ids.key < ids.MIN_VALUE_FOR_ALIAS_ALLOC %} != FALSE) {
        // The alias is the key itself.
        assert_nn_le(a=key, b=MIN_VALUE_FOR_ALIAS_ALLOC - 1);
        return key;
    }

    // Verify that key >= MIN_VALUE_FOR_ALIAS_ALLOC.
    assert_le_felt(a=MIN_VALUE_FOR_ALIAS_ALLOC, b=key);
    return get_alias_of_big_key(aliases=aliases, key=key);
}

// Returns the alias of the given key.
// Assumes the given key is at least MIN_VALUE_FOR_ALIAS_ALLOC.
func get_alias_of_big_key{range_check_ptr}(aliases: Aliases, key: felt) -> felt {
    // Sanity check.
    %{ assert ids.key >= ids.MIN_VALUE_FOR_ALIAS_ALLOC, f"Key {ids.key} is too small." %}
    let (entry: DictAccess*) = find_element(
        array_ptr=aliases.ptr, elm_size=DictAccess.SIZE, n_elms=aliases.len, key=key
    );
    return entry.new_value;
}

// Shared utilites between alias allocation and replacement.

// Same as `serialize_full_contract_state_diff`, but returns a pointer to the diff instead of
// writing it to a given argument.
func get_full_contract_state_diff{range_check_ptr}(
    n_contracts: felt, contract_state_changes: DictAccess*
) -> felt* {
    alloc_locals;
    let (local contract_state_diff_start: felt*) = alloc();
    let res = contract_state_diff_start;
    with res {
        serialize_full_contract_state_diff(
            n_contracts=n_contracts, contract_state_changes=contract_state_changes
        );
    }
    return contract_state_diff_start;
}

// Reutrns whether the contract at the given address should be skipped when assigning/replacing
// aliases.
func should_skip_contract{range_check_ptr}(contract_address: felt) -> felt {
    if (nondet %{ ids.contract_address <= ids.MAX_NON_COMPRESSED_CONTRACT_ADDRESS %} != FALSE) {
        // Don't give any aliases for contracts <= MAX_NON_COMPRESSED_CONTRACT_ADDRESS.
        assert_nn_le(a=contract_address, b=MAX_NON_COMPRESSED_CONTRACT_ADDRESS);
        return TRUE;
    }
    assert_le_felt(a=MAX_NON_COMPRESSED_CONTRACT_ADDRESS + 1, b=contract_address);
    return FALSE;
}

// Returns a pointer to the first storage diff entry whose key is >= MIN_VALUE_FOR_ALIAS_ALLOC.
func get_storage_diff_big_keys_start{range_check_ptr}(
    storage_diff_start: FullStateUpdateEntry*, storage_diff_end: FullStateUpdateEntry*
) -> FullStateUpdateEntry* {
    static_assert FullStateUpdateEntry.key == 0;
    let storage_diff_start: FullStateUpdateEntry* = search_sorted_lower(
        array_ptr=storage_diff_start,
        elm_size=FullStateUpdateEntry.SIZE,
        n_elms=(storage_diff_end - storage_diff_start) / FullStateUpdateEntry.SIZE,
        key=MIN_VALUE_FOR_ALIAS_ALLOC,
    );
    return storage_diff_start;
}
