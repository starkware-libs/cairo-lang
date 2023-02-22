%builtins output pedersen range_check ecdsa bitwise ec_op poseidon

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin, PoseidonBuiltin
from starkware.cairo.common.math import assert_not_equal
from starkware.cairo.common.registers import get_label_location
from starkware.starknet.core.os.block_context import BlockContext, get_block_context
from starkware.starknet.core.os.execution.deprecated_execute_syscalls import (
    execute_deprecated_syscalls,
)
from starkware.starknet.core.os.execution.execute_syscalls import execute_syscalls
from starkware.starknet.core.os.execution.execute_transactions import execute_transactions
from starkware.starknet.core.os.os_config.os_config import get_starknet_os_config_hash
from starkware.starknet.core.os.output import OsCarriedOutputs, os_output_serialize
from starkware.starknet.core.os.state import state_update

// Executes transactions on StarkNet.
func main{
    output_ptr: felt*,
    pedersen_ptr: HashBuiltin*,
    range_check_ptr,
    ecdsa_ptr,
    bitwise_ptr,
    ec_op_ptr,
    poseidon_ptr: PoseidonBuiltin*,
}() {
    alloc_locals;

    // Reserve the initial range check for self validation.
    // Note that this must point to the first range check used by the OS.
    let initial_range_check_ptr = range_check_ptr;
    let range_check_ptr = range_check_ptr + 1;

    let (initial_carried_outputs: OsCarriedOutputs*) = alloc();
    %{
        from starkware.starknet.core.os.os_input import StarknetOsInput

        os_input = StarknetOsInput.load(data=program_input)

        ids.initial_carried_outputs.messages_to_l1 = segments.add_temp_segment()
        ids.initial_carried_outputs.messages_to_l2 = segments.add_temp_segment()
    %}

    let (execute_syscalls_ptr) = get_label_location(label_value=execute_syscalls);
    let (execute_deprecated_syscalls_ptr) = get_label_location(
        label_value=execute_deprecated_syscalls
    );
    let (block_context: BlockContext*) = get_block_context(
        execute_syscalls_ptr=execute_syscalls_ptr,
        execute_deprecated_syscalls_ptr=execute_deprecated_syscalls_ptr,
    );

    let outputs = initial_carried_outputs;
    with outputs {
        let (local reserved_range_checks_end, state_changes) = execute_transactions(
            block_context=block_context
        );
    }
    let final_carried_outputs = outputs;

    local ecdsa_ptr = ecdsa_ptr;
    local bitwise_ptr = bitwise_ptr;

    local initial_state_updates_ptr: felt*;
    %{
        # This hint shouldn't be whitelisted.
        vm_enter_scope(dict(
            storage_by_address=storage_by_address,
            os_input=os_input, __merkle_multi_update_skip_validation_runner=pedersen_builtin))
        ids.initial_state_updates_ptr = segments.add_temp_segment()
    %}
    let state_updates_ptr = initial_state_updates_ptr;

    with state_updates_ptr {
        let (state_update_output) = state_update{hash_ptr=pedersen_ptr}(
            state_changes=state_changes
        );
    }

    %{ vm_exit_scope() %}

    // Compute the general config hash.
    // This is done here to avoid passing pedersen_ptr to os_output_serialize.
    let hash_ptr = pedersen_ptr;
    with hash_ptr {
        let (starknet_os_config_hash) = get_starknet_os_config_hash(
            starknet_os_config=&block_context.starknet_os_config
        );
    }
    let pedersen_ptr = hash_ptr;

    os_output_serialize(
        block_context=block_context,
        state_update_output=state_update_output,
        initial_carried_outputs=initial_carried_outputs,
        final_carried_outputs=final_carried_outputs,
        state_updates_ptr_start=initial_state_updates_ptr,
        state_updates_ptr_end=state_updates_ptr,
        starknet_os_config_hash=starknet_os_config_hash,
    );

    // Make sure that we report using at least 1 range check to guarantee that
    // initial_range_check_ptr points to a valid range check instance.
    assert_not_equal(initial_range_check_ptr, range_check_ptr);
    // Use initial_range_check_ptr to check that range_check_ptr >= reserved_range_checks_end.
    // This should guarantee that all the reserved range checks point to valid instances.
    assert [initial_range_check_ptr] = range_check_ptr - reserved_range_checks_end;

    return ();
}
