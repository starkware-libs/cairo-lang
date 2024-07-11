from starkware.cairo.common.math import assert_nn_le
from starkware.cairo.common.memcpy import memcpy
from starkware.starknet.core.os.output import (
    MessageToL1Header,
    MessageToL2Header,
    OsCarriedOutputs,
    OsOutput,
    OsOutputHeader,
)
from starkware.starknet.core.os.state.commitment import CommitmentUpdate
from starkware.starknet.core.os.state.squash import squash_class_changes, squash_state_changes
from starkware.starknet.core.os.state.state import SquashedOsStateUpdate

// Copies the L1<>L2 message segments from `current` to the end of the aggregated values
// and returns the new aggregated values.
func copy_l1l2_messages(
    aggregated_carried_outputs: OsCarriedOutputs*, current: OsOutput*
) -> OsCarriedOutputs* {
    alloc_locals;

    local initial_messages_to_l1: felt* = current.initial_carried_outputs.messages_to_l1;
    local final_messages_to_l1: felt* = current.final_carried_outputs.messages_to_l1;
    local res_messages_to_l1: felt* = aggregated_carried_outputs.messages_to_l1;
    local len_messages_to_l1: felt = final_messages_to_l1 - initial_messages_to_l1;
    memcpy(dst=res_messages_to_l1, src=initial_messages_to_l1, len=len_messages_to_l1);
    local res_messages_to_l1: felt* = res_messages_to_l1 + len_messages_to_l1;

    local initial_messages_to_l2: felt* = current.initial_carried_outputs.messages_to_l2;
    local final_messages_to_l2: felt* = current.final_carried_outputs.messages_to_l2;
    local res_messages_to_l2: felt* = aggregated_carried_outputs.messages_to_l2;
    local len_messages_to_l2: felt = final_messages_to_l2 - initial_messages_to_l2;
    memcpy(dst=res_messages_to_l2, src=initial_messages_to_l2, len=len_messages_to_l2);
    local res_messages_to_l2: felt* = res_messages_to_l2 + len_messages_to_l2;

    tempvar res = new OsCarriedOutputs(
        messages_to_l1=cast(res_messages_to_l1, MessageToL1Header*),
        messages_to_l2=cast(res_messages_to_l2, MessageToL2Header*),
    );

    return res;
}

// Combines the outputs of multiple Starknet OS runs into a single output, by:
// * checking that the final values of one block match the initial values of the next block,
// * squashing the state updates,
// * concatenating the L1<>L2 message segments.
//
// `os_program_hash` is used for the `os_program_hash` field of the combined output.
func combine_blocks{range_check_ptr}(
    n: felt, os_outputs: OsOutput*, os_program_hash: felt
) -> OsOutput* {
    alloc_locals;

    assert_nn_le(1, n);

    local initial_carried_outputs: OsCarriedOutputs*;

    %{
        # Allocate segments for the messages.
        ids.initial_carried_outputs = segments.gen_arg(
            [segments.add_temp_segment(), segments.add_temp_segment()]
        )
    %}

    let first = os_outputs[0];

    // Copy the messages of the first block.
    let final_carried_outputs = copy_l1l2_messages(
        aggregated_carried_outputs=initial_carried_outputs, current=&first
    );

    tempvar aggregated = new OsOutput(
        header=new OsOutputHeader(
            state_update_output=first.header.state_update_output,
            prev_block_number=first.header.prev_block_number,
            new_block_number=first.header.new_block_number,
            prev_block_hash=first.header.prev_block_hash,
            new_block_hash=first.header.new_block_hash,
            os_program_hash=os_program_hash,
            starknet_os_config_hash=first.header.starknet_os_config_hash,
            use_kzg_da=nondet %{ program_input["use_kzg_da"] %},
            full_output=nondet %{ program_input["full_output"] %},
        ),
        squashed_os_state_update=first.squashed_os_state_update,
        initial_carried_outputs=initial_carried_outputs,
        final_carried_outputs=final_carried_outputs,
    );

    let res = combine_blocks_inner(aggregated=aggregated, n=n - 1, os_outputs=&os_outputs[1]);
    local res_state_update: SquashedOsStateUpdate = [res.squashed_os_state_update];

    // Squash the contract state tree.
    let (n_contract_state_changes, squashed_contract_state_dict) = squash_state_changes(
        contract_state_changes_start=res_state_update.contract_state_changes,
        contract_state_changes_end=&res_state_update.contract_state_changes[
            res_state_update.n_contract_state_changes
        ],
    );

    // Squash the contract class tree.
    let (n_class_updates, squashed_class_changes) = squash_class_changes(
        class_changes_start=res_state_update.contract_class_changes,
        class_changes_end=&res_state_update.contract_class_changes[
            res_state_update.n_class_updates
        ],
    );

    tempvar squashed_res = new OsOutput(
        header=res.header,
        squashed_os_state_update=new SquashedOsStateUpdate(
            contract_state_changes=squashed_contract_state_dict,
            n_contract_state_changes=n_contract_state_changes,
            contract_class_changes=squashed_class_changes,
            n_class_updates=n_class_updates,
        ),
        initial_carried_outputs=res.initial_carried_outputs,
        final_carried_outputs=res.final_carried_outputs,
    );

    return squashed_res;
}

// Helper function for `combine_blocks`.
func combine_blocks_inner(aggregated: OsOutput*, n: felt, os_outputs: OsOutput*) -> OsOutput* {
    if (n == 0) {
        return aggregated;
    }

    alloc_locals;

    let current = os_outputs[0];

    // Check the size of `OsOutput` and `OsOutputHeader` to ensure that if new fields are added
    // they are handled by the aggregator, either in this function or in `output_blocks()`.
    static_assert OsOutput.SIZE == 4;
    static_assert OsOutputHeader.SIZE == 9;

    // Check header consistency.
    assert current.header.state_update_output.initial_root = (
        aggregated.header.state_update_output.final_root
    );
    assert current.header.prev_block_number = aggregated.header.new_block_number;
    assert current.header.prev_block_hash = aggregated.header.new_block_hash;
    assert current.header.starknet_os_config_hash = aggregated.header.starknet_os_config_hash;

    // Check `squashed_os_state_update` consistency: the dictionary entries of the blocks must form
    // one contiguous segment (this is done as part of the hint generating them). Check that the
    // beginning of the current block is at the end of the blocks aggregated so far.
    local aggregated_update: SquashedOsStateUpdate = [aggregated.squashed_os_state_update];
    local current_update: SquashedOsStateUpdate = [current.squashed_os_state_update];
    assert current_update.contract_state_changes = &aggregated_update.contract_state_changes[
        aggregated_update.n_contract_state_changes
    ];
    assert current_update.contract_class_changes = &aggregated_update.contract_class_changes[
        aggregated_update.n_class_updates
    ];

    // Copy the messages.
    let final_carried_outputs = copy_l1l2_messages(
        aggregated_carried_outputs=aggregated.final_carried_outputs, current=&current
    );

    tempvar new_aggregated = new OsOutput(
        header=new OsOutputHeader(
            state_update_output=new CommitmentUpdate(
                initial_root=aggregated.header.state_update_output.initial_root,
                final_root=current.header.state_update_output.final_root,
            ),
            prev_block_number=aggregated.header.prev_block_number,
            new_block_number=current.header.new_block_number,
            prev_block_hash=aggregated.header.prev_block_hash,
            new_block_hash=current.header.new_block_hash,
            os_program_hash=aggregated.header.os_program_hash,
            starknet_os_config_hash=aggregated.header.starknet_os_config_hash,
            use_kzg_da=aggregated.header.use_kzg_da,
            full_output=aggregated.header.full_output,
        ),
        squashed_os_state_update=new SquashedOsStateUpdate(
            contract_state_changes=aggregated_update.contract_state_changes,
            n_contract_state_changes=(
                aggregated_update.n_contract_state_changes + current_update.n_contract_state_changes
            ),
            contract_class_changes=aggregated_update.contract_class_changes,
            n_class_updates=aggregated_update.n_class_updates + current_update.n_class_updates,
        ),
        initial_carried_outputs=aggregated.initial_carried_outputs,
        final_carried_outputs=final_carried_outputs,
    );

    return combine_blocks_inner(aggregated=new_aggregated, n=n - 1, os_outputs=&os_outputs[1]);
}
