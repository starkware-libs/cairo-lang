%builtins output pedersen range_check ecdsa

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.dict import DictAccess
from starkware.cairo.common.math import assert_not_equal
from starkware.cairo.common.segments import relocate_segment
from starkware.cairo.common.serialize import serialize_word
from starkware.starknet.common.storage import Storage
from starkware.starknet.core.os.output import OsCarriedOutputs, OsOutput, os_output_serialize
from starkware.starknet.core.os.state import state_update
from starkware.starknet.core.os.transactions import MessageHeader, execute_transactions

# Executes transactions on StarkNet.
func main{output_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr}():
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
    %}
    tempvar outputs : OsCarriedOutputs = os_output.initial_outputs

    with outputs:
        let (local reserved_range_checks_end, state_changes) = execute_transactions()
    end
    assert os_output.final_outputs = outputs
    local ecdsa_ptr = ecdsa_ptr

    local initial_da_output_ptr : felt*
    %{
        # This hint shouldn't be whitelisted.
        vm_enter_scope(dict(
            storage_by_address=storage_by_address, global_state_storage=global_state_storage,
            os_input=os_input, __merkle_multi_update_skip_validation_runner=pedersen_builtin))
        ids.initial_da_output_ptr = segments.add_temp_segment()
    %}
    let da_output_ptr = initial_da_output_ptr
    with da_output_ptr:
        let (merkle_update_output) = state_update{hash_ptr=pedersen_ptr}(
            state_changes_dict=state_changes.changes_start,
            state_changes_dict_end=state_changes.changes_end)
    end
    assert os_output.merkle_update_output = merkle_update_output

    %{ vm_exit_scope() %}

    os_output_serialize(os_output=os_output)
    relocate_segment(src_ptr=initial_da_output_ptr, dest_ptr=output_ptr)
    let output_ptr = da_output_ptr

    %{
        from starkware.python.math_utils import div_ceil
        onchain_data_start = ids.initial_da_output_ptr
        onchain_data_size = ids.output_ptr - onchain_data_start

        max_page_size = 1000
        n_pages = div_ceil(onchain_data_size, max_page_size)
        for i in range(n_pages):
            start_offset = i * max_page_size
            output_builtin.add_page(
                page_id=1 + i,
                page_start=onchain_data_start + start_offset,
                page_size=min(onchain_data_size - start_offset, max_page_size),
            )
        # Set the tree structure to a root with two children:
        # * A leaf which represents the main part
        # * An inner node for the onchain data part (which contains n_pages children).
        #
        # This is encoded using the following sequence:
        output_builtin.add_attribute('gps_fact_topology', [
            # Push 1 + n_pages pages (all of the pages).
            1 + n_pages,
            # Create a parent node for the last n_pages.
            n_pages,
            # Don't push additional pages.
            0,
            # Take the first page (the main part) and the node that was created (onchain data)
            # and use them to construct the root of the fact tree.
            2,
        ])
    %}

    # Make sure that we report using at least 1 range check to guarantee that
    # initial_range_check_ptr points to a valid range check instance.
    assert_not_equal(initial_range_check_ptr, range_check_ptr)
    # Use initial_range_check_ptr to check that range_check_ptr >= reserved_range_checks_end.
    # This should guarantee that all the reserved range checks point to valid instances.
    assert [initial_range_check_ptr] = range_check_ptr - reserved_range_checks_end

    return ()
end
