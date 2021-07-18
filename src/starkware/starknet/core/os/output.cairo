from starkware.cairo.common.segments import relocate_segment
from starkware.cairo.common.serialize import serialize_word
from starkware.starknet.core.os.state import MerkleUpdateOutput

# Holds all the information that StarkNet's OS needs to output.
# A cross layer message header, the message payload is concatenated to the end of the header.
# The sender/receiver can be on L1 or L2 depending on the message direction.
struct MessageHeader:
    # The address of the contract sending the message.
    member from_address : felt
    # The address of the contract receiving the message.
    member to_address : felt
    member payload_size : felt
end

struct OsCarriedOutputs:
    member messages_to_l1 : MessageHeader*
    member messages_to_l2 : MessageHeader*
end

struct OsOutput:
    # The previous and new root of the contract's storage.
    member merkle_update_output : MerkleUpdateOutput*
    member initial_outputs : OsCarriedOutputs
    member final_outputs : OsCarriedOutputs
end

func os_output_serialize{output_ptr : felt*}(os_output : OsOutput*):
    serialize_word(os_output.merkle_update_output.initial_storage_root)
    serialize_word(os_output.merkle_update_output.final_storage_root)

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
    return ()
end
