from starkware.cairo.common.dict import dict_read, dict_update
from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.math import assert_lt, assert_nn, assert_not_zero
from starkware.cairo.common.memcpy import memcpy
from starkware.cairo.common.segments import relocate_segment
from starkware.starknet.common.new_syscalls import (
    CALL_CONTRACT_SELECTOR,
    DEPLOY_SELECTOR,
    EMIT_EVENT_SELECTOR,
    GET_EXECUTION_INFO_SELECTOR,
    LIBRARY_CALL_SELECTOR,
    REPLACE_CLASS_SELECTOR,
    SEND_MESSAGE_TO_L1_SELECTOR,
    STORAGE_READ_SELECTOR,
    STORAGE_WRITE_SELECTOR,
    CallContractRequest,
    CallContractResponse,
    DeployRequest,
    DeployResponse,
    EmitEventRequest,
    ExecutionInfo,
    FailureReason,
    GetExecutionInfoResponse,
    LibraryCallRequest,
    ReplaceClassRequest,
    RequestHeader,
    ResponseHeader,
    SendMessageToL1Request,
    StorageReadRequest,
    StorageReadResponse,
    StorageWriteRequest,
)
from starkware.starknet.core.os.block_context import BlockContext
from starkware.starknet.core.os.builtins import BuiltinPointers
from starkware.starknet.core.os.constants import (
    CALL_CONTRACT_GAS_COST,
    CONSTRUCTOR_ENTRY_POINT_SELECTOR,
    DEPLOY_GAS_COST,
    EMIT_EVENT_GAS_COST,
    ENTRY_POINT_TYPE_CONSTRUCTOR,
    ENTRY_POINT_TYPE_EXTERNAL,
    ERROR_OUT_OF_GAS,
    GET_EXECUTION_INFO_GAS_COST,
    LIBRARY_CALL_GAS_COST,
    REPLACE_CLASS_GAS_COST,
    SEND_MESSAGE_TO_L1_GAS_COST,
    STORAGE_READ_GAS_COST,
    STORAGE_WRITE_GAS_COST,
    SYSCALL_BASE_GAS_COST,
)
from starkware.starknet.core.os.contract_address.contract_address import get_contract_address
from starkware.starknet.core.os.execution.deprecated_execute_entry_point import (
    select_execute_entry_point_func,
)
from starkware.starknet.core.os.execution.deprecated_execute_syscalls import deploy_contract
from starkware.starknet.core.os.execution.execute_entry_point import ExecutionContext
from starkware.starknet.core.os.output import (
    MessageToL1Header,
    OsCarriedOutputs,
    os_carried_outputs_new,
)
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
        execute_storage_read(contract_address=execution_context.execution_info.contract_address);
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_ptr_end=syscall_ptr_end,
        );
    }

    if (selector == STORAGE_WRITE_SELECTOR) {
        execute_storage_write(contract_address=execution_context.execution_info.contract_address);
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_ptr_end=syscall_ptr_end,
        );
    }

    if (selector == GET_EXECUTION_INFO_SELECTOR) {
        execute_get_execution_info(execution_info=execution_context.execution_info);
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_ptr_end=syscall_ptr_end,
        );
    }

    if (selector == CALL_CONTRACT_SELECTOR) {
        execute_call_contract(
            block_context=block_context, caller_execution_context=execution_context
        );
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_ptr_end=syscall_ptr_end,
        );
    }

    if (selector == LIBRARY_CALL_SELECTOR) {
        execute_library_call(
            block_context=block_context, caller_execution_context=execution_context
        );
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_ptr_end=syscall_ptr_end,
        );
    }

    if (selector == EMIT_EVENT_SELECTOR) {
        // Skip as long as the block hash is not calculated by the OS.
        reduce_syscall_gas_and_write_response_header(
            total_gas_cost=EMIT_EVENT_GAS_COST, request_struct_size=EmitEventRequest.SIZE
        );
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_ptr_end=syscall_ptr_end,
        );
    }

    if (selector == DEPLOY_SELECTOR) {
        execute_deploy(block_context=block_context, caller_execution_context=execution_context);
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_ptr_end=syscall_ptr_end,
        );
    }

    if (selector == REPLACE_CLASS_SELECTOR) {
        execute_replace_class(contract_address=execution_context.execution_info.contract_address);
        return execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_ptr_end=syscall_ptr_end,
        );
    }

    assert selector = SEND_MESSAGE_TO_L1_SELECTOR;

    execute_send_message_to_l1(contract_address=execution_context.execution_info.contract_address);
    return execute_syscalls(
        block_context=block_context,
        execution_context=execution_context,
        syscall_ptr_end=syscall_ptr_end,
    );
}

// Executes a syscall that calls another contract.
func execute_call_contract{
    range_check_ptr,
    syscall_ptr: felt*,
    builtin_ptrs: BuiltinPointers*,
    contract_state_changes: DictAccess*,
    contract_class_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, caller_execution_context: ExecutionContext*) {
    let request = cast(syscall_ptr + RequestHeader.SIZE, CallContractRequest*);
    let (success, remaining_gas) = reduce_syscall_base_gas(
        specific_base_gas_cost=CALL_CONTRACT_GAS_COST, request_struct_size=CallContractRequest.SIZE
    );
    if (success == 0) {
        // Not enough gas to execute the syscall.
        return ();
    }

    tempvar contract_address = request.contract_address;
    let (state_entry: StateEntry*) = dict_read{dict_ptr=contract_state_changes}(
        key=contract_address
    );

    // Prepare execution context.
    tempvar calldata_start = request.calldata_start;
    tempvar caller_execution_info = caller_execution_context.execution_info;
    tempvar execution_context: ExecutionContext* = new ExecutionContext(
        entry_point_type=ENTRY_POINT_TYPE_EXTERNAL,
        class_hash=state_entry.class_hash,
        calldata_size=request.calldata_end - calldata_start,
        calldata=calldata_start,
        execution_info=new ExecutionInfo(
            block_info=caller_execution_info.block_info,
            tx_info=caller_execution_info.tx_info,
            caller_address=caller_execution_info.contract_address,
            contract_address=contract_address,
            selector=request.selector,
        ),
        deprecated_tx_info=caller_execution_context.deprecated_tx_info,
    );

    return contract_call_helper(
        remaining_gas=remaining_gas,
        block_context=block_context,
        execution_context=execution_context,
    );
}

// Implements the library_call syscall.
func execute_library_call{
    range_check_ptr,
    syscall_ptr: felt*,
    builtin_ptrs: BuiltinPointers*,
    contract_state_changes: DictAccess*,
    contract_class_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, caller_execution_context: ExecutionContext*) {
    let request = cast(syscall_ptr + RequestHeader.SIZE, LibraryCallRequest*);
    let (success, remaining_gas) = reduce_syscall_base_gas(
        specific_base_gas_cost=LIBRARY_CALL_GAS_COST, request_struct_size=LibraryCallRequest.SIZE
    );
    if (success == 0) {
        // Not enough gas to execute the syscall.
        return ();
    }

    // Prepare execution context.
    tempvar calldata_start = request.calldata_start;
    tempvar caller_execution_info = caller_execution_context.execution_info;
    tempvar execution_context: ExecutionContext* = new ExecutionContext(
        entry_point_type=ENTRY_POINT_TYPE_EXTERNAL,
        class_hash=request.class_hash,
        calldata_size=request.calldata_end - calldata_start,
        calldata=calldata_start,
        execution_info=new ExecutionInfo(
            block_info=caller_execution_info.block_info,
            tx_info=caller_execution_info.tx_info,
            caller_address=caller_execution_info.caller_address,
            contract_address=caller_execution_info.contract_address,
            selector=request.selector,
        ),
        deprecated_tx_info=caller_execution_context.deprecated_tx_info,
    );

    return contract_call_helper(
        remaining_gas=remaining_gas,
        block_context=block_context,
        execution_context=execution_context,
    );
}

// Executes the entry point and writes the corresponding response to the syscall_ptr.
// Assumes that syscall_ptr points at the response header.
func contract_call_helper{
    range_check_ptr,
    syscall_ptr: felt*,
    builtin_ptrs: BuiltinPointers*,
    contract_state_changes: DictAccess*,
    contract_class_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(remaining_gas: felt, block_context: BlockContext*, execution_context: ExecutionContext*) {
    with remaining_gas {
        let (retdata_size, retdata) = select_execute_entry_point_func(
            block_context=block_context, execution_context=execution_context
        );
    }

    let response_header = cast(syscall_ptr, ResponseHeader*);
    // Advance syscall pointer to the response body.
    let syscall_ptr = syscall_ptr + ResponseHeader.SIZE;

    // Write the response header.
    assert [response_header] = ResponseHeader(gas=remaining_gas, failure_flag=0);

    let response = cast(syscall_ptr, CallContractResponse*);
    // Advance syscall pointer to the next syscall.
    let syscall_ptr = syscall_ptr + CallContractResponse.SIZE;

    %{
        # Check that the actual return value matches the expected one.
        expected = memory.get_range(
            addr=ids.response.retdata_start,
            size=ids.response.retdata_end - ids.response.retdata_start,
        )
        actual = memory.get_range(addr=ids.retdata, size=ids.retdata_size)

        assert expected == actual, f'Return value mismatch; expected={expected}, actual={actual}.'
    %}

    // Write the response.
    relocate_segment(src_ptr=response.retdata_start, dest_ptr=retdata);
    assert [response] = CallContractResponse(
        retdata_start=retdata, retdata_end=retdata + retdata_size
    );

    return ();
}

// Deploys a contract and invokes its constructor.
func execute_deploy{
    range_check_ptr,
    syscall_ptr: felt*,
    builtin_ptrs: BuiltinPointers*,
    contract_state_changes: DictAccess*,
    contract_class_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, caller_execution_context: ExecutionContext*) {
    alloc_locals;
    let request = cast(syscall_ptr + RequestHeader.SIZE, DeployRequest*);
    let (success, remaining_gas) = reduce_syscall_base_gas(
        specific_base_gas_cost=DEPLOY_GAS_COST, request_struct_size=DeployRequest.SIZE
    );
    if (success == 0) {
        // Not enough gas to execute the syscall.
        return ();
    }

    local caller_execution_info: ExecutionInfo* = caller_execution_context.execution_info;
    local caller_address = caller_execution_info.contract_address;

    // Verify deploy_from_zero is either 0 (FALSE) or 1 (TRUE).
    tempvar deploy_from_zero = request.deploy_from_zero;
    assert deploy_from_zero * (deploy_from_zero - 1) = 0;
    // Set deployer_address to 0 if request.deploy_from_zero is TRUE.
    let deployer_address = (1 - deploy_from_zero) * caller_address;

    tempvar constructor_calldata_start = request.constructor_calldata_start;
    tempvar constructor_calldata_size = request.constructor_calldata_end -
        constructor_calldata_start;
    let hash_ptr = builtin_ptrs.pedersen;
    with hash_ptr {
        let (contract_address) = get_contract_address(
            salt=request.contract_address_salt,
            class_hash=request.class_hash,
            constructor_calldata_size=constructor_calldata_size,
            constructor_calldata=constructor_calldata_start,
            deployer_address=deployer_address,
        );
    }
    tempvar builtin_ptrs = new BuiltinPointers(
        pedersen=hash_ptr,
        range_check=builtin_ptrs.range_check,
        ecdsa=builtin_ptrs.ecdsa,
        bitwise=builtin_ptrs.bitwise,
        ec_op=builtin_ptrs.ec_op,
        poseidon=builtin_ptrs.poseidon,
        segment_arena=builtin_ptrs.segment_arena,
    );

    tempvar constructor_execution_context = new ExecutionContext(
        entry_point_type=ENTRY_POINT_TYPE_CONSTRUCTOR,
        class_hash=request.class_hash,
        calldata_size=constructor_calldata_size,
        calldata=constructor_calldata_start,
        execution_info=new ExecutionInfo(
            block_info=caller_execution_info.block_info,
            tx_info=caller_execution_info.tx_info,
            caller_address=caller_address,
            contract_address=contract_address,
            selector=CONSTRUCTOR_ENTRY_POINT_SELECTOR,
        ),
        deprecated_tx_info=caller_execution_context.deprecated_tx_info,
    );

    with remaining_gas {
        let (retdata_size, retdata) = deploy_contract(
            block_context=block_context, constructor_execution_context=constructor_execution_context
        );
    }

    let response_header = cast(syscall_ptr, ResponseHeader*);
    // Advance syscall pointer to the response body.
    let syscall_ptr = syscall_ptr + ResponseHeader.SIZE;

    // Write the response header.
    assert [response_header] = ResponseHeader(gas=remaining_gas, failure_flag=0);

    let response = cast(syscall_ptr, DeployResponse*);
    // Advance syscall pointer to the next syscall.
    let syscall_ptr = syscall_ptr + DeployResponse.SIZE;

    %{
        # Check that the actual return value matches the expected one.
        expected = memory.get_range(
            addr=ids.response.constructor_retdata_start,
            size=ids.response.constructor_retdata_end - ids.response.constructor_retdata_start,
        )
        actual = memory.get_range(addr=ids.retdata, size=ids.retdata_size)
        assert expected == actual, f'Return value mismatch; expected={expected}, actual={actual}.'
    %}

    // Write the response.
    relocate_segment(src_ptr=response.constructor_retdata_start, dest_ptr=retdata);
    assert [response] = DeployResponse(
        contract_address=contract_address,
        constructor_retdata_start=retdata,
        constructor_retdata_end=retdata + retdata_size,
    );

    return ();
}

// Reads a value from the current contract's storage.
func execute_storage_read{range_check_ptr, syscall_ptr: felt*, contract_state_changes: DictAccess*}(
    contract_address: felt
) {
    alloc_locals;
    let request = cast(syscall_ptr + RequestHeader.SIZE, StorageReadRequest*);

    // Reduce gas.
    let success = reduce_syscall_gas_and_write_response_header(
        total_gas_cost=STORAGE_READ_GAS_COST, request_struct_size=StorageReadRequest.SIZE
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
}(contract_address: felt) {
    alloc_locals;
    let request = cast(syscall_ptr + RequestHeader.SIZE, StorageWriteRequest*);

    // Reduce gas.
    let success = reduce_syscall_gas_and_write_response_header(
        total_gas_cost=STORAGE_WRITE_GAS_COST, request_struct_size=StorageWriteRequest.SIZE
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

// Gets the execution info.
func execute_get_execution_info{range_check_ptr, syscall_ptr: felt*}(
    execution_info: ExecutionInfo*
) {
    // Reduce gas.
    let success = reduce_syscall_gas_and_write_response_header(
        total_gas_cost=GET_EXECUTION_INFO_GAS_COST, request_struct_size=0
    );
    if (success == 0) {
        // Not enough gas to execute the syscall.
        return ();
    }

    assert [cast(syscall_ptr, GetExecutionInfoResponse*)] = GetExecutionInfoResponse(
        execution_info=execution_info
    );
    // Advance syscall pointer to the next syscall.
    let syscall_ptr = syscall_ptr + GetExecutionInfoResponse.SIZE;

    return ();
}

// Replaces the class.
func execute_replace_class{
    range_check_ptr, syscall_ptr: felt*, contract_state_changes: DictAccess*
}(contract_address: felt) {
    alloc_locals;
    let request = cast(syscall_ptr + RequestHeader.SIZE, ReplaceClassRequest*);

    // Reduce gas.
    let success = reduce_syscall_gas_and_write_response_header(
        total_gas_cost=REPLACE_CLASS_GAS_COST, request_struct_size=ReplaceClassRequest.SIZE
    );
    if (success == 0) {
        // Not enough gas to execute the syscall.
        return ();
    }

    let class_hash = request.class_hash;

    local state_entry: StateEntry*;
    %{
        # Fetch a state_entry in this hint and validate it in the update at the end
        # of this function.
        ids.state_entry = __dict_manager.get_dict(ids.contract_state_changes)[ids.contract_address]
    %}

    tempvar new_state_entry = new StateEntry(
        class_hash=class_hash, storage_ptr=state_entry.storage_ptr, nonce=state_entry.nonce
    );

    dict_update{dict_ptr=contract_state_changes}(
        key=contract_address,
        prev_value=cast(state_entry, felt),
        new_value=cast(new_state_entry, felt),
    );

    return ();
}

// Sends a message to L1.
func execute_send_message_to_l1{range_check_ptr, syscall_ptr: felt*, outputs: OsCarriedOutputs*}(
    contract_address: felt
) {
    alloc_locals;
    let request = cast(syscall_ptr + RequestHeader.SIZE, SendMessageToL1Request*);
    let success = reduce_syscall_gas_and_write_response_header(
        total_gas_cost=SEND_MESSAGE_TO_L1_GAS_COST, request_struct_size=SendMessageToL1Request.SIZE
    );
    if (success == 0) {
        // Not enough gas to execute the syscall.
        return ();
    }

    tempvar payload_start = request.payload_start;
    tempvar payload_size = request.payload_end - payload_start;

    assert [outputs.messages_to_l1] = MessageToL1Header(
        from_address=contract_address, to_address=request.to_address, payload_size=payload_size
    );
    memcpy(
        dst=outputs.messages_to_l1 + MessageToL1Header.SIZE, src=payload_start, len=payload_size
    );
    let (outputs) = os_carried_outputs_new(
        messages_to_l1=outputs.messages_to_l1 + MessageToL1Header.SIZE + payload_size,
        messages_to_l2=outputs.messages_to_l2,
    );

    return ();
}

// Reduces the total amount of gas required for the current syscall and writes the response header.
// In case of out-of-gas failure, writes the FailureReason object to syscall_ptr.
// Returns 1 if the gas reduction succeeded and 0 otherwise.
func reduce_syscall_gas_and_write_response_header{range_check_ptr, syscall_ptr: felt*}(
    total_gas_cost: felt, request_struct_size: felt
) -> felt {
    let (success, remaining_gas) = reduce_syscall_base_gas(
        specific_base_gas_cost=total_gas_cost, request_struct_size=request_struct_size
    );
    if (success != 0) {
        // Reduction has succeded; write the response header.
        let response_header = cast(syscall_ptr, ResponseHeader*);
        // Advance syscall pointer to the response body.
        let syscall_ptr = syscall_ptr + ResponseHeader.SIZE;
        assert [response_header] = ResponseHeader(gas=remaining_gas, failure_flag=0);

        return 1;
    }

    // Reduction has failed; in that case, 'reduce_syscall_base_gas' already wrote the response
    // objects and advanced the syscall pointer.
    return 0;
}

// Reduces the base amount of gas for the current syscall.
// In case of out-of-gas failure, writes the corresponding ResponseHeader and FailureReason
// objects to syscall_ptr.
// Returns 1 if the gas reduction succeeded and 0 otherwise, along with the remaining gas.
func reduce_syscall_base_gas{range_check_ptr, syscall_ptr: felt*}(
    specific_base_gas_cost: felt, request_struct_size: felt
) -> (success: felt, remaining_gas: felt) {
    let request_header = cast(syscall_ptr, RequestHeader*);
    // Advance syscall pointer to the response header.
    tempvar syscall_ptr = syscall_ptr + RequestHeader.SIZE + request_struct_size;

    // Refund the pre-charged base gas.
    let required_gas = specific_base_gas_cost - SYSCALL_BASE_GAS_COST;
    tempvar initial_gas = request_header.gas;
    if (nondet %{ ids.initial_gas >= ids.required_gas %} != 0) {
        tempvar remaining_gas = initial_gas - required_gas;
        assert_nn(remaining_gas);
        return (success=1, remaining_gas=remaining_gas);
    }

    // Handle out-of-gas.
    assert_lt(initial_gas, required_gas);
    tempvar response_header = cast(syscall_ptr, ResponseHeader*);
    // Advance syscall pointer to the response body.
    let syscall_ptr = syscall_ptr + ResponseHeader.SIZE;

    // Write the response header.
    assert [response_header] = ResponseHeader(gas=initial_gas, failure_flag=1);

    let failure_reason: FailureReason* = cast(syscall_ptr, FailureReason*);
    // Advance syscall pointer to the next syscall.
    let syscall_ptr = syscall_ptr + FailureReason.SIZE;

    // Write the failure reason.
    tempvar start = failure_reason.start;
    assert start[0] = ERROR_OUT_OF_GAS;
    assert failure_reason.end = start + 1;

    return (success=0, remaining_gas=initial_gas);
}
