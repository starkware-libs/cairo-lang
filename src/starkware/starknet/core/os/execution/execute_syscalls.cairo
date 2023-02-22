from starkware.cairo.common.dict import dict_read, dict_update
from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.math import assert_lt, assert_nn, assert_not_zero
from starkware.starknet.common.new_syscalls import (
    EMIT_EVENT_SELECTOR,
    GET_CALLER_ADDRESS_SELECTOR,
    STORAGE_READ_SELECTOR,
    STORAGE_WRITE_SELECTOR,
    EmitEventRequest,
    FailureReason,
    GetCallerAddressResponse,
    RequestHeader,
    ResponseHeader,
    StorageReadRequest,
    StorageReadResponse,
    StorageWriteRequest,
)
from starkware.starknet.core.os.block_context import BlockContext
from starkware.starknet.core.os.builtins import BuiltinPointers
from starkware.starknet.core.os.constants import (
    EMIT_EVENT_GAS_COST,
    ERROR_OUT_OF_GAS,
    GET_CALLER_ADDRESS_GAS_COST,
    STORAGE_READ_GAS_COST,
    STORAGE_WRITE_GAS_COST,
    SYSCALL_BASE_GAS_COST,
)
from starkware.starknet.core.os.execution.execute_entry_point import ExecutionContext
from starkware.starknet.core.os.output import OsCarriedOutputs
from starkware.starknet.core.os.state import StateEntry

// Executes the system calls in syscall_ptr.
// The signature of the function 'call_execute_syscalls' must match this function's signature.
//
// Arguments:
// block_context - a read-only context used for transaction execution.
// execution_context - The execution context in which the system calls need to be executed.
// syscall_ptr_end - a pointer to the end of the syscall segment.
func execute_syscalls{
    range_check_ptr,
    syscall_ptr: felt*,
    builtin_ptrs: BuiltinPointers*,
    contract_state_changes: DictAccess*,
    contract_class_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, execution_context: ExecutionContext*, syscall_ptr_end: felt*) {
    if (syscall_ptr == syscall_ptr_end) {
        return ();
    }

    tempvar selector = [syscall_ptr];
    if (selector == STORAGE_READ_SELECTOR) {
        execute_storage_read(contract_address=execution_context.contract_address);
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_ptr_end=syscall_ptr_end,
        );
    }

    if (selector == STORAGE_WRITE_SELECTOR) {
        execute_storage_write(contract_address=execution_context.contract_address);
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_ptr_end=syscall_ptr_end,
        );
    }

    if (selector == EMIT_EVENT_SELECTOR) {
        reduce_syscall_gas(gas_cost=EMIT_EVENT_GAS_COST, request_size=EmitEventRequest.SIZE);
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_ptr_end=syscall_ptr_end,
        );
    }

    assert selector = GET_CALLER_ADDRESS_SELECTOR;
    execute_get_caller_address(caller_address=execution_context.caller_address);
    return execute_syscalls(
        block_context=block_context,
        execution_context=execution_context,
        syscall_ptr_end=syscall_ptr_end,
    );
}

// Reads a value from the current contract's storage.
func execute_storage_read{range_check_ptr, syscall_ptr: felt*, contract_state_changes: DictAccess*}(
    contract_address
) {
    alloc_locals;
    let request = cast(syscall_ptr + RequestHeader.SIZE, StorageReadRequest*);

    // Reduce gas.
    let success = reduce_syscall_gas(
        gas_cost=STORAGE_READ_GAS_COST, request_size=StorageReadRequest.SIZE
    );
    if (success == 0) {
        // Not enough gas to execute the syscall.
        return ();
    }

    let response = cast(syscall_ptr, StorageReadResponse*);
    // Advance syscall pointer to the next syscall.
    let syscall_ptr = syscall_ptr + StorageReadResponse.SIZE;

    local state_entry: StateEntry*;
    local new_state_entry: StateEntry*;
    %{
        # Fetch a state_entry in this hint and validate it in the update that comes next.
        ids.state_entry = __dict_manager.get_dict(ids.contract_state_changes)[ids.contract_address]
        ids.new_state_entry = segments.add()
    %}

    // Update the contract's storage.
    static_assert StorageReadRequest.SIZE == 2;
    assert request.reserved = 0;
    tempvar value = response.value;
    tempvar storage_ptr = state_entry.storage_ptr;
    assert [storage_ptr] = DictAccess(key=request.key, prev_value=value, new_value=value);
    let storage_ptr = storage_ptr + DictAccess.SIZE;

    // Update the state.
    assert [new_state_entry] = StateEntry(
        class_hash=state_entry.class_hash, storage_ptr=storage_ptr, nonce=state_entry.nonce
    );
    dict_update{dict_ptr=contract_state_changes}(
        key=contract_address,
        prev_value=cast(state_entry, felt),
        new_value=cast(new_state_entry, felt),
    );

    return ();
}

// Writes a value to the current contract's storage.
func execute_storage_write{
    range_check_ptr, syscall_ptr: felt*, contract_state_changes: DictAccess*
}(contract_address) {
    alloc_locals;
    let request = cast(syscall_ptr + RequestHeader.SIZE, StorageWriteRequest*);

    // Reduce gas.
    let success = reduce_syscall_gas(
        gas_cost=STORAGE_WRITE_GAS_COST, request_size=StorageWriteRequest.SIZE
    );
    if (success == 0) {
        // Not enough gas to execute the syscall.
        return ();
    }

    local prev_value: felt;
    local state_entry: StateEntry*;
    local new_state_entry: StateEntry*;
    %{
        storage = execution_helper.storage_by_address[ids.contract_address]
        ids.prev_value = storage.read(key=ids.request.key)
        storage.write(key=ids.request.key, value=ids.request.value)

        # Fetch a state_entry in this hint and validate it in the update that comes next.
        ids.state_entry = __dict_manager.get_dict(ids.contract_state_changes)[ids.contract_address]
        ids.new_state_entry = segments.add()
    %}

    // Update the contract's storage.
    static_assert StorageWriteRequest.SIZE == 3;
    assert request.reserved = 0;
    tempvar storage_ptr = state_entry.storage_ptr;
    assert [storage_ptr] = DictAccess(
        key=request.key, prev_value=prev_value, new_value=request.value
    );
    let storage_ptr = storage_ptr + DictAccess.SIZE;

    // Update the state.
    assert [new_state_entry] = StateEntry(
        class_hash=state_entry.class_hash, storage_ptr=storage_ptr, nonce=state_entry.nonce
    );
    dict_update{dict_ptr=contract_state_changes}(
        key=contract_address,
        prev_value=cast(state_entry, felt),
        new_value=cast(new_state_entry, felt),
    );

    return ();
}

// Gets the address of the caller contract.
func execute_get_caller_address{
    range_check_ptr, syscall_ptr: felt*, contract_state_changes: DictAccess*
}(caller_address) {
    // Reduce gas.
    let success = reduce_syscall_gas(gas_cost=GET_CALLER_ADDRESS_GAS_COST, request_size=0);
    if (success == 0) {
        // Not enough gas to execute the syscall.
        return ();
    }

    assert [cast(syscall_ptr, GetCallerAddressResponse*)] = GetCallerAddressResponse(
        caller_address=caller_address
    );
    // Advance syscall pointer to the next syscall.
    let syscall_ptr = syscall_ptr + GetCallerAddressResponse.SIZE;

    return ();
}

// Reduces the required amount of gas for the current syscall and writes the response header.
// In case of out-of-gas failure, writes the FailureReason object to syscall_ptr.
// Returns 1 if the gas reduction succeeded and 0 otherwise.
func reduce_syscall_gas{range_check_ptr, syscall_ptr: felt*}(
    gas_cost: felt, request_size: felt
) -> felt {
    let request_header = cast(syscall_ptr, RequestHeader*);
    // Advance syscall pointer to the response header.
    tempvar syscall_ptr = syscall_ptr + RequestHeader.SIZE + request_size;

    tempvar response_header = cast(syscall_ptr, ResponseHeader*);
    // Advance syscall pointer to the response body.
    let syscall_ptr = syscall_ptr + ResponseHeader.SIZE;

    // Refund the pre-charged base gas.
    let required_gas = gas_cost - SYSCALL_BASE_GAS_COST;
    if (response_header.failure_flag != 0) {
        // Verify that there was not enough gas to invoke the syscall.
        tempvar initial_gas = request_header.gas;
        assert_lt(initial_gas, required_gas);
        assert [response_header] = ResponseHeader(gas=initial_gas, failure_flag=1);

        // Write the failure reason.
        let failure_reason: FailureReason* = cast(syscall_ptr, FailureReason*);
        // Advance syscall pointer to the next syscall.
        let syscall_ptr = syscall_ptr + FailureReason.SIZE;

        tempvar start = failure_reason.start;
        assert start[0] = ERROR_OUT_OF_GAS;
        assert failure_reason.end = start + 1;

        return 0;
    }

    // Handle valid syscall.
    tempvar remaining_gas = request_header.gas - required_gas;
    assert [response_header] = ResponseHeader(gas=remaining_gas, failure_flag=0);
    // Check that the remaining gas is non-negative.
    assert_nn(remaining_gas);

    return 1;
}
