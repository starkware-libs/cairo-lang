%builtins output pedersen range_check ecdsa bitwise

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.dict import DictAccess
from starkware.cairo.common.math import assert_not_equal
from starkware.cairo.common.segments import relocate_segment
from starkware.cairo.common.serialize import serialize_word
from starkware.starknet.core.os.output import OsCarriedOutputs, OsOutput, os_output_serialize
from starkware.starknet.core.os.state import state_update
from starkware.starknet.core.os.transactions import MessageHeader, execute_transactions

# Executes transactions on StarkNet.
func main{output_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr, bitwise_ptr}(
        ):
    alloc_locals

    # Reserve the initial range check for self validation.
    # Note that this must point to the first range check used by the OS.
    let initial_range_check_ptr = range_check_ptr
    let range_check_ptr = range_check_ptr + 1

    let (local os_output : OsOutput*) = alloc()
    %{
        from starkware.starknet.core.os.os_input import StarknetOsInput

        os_input = StarknetOsInput.Schema().load(program_input)

        ids.os_output.initial_outputs.messages_to_l1 = segments.add_temp_segment()
        ids.os_output.initial_outputs.messages_to_l2 = segments.add_temp_segment()
        ids.os_output.initial_outputs.deployment_info = segments.add_temp_segment()
    %}
    tempvar outputs : OsCarriedOutputs = os_output.initial_outputs

    with outputs:
        let (local reserved_range_checks_end, state_changes) = execute_transactions()
    end
    assert os_output.final_outputs = outputs
    local ecdsa_ptr = ecdsa_ptr
    local bitwise_ptr = bitwise_ptr

    local initial_storage_updates_ptr : felt*
    %{
        # This hint shouldn't be whitelisted.
        vm_enter_scope(dict(
            storage_by_address=storage_by_address, global_state_storage=global_state_storage,
            os_input=os_input, __merkle_multi_update_skip_validation_runner=pedersen_builtin))
        ids.initial_storage_updates_ptr = segments.add_temp_segment()
    %}
    let storage_updates_ptr = initial_storage_updates_ptr
    with storage_updates_ptr:
        let (commitment_tree_update_output) = state_update{hash_ptr=pedersen_ptr}(
            state_changes_dict=state_changes.changes_start,
            state_changes_dict_end=state_changes.changes_end)
    end
    assert os_output.commitment_tree_update_output = commitment_tree_update_output

    %{ vm_exit_scope() %}

    os_output_serialize(
        os_output=os_output,
        storage_updates_ptr_start=initial_storage_updates_ptr,
        storage_updates_ptr_end=storage_updates_ptr)

    # Make sure that we report using at least 1 range check to guarantee that
    # initial_range_check_ptr points to a valid range check instance.
    assert_not_equal(initial_range_check_ptr, range_check_ptr)
    # Use initial_range_check_ptr to check that range_check_ptr >= reserved_range_checks_end.
    # This should guarantee that all the reserved range checks point to valid instances.
    assert [initial_range_check_ptr] = range_check_ptr - reserved_range_checks_end

    return ()
end
