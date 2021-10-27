from starkware.cairo.common.segments import relocate_segment
from starkware.cairo.common.serialize import serialize_word
from starkware.starknet.core.os.state import CommitmentTreeUpdateOutput

# A cross layer message header, the message payload is concatenated to the end of the header.
# The sender/receiver can be on L1 or L2 depending on the message direction.
struct MessageHeader:
    # The address of the contract sending the message.
    member from_address : felt
    # The address of the contract receiving the message.
    member to_address : felt
    member payload_size : felt
end

# A contract deployment information header.
# Call data of size 'calldata_size' is concatenated to the end of the header.
struct DeploymentInfoHeader:
    member contract_address : felt
    member contract_hash : felt
    member calldata_size : felt
end

# Holds all the information that StarkNet's OS needs to output.
struct OsCarriedOutputs:
    member messages_to_l1 : MessageHeader*
    member messages_to_l2 : MessageHeader*
    # A concatenated list of deployment infos, each consists of DeploymentInfoHeader and calldata.
    member deployment_info : DeploymentInfoHeader*
end

struct OsOutput:
    # The previous and new root of the contract's storage.
    member commitment_tree_update_output : CommitmentTreeUpdateOutput*
    member initial_outputs : OsCarriedOutputs
    member final_outputs : OsCarriedOutputs
end

func os_output_serialize{output_ptr : felt*}(
        os_output : OsOutput*, storage_updates_ptr_start : felt*, storage_updates_ptr_end : felt*):
    # Serialize program output.

    # Serialize roots.
    serialize_word(os_output.commitment_tree_update_output.initial_storage_root)
    serialize_word(os_output.commitment_tree_update_output.final_storage_root)

    let messages_to_l1_segment_size = (
        os_output.final_outputs.messages_to_l1 -
        os_output.initial_outputs.messages_to_l1)
    serialize_word(messages_to_l1_segment_size)

    # Relocate 'messages_to_l1_segment' to the correct place in the output segment.
    relocate_segment(src_ptr=os_output.initial_outputs.messages_to_l1, dest_ptr=output_ptr)
    let output_ptr = cast(os_output.final_outputs.messages_to_l1, felt*)

    let messages_to_l2_segment_size = (
        os_output.final_outputs.messages_to_l2 -
        os_output.initial_outputs.messages_to_l2)
    serialize_word(messages_to_l2_segment_size)

    # Relocate 'messages_to_l2_segment' to the correct place in the output segment.
    relocate_segment(src_ptr=os_output.initial_outputs.messages_to_l2, dest_ptr=output_ptr)
    let output_ptr = cast(os_output.final_outputs.messages_to_l2, felt*)

    # Serialize data availability.
    let da_start = output_ptr

    let deployment_info_segment_size = (
        os_output.final_outputs.deployment_info -
        os_output.initial_outputs.deployment_info)
    serialize_word(deployment_info_segment_size)

    # Relocate 'deployment_info_segment' to the correct place in the output segment.
    relocate_segment(src_ptr=os_output.initial_outputs.deployment_info, dest_ptr=output_ptr)
    let output_ptr = cast(os_output.final_outputs.deployment_info, felt*)

    # Relocate 'storage_updates_segment' to the correct place in the output segment.
    relocate_segment(src_ptr=storage_updates_ptr_start, dest_ptr=output_ptr)
    let output_ptr = storage_updates_ptr_end

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

    return ()
end
