from starkware.cairo.builtin_selection.select_input_builtins import select_input_builtins
from starkware.cairo.builtin_selection.validate_builtins import validate_builtins
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bool import FALSE
from starkware.cairo.common.cairo_builtins import KeccakBuiltin
from starkware.cairo.common.dict import dict_read
from starkware.cairo.common.dict_access import DictAccess
from starkware.cairo.common.find_element import find_element, search_sorted_optimistic
from starkware.cairo.common.math import assert_lt, assert_nn, assert_not_zero
from starkware.cairo.common.registers import get_ap
from starkware.starknet.builtins.segment_arena.segment_arena import (
    SegmentArenaBuiltin,
    validate_segment_arena,
)
from starkware.starknet.common.new_syscalls import ExecutionInfo
from starkware.starknet.common.syscalls import TxInfo as DeprecatedTxInfo
from starkware.starknet.core.os.block_context import BlockContext
from starkware.starknet.core.os.builtins import (
    BuiltinEncodings,
    BuiltinParams,
    BuiltinPointers,
    NonSelectableBuiltins,
    SelectableBuiltins,
    update_builtin_ptrs,
)
from starkware.starknet.core.os.constants import (
    DEFAULT_ENTRY_POINT_SELECTOR,
    ENTRY_POINT_INITIAL_BUDGET,
    ENTRY_POINT_TYPE_CONSTRUCTOR,
    ENTRY_POINT_TYPE_EXTERNAL,
    ENTRY_POINT_TYPE_L1_HANDLER,
    ERROR_ENTRY_POINT_NOT_FOUND,
    ERROR_OUT_OF_GAS,
    NOP_ENTRY_POINT_OFFSET,
    SIERRA_ARRAY_LEN_BOUND,
)
from starkware.starknet.core.os.contract_class.compiled_class import (
    CompiledClass,
    CompiledClassEntryPoint,
    CompiledClassFact,
)
from starkware.starknet.core.os.execution.revert import (
    RevertLogEntry,
    handle_revert,
    init_revert_log,
)
from starkware.starknet.core.os.output import OsCarriedOutputs
from starkware.starknet.core.os.state.commitment import StateEntry

// Represents the execution context during the execution of contract code.
struct ExecutionContext {
    entry_point_type: felt,
    // The hash of the contract class to execute.
    class_hash: felt,
    calldata_size: felt,
    calldata: felt*,
    // Additional information about the execution.
    execution_info: ExecutionInfo*,
    // Information about the transaction that triggered the execution.
    deprecated_tx_info: DeprecatedTxInfo*,
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
    revert_log: RevertLogEntry*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, execution_context: ExecutionContext*, syscall_ptr_end: felt*) {
    jmp abs block_context.execute_syscalls_ptr;
}

// Returns the CompiledClassEntryPoint, based on 'compiled_class' and 'execution_context'.
func get_entry_point{range_check_ptr}(
    compiled_class: CompiledClass*, execution_context: ExecutionContext*
) -> (success: felt, entry_point: CompiledClassEntryPoint*) {
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
                return (success=1, entry_point=cast(0, CompiledClassEntryPoint*));
            }
        }
    }

    // The key must be at offset 0.
    static_assert CompiledClassEntryPoint.selector == 0;
    let (entry_point_desc: CompiledClassEntryPoint*, success) = search_sorted_optimistic(
        array_ptr=cast(entry_points, felt*),
        elm_size=CompiledClassEntryPoint.SIZE,
        n_elms=n_entry_points,
        key=execution_context.execution_info.selector,
    );
    if (success != FALSE) {
        return (success=1, entry_point=entry_point_desc);
    }

    return (success=0, entry_point=cast(0, CompiledClassEntryPoint*));
}

// Executes an entry point in a contract.
// The contract entry point is selected based on execution_context.entry_point_type
// and execution_context.execution_info.selector.
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
    revert_log: RevertLogEntry*,
    outputs: OsCarriedOutputs*,
}(block_context: BlockContext*, execution_context: ExecutionContext*) -> (
    is_reverted: felt, retdata_size: felt, retdata: felt*
) {
    alloc_locals;
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
    let (success, compiled_class_entry_point: CompiledClassEntryPoint*) = get_entry_point(
        compiled_class=compiled_class, execution_context=execution_context
    );

    if (success == 0) {
        %{ execution_helper.exit_call() %}
        let (retdata: felt*) = alloc();
        assert retdata[0] = ERROR_ENTRY_POINT_NOT_FOUND;
        return (is_reverted=1, retdata_size=1, retdata=retdata);
    }

    if (compiled_class_entry_point == cast(0, CompiledClassEntryPoint*)) {
        %{ execution_helper.exit_call() %}
        // Assert that there is no call data in the case of NOP entry point.
        assert execution_context.calldata_size = 0;
        return (is_reverted=0, retdata_size=0, retdata=cast(0, felt*));
    }

    let entry_point_offset = compiled_class_entry_point.offset;
    local range_check_ptr = range_check_ptr;
    local contract_entry_point: felt* = compiled_class.bytecode_ptr + entry_point_offset;

    let (local os_context: felt*) = alloc();
    let (local syscall_ptr: felt*) = alloc();

    %{ syscall_handler.set_syscall_ptr(syscall_ptr=ids.syscall_ptr) %}
    assert [os_context] = cast(syscall_ptr, felt);

    if (nondet %{ ids.remaining_gas < ids.ENTRY_POINT_INITIAL_BUDGET %} != FALSE) {
        assert_lt(remaining_gas, ENTRY_POINT_INITIAL_BUDGET);
        %{ execution_helper.exit_call() %}
        let (retdata: felt*) = alloc();
        assert retdata[0] = ERROR_OUT_OF_GAS;
        return (is_reverted=1, retdata_size=1, retdata=retdata);
    }

    let remaining_gas = remaining_gas - ENTRY_POINT_INITIAL_BUDGET;
    // Remaining gas should be at least ENTRY_POINT_INITIAL_BUDGET.
    assert_nn(remaining_gas);

    let builtin_ptrs: BuiltinPointers* = prepare_builtin_ptrs_for_execute(builtin_ptrs);

    let n_builtins = BuiltinEncodings.SIZE;
    local builtin_params: BuiltinParams* = block_context.builtin_params;
    local calldata_size: felt = execution_context.calldata_size;
    local calldata_start: felt* = execution_context.calldata;
    local calldata_end: felt* = calldata_start + calldata_size;
    local entry_point_n_builtins = compiled_class_entry_point.n_builtins;
    local entry_point_builtin_list: felt* = compiled_class_entry_point.builtin_list;

    // Sanity check: Verify that `calldata` is a valid Sierra array.
    // Don't use `assert_nn_le` for efficiency.
    assert [range_check_ptr] = calldata_size;
    assert [range_check_ptr + 1] = calldata_size + 2 ** 128 - SIERRA_ARRAY_LEN_BOUND;
    let range_check_ptr = range_check_ptr + 2;

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
        if execution_helper.debug_mode:
            # Validate the predicted gas cost.
            actual = ids.remaining_gas - ids.entry_point_return_values.gas_builtin
            predicted = execution_helper.call_info.gas_consumed
            if execution_helper.call_info.tracked_resource.is_sierra_gas():
                predicted = predicted - ids.ENTRY_POINT_INITIAL_BUDGET
                assert actual == predicted, (
                    "Predicted gas costs are inconsistent with the actual execution; "
                    f"{predicted=}, {actual=}."
                )
            else:
                assert predicted == 0, "Predicted gas cost must be zero in CairoSteps mode."


        # Exit call.
        syscall_handler.validate_and_discard_syscall_ptr(
            syscall_ptr_end=ids.entry_point_return_values.syscall_ptr
        )
        execution_helper.exit_call()
    %}
    local is_reverted = entry_point_return_values.failure_flag;

    let remaining_gas = entry_point_return_values.gas_builtin;
    let retdata_start = entry_point_return_values.retdata_start;
    let retdata_end = entry_point_return_values.retdata_end;

    let return_builtin_ptrs = update_builtin_ptrs(
        builtin_params=builtin_params,
        builtin_ptrs=builtin_ptrs,
        n_selected_builtins=entry_point_n_builtins,
        selected_encodings=entry_point_builtin_list,
        selected_ptrs=returned_builtin_ptrs_subset,
    );

    // Validate the segment_arena builtin.
    // Note that as the segment_arena pointer points to the first unused element, we need to
    // take segment_arena[-1] to get the actual values.
    tempvar prev_segment_arena = &builtin_ptrs.selectable.segment_arena[-1];
    tempvar current_segment_arena = &return_builtin_ptrs.selectable.segment_arena[-1];
    assert prev_segment_arena.infos = current_segment_arena.infos;
    validate_segment_arena(segment_arena=current_segment_arena);

    local orig_revert_log: RevertLogEntry* = revert_log;
    local orig_outputs: OsCarriedOutputs* = outputs;

    // If necessary, create a new revert_log and dummy outputs before calling
    // `call_execute_syscalls`.
    if (is_reverted != FALSE) {
        // Create a new revert log for the reverted entry point. This will be used to revert the
        // entry point changes after calling `call_execute_syscalls`.
        let revert_log = init_revert_log();
        // Create a dummy OsCarriedOutputs so that messages to L1 will be discarded.
        // The dummy is initialized with
        // OsCarriedOutputs(messages_to_l1="empty segment", messages_to_l2=0).
        tempvar outputs = cast(nondet %{ segments.gen_arg([[], 0]) %}, OsCarriedOutputs*);
    } else {
        tempvar revert_log = orig_revert_log;
        tempvar outputs = orig_outputs;
    }
    let builtin_ptrs = return_builtin_ptrs;
    with syscall_ptr {
        call_execute_syscalls(
            block_context=block_context,
            execution_context=execution_context,
            syscall_ptr_end=entry_point_return_values.syscall_ptr,
        );
    }

    if (is_reverted != FALSE) {
        handle_revert(
            contract_address=execution_context.execution_info.contract_address,
            revert_log_end=revert_log,
        );
        // Restore the original revert log and outputs.
        let revert_log = orig_revert_log;
        let outputs = orig_outputs;
        return (
            is_reverted=is_reverted, retdata_size=retdata_end - retdata_start, retdata=retdata_start
        );
    }

    return (
        is_reverted=is_reverted, retdata_size=retdata_end - retdata_start, retdata=retdata_start
    );
}

// Prepares the builtin pointer for the execution of an entry point.
// In particular, restarts the SegmentArenaBuiltin struct if it was previously used.
func prepare_builtin_ptrs_for_execute(builtin_ptrs: BuiltinPointers*) -> BuiltinPointers* {
    let selectable_builtins = &builtin_ptrs.selectable;
    tempvar segment_arena_ptr = selectable_builtins.segment_arena;
    tempvar prev_segment_arena = &segment_arena_ptr[-1];

    // If no segment was allocated, we don't need to restart the struct.
    tempvar prev_n_segments = prev_segment_arena.n_segments;
    if (prev_n_segments == 0) {
        return builtin_ptrs;
    }

    assert segment_arena_ptr[0] = SegmentArenaBuiltin(
        infos=&prev_segment_arena.infos[prev_n_segments], n_segments=0, n_finalized=0
    );
    let segment_arena_ptr = &segment_arena_ptr[1];
    return new BuiltinPointers(
        selectable=SelectableBuiltins(
            pedersen=selectable_builtins.pedersen,
            range_check=selectable_builtins.range_check,
            ecdsa=selectable_builtins.ecdsa,
            bitwise=selectable_builtins.bitwise,
            ec_op=selectable_builtins.ec_op,
            poseidon=selectable_builtins.poseidon,
            segment_arena=segment_arena_ptr,
            range_check96=selectable_builtins.range_check96,
            add_mod=selectable_builtins.add_mod,
            mul_mod=selectable_builtins.mul_mod,
        ),
        non_selectable=builtin_ptrs.non_selectable,
    );
}
