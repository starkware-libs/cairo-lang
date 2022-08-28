%builtins output pedersen range_check ecdsa bitwise ec_op

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.math import assert_not_equal
from starkware.starknet.core.os.block_context import BlockContext, get_block_context
from starkware.starknet.core.os.os_config.os_config import get_starknet_os_config_hash
from starkware.starknet.core.os.output import OsCarriedOutputs, os_output_serialize
from starkware.starknet.core.os.state import state_update
from starkware.starknet.core.os.transactions import execute_transactions

// Executes transactions on StarkNet.
func main{
    output_ptr: felt*,
    pedersen_ptr: HashBuiltin*,
    range_check_ptr,
    ecdsa_ptr,
    bitwise_ptr,
    ec_op_ptr,
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
        ids.initial_carried_outputs.deployment_info = segments.add_temp_segment()
    %}

    let (block_context: BlockContext*) = get_block_context();

    let outputs = initial_carried_outputs;
    with outputs {
        let (local reserved_range_checks_end, state_changes) = execute_transactions(
            block_context=block_context
        );
    }
    let final_carried_outputs = outputs;

    local ecdsa_ptr = ecdsa_ptr;
    local bitwise_ptr = bitwise_ptr;

    local initial_storage_updates_ptr: felt*;
    %{
        # This hint shouldn't be whitelisted.
        vm_enter_scope(dict(
            storage_by_address=storage_by_address, global_state_storage=global_state_storage,
            os_input=os_input, __merkle_multi_update_skip_validation_runner=pedersen_builtin))
        ids.initial_storage_updates_ptr = segments.add_temp_segment()
    %}
    let storage_updates_ptr = initial_storage_updates_ptr;

    with storage_updates_ptr {
        let (commitment_tree_update_output) = state_update{hash_ptr=pedersen_ptr}(
            state_changes_dict=state_changes.changes_start,
            state_changes_dict_end=state_changes.changes_end,
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
        commitment_tree_update_output=commitment_tree_update_output,
        initial_carried_outputs=initial_carried_outputs,
        final_carried_outputs=final_carried_outputs,
        storage_updates_ptr_start=initial_storage_updates_ptr,
        storage_updates_ptr_end=storage_updates_ptr,
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
