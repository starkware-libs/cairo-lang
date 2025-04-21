from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.dict import DictAccess, dict_update
from starkware.starknet.core.os.state.commitment import StateEntry

const CONTRACT_ADDRESS_UPPER_BOUND = 2 ** 251;
const CHANGE_CONTRACT_ENTRY = CONTRACT_ADDRESS_UPPER_BOUND;
const CHANGE_CLASS_ENTRY = CHANGE_CONTRACT_ENTRY + 1;

// Represents an entry of the revert log, which can be either:
// 1. contract address separator:
//   [CHANGE_CONTRACT_ENTRY, contact_address] - indicates that the preceding entries in the log
//   refer to the given `contract_address`.
// 2. change class entry - used to revert changes of class hash (due to deploy or replace_class):
//   [CHANGE_CLASS_ENTRY, old_class_hash]
// 3. storage write entry - used to revert changes to the contract's storage:
//   [storage_key, old_value]
//
// The first entry of the revert log is [CHANGE_CONTRACT_ENTRY, CONTRACT_ADDRESS_UPPER_BOUND].
struct RevertLogEntry {
    // Either the storage key, CHANGE_CONTRACT_ENTRY or CHANGE_CLASS_ENTRY.
    selector: felt,
    // The relevant (old) value.
    value: felt,
}

func init_revert_log() -> RevertLogEntry* {
    let (revert_log: RevertLogEntry*) = alloc();
    // Add termination entry.
    assert revert_log[0] = RevertLogEntry(
        selector=CHANGE_CONTRACT_ENTRY, value=CONTRACT_ADDRESS_UPPER_BOUND
    );
    return &revert_log[1];
}

// Processes the revert log backwards and updates contract_state_changes to revert the
// changes.
func handle_revert{contract_state_changes: DictAccess*}(
    contract_address, revert_log_end: RevertLogEntry*
) {
    alloc_locals;

    local state_entry: StateEntry*;

    %{
        # Fetch a state_entry in this hint and validate it in the update that comes next.
        ids.state_entry = __dict_manager.get_dict(ids.contract_state_changes)[ids.contract_address]

        # Fetch the relevant storage.
        storage = execution_helper.storage_by_address[ids.contract_address]
    %}

    let class_hash = state_entry.class_hash;
    let storage_ptr = state_entry.storage_ptr;
    with class_hash, storage_ptr, revert_log_end {
        revert_contract_changes();
    }

    dict_update{dict_ptr=contract_state_changes}(
        key=contract_address,
        prev_value=cast(state_entry, felt),
        new_value=cast(
            new StateEntry(class_hash=class_hash, storage_ptr=storage_ptr, nonce=state_entry.nonce),
            felt,
        ),
    );

    // `revert_contract_changes()` stops where
    // `revert_log_end[0].selector == CHANGE_CONTRACT_ENTRY`.
    tempvar next_contract_address = revert_log_end[0].value;

    if (next_contract_address == CONTRACT_ADDRESS_UPPER_BOUND) {
        // Finish backward processing: this entry marks the beginning of the revert log.
        return ();
    }

    return handle_revert(contract_address=next_contract_address, revert_log_end=revert_log_end);
}

// Processes revert log entries related to a specific contract, returns to the caller once
// a CHANGE_CONTRACT_ENTRY is encountered.
func revert_contract_changes{
    class_hash: felt, storage_ptr: DictAccess*, revert_log_end: RevertLogEntry*
}() {
    let revert_log_end = &revert_log_end[-1];

    tempvar selector = revert_log_end[0].selector;
    if (selector == CHANGE_CONTRACT_ENTRY) {
        // Change contract entries are handled by the caller.
        return ();
    }

    if (selector == CHANGE_CLASS_ENTRY) {
        // Change class entry.
        let class_hash = revert_log_end[0].value;
        return revert_contract_changes();
    }

    // Storage write entry.
    let storage_key = selector;
    let value = revert_log_end[0].value;
    assert storage_ptr[0] = DictAccess(
        key=storage_key, prev_value=nondet %{ storage.read(key=ids.storage_key) %}, new_value=value
    );
    %{ storage.write(key=ids.storage_key, value=ids.value) %}
    let storage_ptr = &storage_ptr[1];
    return revert_contract_changes();
}
