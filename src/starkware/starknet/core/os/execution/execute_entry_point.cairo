from starkware.cairo.builtin_selection.select_builtins import select_builtins
from starkware.cairo.builtin_selection.select_input_builtins import select_input_builtins
from starkware.cairo.builtin_selection.validate_builtins import validate_builtins
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.dict import dict_read
from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.find_element import find_element, search_sorted
from starkware.cairo.common.math import assert_not_zero
from starkware.cairo.common.registers import get_ap
from starkware.starknet.common.syscalls import TxInfo
from starkware.starknet.core.os.block_context import BlockContext
from starkware.starknet.core.os.builtins import BuiltinEncodings, BuiltinParams, BuiltinPointers
from starkware.starknet.core.os.constants import (
    DEFAULT_ENTRY_POINT_SELECTOR,
    ENTRY_POINT_GAS_COST,
    ENTRY_POINT_TYPE_CONSTRUCTOR,
    ENTRY_POINT_TYPE_EXTERNAL,
    ENTRY_POINT_TYPE_L1_HANDLER,
    NOP_ENTRY_POINT_OFFSET,
)
from starkware.starknet.core.os.contract_class.compiled_class import (
    CompiledClass,
    CompiledClassEntryPoint,
    CompiledClassFact,
)
from starkware.starknet.core.os.output import OsCarriedOutputs

// Represents the execution context during the execution of contract code.
struct ExecutionContext {
    entry_point_type: felt,
    caller_address: felt,
    // The execution is done in the context of the contract at 'contract_address'.
    // This address controls the storage being used, messages sent to L1, calling contracts, etc.
    contract_address: felt,
    // The hash of the contract class to execute.
    class_hash: felt,
    selector: felt,
    calldata_size: felt,
    calldata: felt*,
    // Information about the transaction that triggered the execution.
    original_tx_info: TxInfo*,
}

// Represents the arguments pushed to the stack before calling an entry point.
struct EntryPointCallArguments {
    gas_builtin: felt,
    syscall_ptr: felt*,
    calldata_start: felt*,
    calldata_end: felt*,
}

// Represents the values returned by a call to an entry point.
struct EntryPointReturnValues {
    gas_builtin: felt,
    syscall_ptr: felt*,
    // The failure_flag is 0 if the execution succeeded and 1 if it failed.
    failure_flag: felt,
    retdata_start: felt*,
    retdata_end: felt*,
}

// Performs a Cairo jump to the function 'execute_syscalls'.
// This function's signature must match the signature of 'execute_syscalls'.
func call_execute_syscalls{
    range_check_ptr,
    syscall_ptr: felt*,
    builtin_ptrs: BuiltinPointers*,
    contract_state_changes: DictAccess*,
    contract_class_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, execution_context: ExecutionContext*, syscall_ptr_end: felt*) {
    jmp abs block_context.execute_syscalls_ptr;
}

// Returns the CompiledClassEntryPoint, based on 'compiled_class' and 'execution_context'.
func get_entry_point{range_check_ptr}(
    compiled_class: CompiledClass*, execution_context: ExecutionContext*
) -> (entry_point: CompiledClassEntryPoint*) {
    alloc_locals;
    // Get the entry points corresponding to the transaction's type.
    local entry_points: CompiledClassEntryPoint*;
    local n_entry_points: felt;

    tempvar entry_point_type = execution_context.entry_point_type;
    if (entry_point_type == ENTRY_POINT_TYPE_L1_HANDLER) {
        entry_points = compiled_class.l1_handlers;
        n_entry_points = compiled_class.n_l1_handlers;
    } else {
        if (entry_point_type == ENTRY_POINT_TYPE_EXTERNAL) {
            entry_points = compiled_class.external_functions;
            n_entry_points = compiled_class.n_external_functions;
        } else {
            assert entry_point_type = ENTRY_POINT_TYPE_CONSTRUCTOR;
            entry_points = compiled_class.constructors;
            n_entry_points = compiled_class.n_constructors;

            if (n_entry_points == 0) {
                return (entry_point=cast(0, CompiledClassEntryPoint*));
            }
        }
    }

    // The key must be at offset 0.
    static_assert CompiledClassEntryPoint.selector == 0;
    let (entry_point_desc: CompiledClassEntryPoint*, success) = search_sorted(
        array_ptr=cast(entry_points, felt*),
        elm_size=CompiledClassEntryPoint.SIZE,
        n_elms=n_entry_points,
        key=execution_context.selector,
    );
    if (success != 0) {
        return (entry_point=entry_point_desc);
    }

    // If the selector was not found, verify that the first entry point is the default entry point,
    // and call it.
    assert_not_zero(n_entry_points);
    assert entry_points[0].selector = DEFAULT_ENTRY_POINT_SELECTOR;
    return (entry_point=&entry_points[0]);
}

// Executes an entry point in a contract.
// The contract entry point is selected based on execution_context.entry_point_type
// and execution_context.selector.
//
// Arguments:
// block_context - a global context that is fixed throughout the block.
// execution_context - The context for the current execution.
func execute_entry_point{
    range_check_ptr,
    remaining_gas: felt,
    builtin_ptrs: BuiltinPointers*,
    contract_state_changes: DictAccess*,
    contract_class_changes: DictAccess*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, execution_context: ExecutionContext*) -> (
    retdata_size: felt, retdata: felt*
) {
    alloc_locals;
    %{ execution_helper.enter_call() %}

    let (compiled_class_hash: felt) = dict_read{dict_ptr=contract_class_changes}(
        key=execution_context.class_hash
    );
    // The key must be at offset 0.
    static_assert CompiledClassFact.hash == 0;
    let (compiled_class_fact: CompiledClassFact*) = find_element(
        array_ptr=block_context.compiled_class_facts,
        elm_size=CompiledClassFact.SIZE,
        n_elms=block_context.n_compiled_class_facts,
        key=compiled_class_hash,
    );
    local compiled_class: CompiledClass* = compiled_class_fact.compiled_class;
    let (compiled_class_entry_point: CompiledClassEntryPoint*) = get_entry_point(
        compiled_class=compiled_class, execution_context=execution_context
    );

    if (compiled_class_entry_point == cast(0, CompiledClassEntryPoint*)) {
        // Assert that there is no call data in the case of NOP entry point.
        assert execution_context.calldata_size = 0;
        %{ execution_helper.exit_call() %}
        return (retdata_size=0, retdata=cast(0, felt*));
    }

    let entry_point_offset = compiled_class_entry_point.offset;
    local range_check_ptr = range_check_ptr;
    local contract_entry_point: felt* = compiled_class.bytecode_ptr + entry_point_offset;

    local os_context: felt*;
    local syscall_ptr: felt*;

    %{
        ids.os_context = segments.add()
        ids.syscall_ptr = segments.add()

        syscall_handler.set_syscall_ptr(syscall_ptr=ids.syscall_ptr)
    %}
    assert [os_context] = cast(syscall_ptr, felt);

    let n_builtins = BuiltinEncodings.SIZE;
    local builtin_params: BuiltinParams* = block_context.builtin_params;
    local calldata_start: felt* = execution_context.calldata;
    local calldata_end: felt* = calldata_start + execution_context.calldata_size;
    local entry_point_n_builtins = compiled_class_entry_point.n_builtins;
    local entry_point_builtin_list: felt* = compiled_class_entry_point.builtin_list;
    // Call select_input_builtins to push the relevant builtin pointer arguments on the stack.
    select_input_builtins(
        all_encodings=builtin_params.builtin_encodings,
        all_ptrs=builtin_ptrs,
        n_all_builtins=n_builtins,
        selected_encodings=entry_point_builtin_list,
        n_selected_builtins=entry_point_n_builtins,
    );

    // Use tempvar to pass the rest of the arguments to contract_entry_point().
    let current_ap = ap;
    tempvar args = EntryPointCallArguments(
        gas_builtin=remaining_gas,
        syscall_ptr=syscall_ptr,
        calldata_start=calldata_start,
        calldata_end=calldata_end,
    );
    static_assert ap == current_ap + EntryPointCallArguments.SIZE;

    %{ vm_enter_scope({'syscall_handler': syscall_handler}) %}
    call abs contract_entry_point;
    %{ vm_exit_scope() %}
    // Retrieve returned_builtin_ptrs_subset.
    // Note that returned_builtin_ptrs_subset cannot be set in a hint because doing so will allow a
    // malicious prover to lie about the storage changes of a valid contract.
    let (ap_val) = get_ap();
    local return_values_ptr: felt* = ap_val - EntryPointReturnValues.SIZE;
    local returned_builtin_ptrs_subset: felt* = return_values_ptr - entry_point_n_builtins;
    local entry_point_return_values: EntryPointReturnValues* = cast(
        return_values_ptr, EntryPointReturnValues*
    );
    %{
        syscall_handler.validate_and_discard_syscall_ptr(
            syscall_ptr_end=ids.entry_point_return_values.syscall_ptr
        )
    %}

    // Check that the execution was successful.
    assert entry_point_return_values.failure_flag = 0;

    let remaining_gas = entry_point_return_values.gas_builtin;
    let retdata_start = entry_point_return_values.retdata_start;
    let retdata_end = entry_point_return_values.retdata_end;

    local return_builtin_ptrs: BuiltinPointers*;
    %{
        from starkware.starknet.core.os.os_utils import update_builtin_pointers

        # Fill the values of all builtin pointers after the current transaction.
        ids.return_builtin_ptrs = segments.gen_arg(
            update_builtin_pointers(
                memory=memory,
                n_builtins=ids.n_builtins,
                builtins_encoding_addr=ids.builtin_params.builtin_encodings.address_,
                n_selected_builtins=ids.entry_point_n_builtins,
                selected_builtins_encoding_addr=ids.entry_point_builtin_list,
                orig_builtins_ptrs_addr=ids.builtin_ptrs.address_,
                selected_builtins_ptrs_addr=ids.returned_builtin_ptrs_subset,
                ),
            )
    %}
    select_builtins(
        n_builtins=n_builtins,
        all_encodings=builtin_params.builtin_encodings,
        all_ptrs=return_builtin_ptrs,
        n_selected_builtins=entry_point_n_builtins,
        selected_encodings=entry_point_builtin_list,
        selected_ptrs=returned_builtin_ptrs_subset,
    );

    // Call validate_builtins to validate that the builtin pointers have advanced correctly.
    validate_builtins(
        prev_builtin_ptrs=builtin_ptrs,
        new_builtin_ptrs=return_builtin_ptrs,
        builtin_instance_sizes=builtin_params.builtin_instance_sizes,
        n_builtins=n_builtins,
    );

    let builtin_ptrs = return_builtin_ptrs;
    with syscall_ptr {
        call_execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_ptr_end=entry_point_return_values.syscall_ptr,
        );
    }

    %{ execution_helper.exit_call() %}
    return (retdata_size=retdata_end - retdata_start, retdata=retdata_start);
}
