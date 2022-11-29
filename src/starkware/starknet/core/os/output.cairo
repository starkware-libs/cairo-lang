from starkware.cairo.common.registers import get_fp_and_pc
from starkware.cairo.common.segments import relocate_segment
from starkware.cairo.common.serialize import serialize_word
from starkware.starknet.core.os.block_context import BlockContext, BlockInfo
from starkware.starknet.core.os.state import CommitmentTreeUpdateOutput

// An L2 to L1 message header, the message payload is concatenated to the end of the header.
struct MessageToL1Header {
    // The L2 address of the contract sending the message.
    from_address: felt,
    // The L1 address of the contract receiving the message.
    to_address: felt,
    payload_size: felt,
}

// An L1 to L2 message header, the message payload is concatenated to the end of the header.
struct MessageToL2Header {
    // The L1 address of the contract sending the message.
    from_address: felt,
    // The L2 address of the contract receiving the message.
    to_address: felt,
    nonce: felt,
    selector: felt,
    payload_size: felt,
}

// Contract deployment information.
struct DeploymentInfo {
    contract_address: felt,
    class_hash: felt,
}

// Holds all the information that StarkNet's OS needs to output.
struct OsCarriedOutputs {
    messages_to_l1: MessageToL1Header*,
    messages_to_l2: MessageToL2Header*,
    // A concatenated list of deployment infos.
    deployment_info: DeploymentInfo*,
}

func os_carried_outputs_new(
    messages_to_l1: MessageToL1Header*,
    messages_to_l2: MessageToL2Header*,
    deployment_info: DeploymentInfo*,
) -> (os_carried_outputs: OsCarriedOutputs*) {
    let (fp_val, pc_val) = get_fp_and_pc();
    static_assert OsCarriedOutputs.SIZE == Args.SIZE;
    return (os_carried_outputs=cast(fp_val - 2 - OsCarriedOutputs.SIZE, OsCarriedOutputs*));
}

func os_output_serialize{output_ptr: felt*}(
    block_context: BlockContext*,
    commitment_tree_update_output: CommitmentTreeUpdateOutput*,
    initial_carried_outputs: OsCarriedOutputs*,
    final_carried_outputs: OsCarriedOutputs*,
    storage_updates_ptr_start: felt*,
    storage_updates_ptr_end: felt*,
    starknet_os_config_hash: felt,
) {
    // Serialize program output.

    // Serialize roots.
    serialize_word(commitment_tree_update_output.initial_storage_root);
    serialize_word(commitment_tree_update_output.final_storage_root);

    serialize_word(block_context.block_info.block_number);
    serialize_word(starknet_os_config_hash);

    let messages_to_l1_segment_size = (
        final_carried_outputs.messages_to_l1 - initial_carried_outputs.messages_to_l1
    );
    serialize_word(messages_to_l1_segment_size);

    // Relocate 'messages_to_l1_segment' to the correct place in the output segment.
    relocate_segment(src_ptr=initial_carried_outputs.messages_to_l1, dest_ptr=output_ptr);
    let output_ptr = cast(final_carried_outputs.messages_to_l1, felt*);

    let messages_to_l2_segment_size = (
        final_carried_outputs.messages_to_l2 - initial_carried_outputs.messages_to_l2
    );
    serialize_word(messages_to_l2_segment_size);

    // Relocate 'messages_to_l2_segment' to the correct place in the output segment.
    relocate_segment(src_ptr=initial_carried_outputs.messages_to_l2, dest_ptr=output_ptr);
    let output_ptr = cast(final_carried_outputs.messages_to_l2, felt*);

    // Serialize data availability.
    let da_start = output_ptr;

    let deployment_info_segment_size = (
        final_carried_outputs.deployment_info - initial_carried_outputs.deployment_info
    );
    serialize_word(deployment_info_segment_size);

    // Relocate 'deployment_info_segment' to the correct place in the output segment.
    relocate_segment(src_ptr=initial_carried_outputs.deployment_info, dest_ptr=output_ptr);
    let output_ptr = cast(final_carried_outputs.deployment_info, felt*);

    // Relocate 'storage_updates_segment' to the correct place in the output segment.
    relocate_segment(src_ptr=storage_updates_ptr_start, dest_ptr=output_ptr);
    let output_ptr = storage_updates_ptr_end;

    %{
        from starkware.python.math_utils import div_ceil
        onchain_data_start = ids.da_start
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

    return ();
}
