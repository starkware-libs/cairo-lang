from starkware.cairo.common.bool import FALSE
from starkware.cairo.common.dict import dict_read, dict_update
from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.math import assert_nn_le
from starkware.starknet.common.new_syscalls import ExecutionInfo, ResourceBounds, TxInfo
from starkware.starknet.common.syscalls import TxInfo as DeprecatedTxInfo
from starkware.starknet.core.os.block_context import BlockContext
from starkware.starknet.core.os.builtins import BuiltinPointers
from starkware.starknet.core.os.constants import (
    ENTRY_POINT_TYPE_EXTERNAL,
    VALIDATE_ENTRY_POINT_SELECTOR,
    VALIDATED,
)
from starkware.starknet.core.os.execution.deprecated_execute_entry_point import (
    non_reverting_select_execute_entry_point_func,
)
from starkware.starknet.core.os.execution.execute_entry_point import ExecutionContext
from starkware.starknet.core.os.output import OsCarriedOutputs
from starkware.starknet.core.os.state.commitment import StateEntry

// Initializes the given DeprecatedTxInfo (dst) based on the given TxInfo.
func fill_deprecated_tx_info(tx_info: TxInfo*, dst: DeprecatedTxInfo*) {
    tempvar signature_start = tx_info.signature_start;
    assert [dst] = DeprecatedTxInfo(
        version=tx_info.version,
        account_contract_address=tx_info.account_contract_address,
        max_fee=tx_info.max_fee,
        signature_len=tx_info.signature_end - signature_start,
        signature=signature_start,
        transaction_hash=tx_info.transaction_hash,
        chain_id=tx_info.chain_id,
        nonce=tx_info.nonce,
    );
    return ();
}

// Verifies that the given (non-deprecated) `TxInfo` object is consistent with its version, in the
// sense that deprecated transactions (version < 3) have all new fields set to zero and
// non-deprecated transactions (version = 3) have old fields set to zero.
func assert_deprecated_tx_fields_consistency(tx_info: TxInfo*) {
    tempvar version = tx_info.version;
    if (version * (version - 1) * (version - 2) == 0) {
        let nullptr = cast(0, felt*);
        assert tx_info.tip = 0;
        assert tx_info.resource_bounds_start = cast(0, ResourceBounds*);
        assert tx_info.resource_bounds_end = cast(0, ResourceBounds*);
        assert tx_info.paymaster_data_start = nullptr;
        assert tx_info.paymaster_data_end = nullptr;
        assert tx_info.nonce_data_availability_mode = 0;
        assert tx_info.fee_data_availability_mode = 0;
        assert tx_info.account_deployment_data_start = nullptr;
        assert tx_info.account_deployment_data_end = nullptr;
    } else {
        with_attr error_message("Invalid transaction version: {version}.") {
            assert version = 3;
        }
        assert tx_info.max_fee = 0;
    }
    return ();
}

// Verifies that the transaction's nonce matches the contract's nonce and increments the
// latter.
func check_and_increment_nonce{contract_state_changes: DictAccess*}(tx_info: TxInfo*) -> () {
    // Do not handle nonce for version 0.
    if (tx_info.version == 0) {
        return ();
    }

    tempvar state_entry: StateEntry*;
    %{
        # Fetch a state_entry in this hint and validate it in the update that comes next.
        ids.state_entry = __dict_manager.get_dict(ids.contract_state_changes)[
            ids.tx_info.account_contract_address
        ]
    %}

    tempvar current_nonce = state_entry.nonce;
    with_attr error_message("Unexpected nonce.") {
        assert current_nonce = tx_info.nonce;
    }

    // Update contract_state_changes.
    tempvar new_state_entry = new StateEntry(
        class_hash=state_entry.class_hash,
        storage_ptr=state_entry.storage_ptr,
        nonce=current_nonce + 1,
    );
    dict_update{dict_ptr=contract_state_changes}(
        key=tx_info.account_contract_address,
        prev_value=cast(state_entry, felt),
        new_value=cast(new_state_entry, felt),
    );
    return ();
}

// Changes the class_hash according to the class that belongs to the executed contract address.
// Therefore, it shouldn't be used for execution_context that was created for library_call
// (since the class hash has nothing to do with the contract address in that case).
func update_class_hash_in_execution_context{range_check_ptr, contract_state_changes: DictAccess*}(
    execution_context: ExecutionContext*
) -> ExecutionContext* {
    let (state_entry: StateEntry*) = dict_read{dict_ptr=contract_state_changes}(
        key=execution_context.execution_info.contract_address
    );
    return new ExecutionContext(
        entry_point_type=execution_context.entry_point_type,
        class_hash=state_entry.class_hash,
        calldata_size=execution_context.calldata_size,
        calldata=execution_context.calldata,
        execution_info=execution_context.execution_info,
        deprecated_tx_info=execution_context.deprecated_tx_info,
    );
}

// Runs the account contract's "__validate__" entry point, which is responsible for
// signature verification.
//
// Arguments:
// block_context - a global context that is fixed throughout the block.
// tx_execution_context - The execution context of the underlying invoke transaction.
func run_validate{
    range_check_ptr,
    remaining_gas: felt,
    builtin_ptrs: BuiltinPointers*,
    contract_state_changes: DictAccess*,
    contract_class_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, tx_execution_context: ExecutionContext*) {
    alloc_locals;
    local tx_execution_info: ExecutionInfo* = tx_execution_context.execution_info;

    // Do not run "__validate__" for version 0.
    if (tx_execution_info.tx_info.version == 0) {
        return ();
    }

    // "__validate__" is expected to get the same calldata as "__execute__".
    local validate_execution_context: ExecutionContext* = new ExecutionContext(
        entry_point_type=ENTRY_POINT_TYPE_EXTERNAL,
        class_hash=tx_execution_context.class_hash,
        calldata_size=tx_execution_context.calldata_size,
        calldata=tx_execution_context.calldata,
        execution_info=new ExecutionInfo(
            block_info=block_context.block_info_for_validate,
            tx_info=tx_execution_info.tx_info,
            caller_address=tx_execution_info.caller_address,
            contract_address=tx_execution_info.contract_address,
            selector=VALIDATE_ENTRY_POINT_SELECTOR,
        ),
        deprecated_tx_info=tx_execution_context.deprecated_tx_info,
    );

    // The __validate__ function should not revert.
    let (retdata_size, retdata, is_deprecated) = non_reverting_select_execute_entry_point_func(
        block_context=block_context, execution_context=validate_execution_context
    );
    if (is_deprecated == 0) {
        %{
            # Fetch the result, up to 100 elements.
            result = memory.get_range(ids.retdata, min(100, ids.retdata_size))

            if result != [ids.VALIDATED]:
                print("Invalid return value from __validate__:")
                print(f"  Size: {ids.retdata_size}")
                print(f"  Result (at most 100 elements): {result}")
        %}
        assert retdata_size = 1;
        assert retdata[0] = VALIDATED;
    }

    return ();
}

// Caps the remaining gas to the given max_gas.
//
// Arguments:
// max_gas - expected to be the maximal validate or execute gas constant.
func cap_remaining_gas{range_check_ptr, remaining_gas: felt}(max_gas: felt) {
    if (nondet %{ ids.remaining_gas > ids.max_gas %} != FALSE) {
        assert_nn_le(max_gas, remaining_gas - 1);
        tempvar remaining_gas = max_gas;
    } else {
        assert_nn_le(remaining_gas, max_gas);
        tempvar remaining_gas = remaining_gas;
    }
    return ();
}
