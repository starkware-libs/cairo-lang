# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

%builtins output pedersen range_check ecdsa

from starkware.cairo.apps.starkex2_0.__start__ import __start__
from starkware.cairo.apps.starkex2_0.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.apps.starkex2_0.common.dict import DictAccess, squash_dict
from starkware.cairo.apps.starkex2_0.common.merkle_multi_update import merkle_multi_update
from starkware.cairo.apps.starkex2_0.dex_context import make_dex_context
from starkware.cairo.apps.starkex2_0.execute_batch import execute_batch
from starkware.cairo.apps.starkex2_0.execute_modification import ModificationOutput
from starkware.cairo.apps.starkex2_0.hash_vault_ptr_dict import hash_vault_ptr_dict
from starkware.cairo.apps.starkex2_0.vault_update import VaultState

struct DexOutput:
    member initial_vault_root : felt
    member final_vault_root : felt
    member initial_order_root : felt
    member final_order_root : felt
    member global_expiration_timestamp : felt
    member vault_tree_height : felt
    member order_tree_height : felt
    member n_modifications : felt
    member n_conditional_transfers : felt
end

func main(
        output_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr,
        ecdsa_ptr : SignatureBuiltin*) -> (
        output_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr,
        ecdsa_ptr : SignatureBuiltin*):
    alloc_locals
    # Create the globals struct.
    let dex_output = cast(output_ptr, DexOutput*)
    let (dex_context_ptr) = make_dex_context(
        vault_tree_height=dex_output.vault_tree_height,
        order_tree_height=dex_output.order_tree_height,
        global_expiration_timestamp=dex_output.global_expiration_timestamp)

    local vault_dict : DictAccess*
    local order_dict : DictAccess*
    local conditional_transfer_ptr : felt*
    # Call execute_batch.
    # Advance output_ptr by DexOutput.SIZE, since DexOutput appears before other stuff.
    let executed_batch = execute_batch(
        modification_ptr=cast(output_ptr + DexOutput.SIZE, ModificationOutput*),
        conditional_transfer_ptr=conditional_transfer_ptr,
        hash_ptr=pedersen_ptr,
        range_check_ptr=range_check_ptr,
        ecdsa_ptr=ecdsa_ptr,
        vault_dict=vault_dict,
        order_dict=order_dict,
        dex_context_ptr=dex_context_ptr)
    let range_check_ptr = executed_batch.range_check_ptr

    # Assert conditional transfer data starts where modification data ends.
    conditional_transfer_ptr = executed_batch.modification_ptr

    # Store conditional transfer end pointer.
    local conditional_transfer_end_ptr : felt* = cast(
        executed_batch.conditional_transfer_ptr, felt*)

    # Assert that the number of modifications that appear in the output is correct.
    assert dex_output.n_modifications = (
        cast(conditional_transfer_ptr, felt) - (cast(output_ptr, felt) + DexOutput.SIZE)) /
        ModificationOutput.SIZE

    # Assert that the number of conditional transfers that appear in the output is correct.
    assert dex_output.n_conditional_transfers = (
        conditional_transfer_end_ptr - conditional_transfer_ptr)

    # Store builtin pointers.
    local hash_ptr_after_execute_batch : HashBuiltin* = executed_batch.hash_ptr
    local ecdsa_ptr_after_execute_batch : SignatureBuiltin* = executed_batch.ecdsa_ptr
    local order_dict_end : DictAccess* = executed_batch.order_dict

    # Check that the vault and order accesses recorded in vault_dict and dict_vault are
    # valid lists of dict accesses and squash them to obtain squashed dicts
    # (squashed_vault_dict and squashed_order_dict) with one entry per key
    # (value before and value after) which summarizes all the accesses to that key.

    # Squash the vault_dict.
    with range_check_ptr:
        local squashed_vault_dict : DictAccess*
        let (squash_vault_dict_ret) = squash_dict(
            dict_accesses=vault_dict,
            dict_accesses_end=executed_batch.vault_dict,
            squashed_dict=squashed_vault_dict)
        local squashed_vault_dict_segment_size = squash_vault_dict_ret - squashed_vault_dict

        # Squash the order_dict.
        local squashed_order_dict : DictAccess*
        let (squash_order_dict_ret) = squash_dict(
            dict_accesses=order_dict,
            dict_accesses_end=order_dict_end,
            squashed_dict=squashed_order_dict)
    end
    local squashed_order_dict_segment_size = squash_order_dict_ret - squashed_order_dict
    local range_check_ptr_after_squash_order_dict = range_check_ptr

    # The squashed_vault_dict holds pointers to vault states instead of vault tree leaf values.
    # Call hash_vault_ptr_dict to obtain a new dict that can be passed to merkle_multi_update.
    local hashed_vault_dict : DictAccess*
    let (hash_vault_dict_ptr) = hash_vault_ptr_dict(
        hash_ptr=hash_ptr_after_execute_batch,
        vault_ptr_dict=squashed_vault_dict,
        n_entries=squashed_vault_dict_segment_size / DictAccess.SIZE,
        vault_hash_dict=hashed_vault_dict)

    # Verify hashed_vault_dict consistency with the vault merkle root.
    # Make a copy of the first argument to avoid a compiler optimization that was added after the
    # code was deployed.
    [ap] = hash_vault_dict_ptr; ap++
    let hash_ptr = cast([ap - 1], HashBuiltin*)
    with hash_ptr:
        merkle_multi_update(
            update_ptr=hashed_vault_dict,
            n_updates=squashed_vault_dict_segment_size / DictAccess.SIZE,
            height=dex_output.vault_tree_height,
            prev_root=dex_output.initial_vault_root,
            new_root=dex_output.final_vault_root)

        # Verify squashed_order_dict consistency with the order merkle root.
        # Make a copy of the first argument to avoid a compiler optimization that was added after
        # the code was deployed.
        [ap] = hash_ptr; ap++
        let hash_ptr = cast([ap - 1], HashBuiltin*)
        merkle_multi_update(
            update_ptr=squashed_order_dict,
            n_updates=squashed_order_dict_segment_size / DictAccess.SIZE,
            height=dex_output.order_tree_height,
            prev_root=dex_output.initial_order_root,
            new_root=dex_output.final_order_root)
    end

    # Return updated pointers.
    return (
        output_ptr=conditional_transfer_end_ptr,
        pedersen_ptr=hash_ptr,
        range_check_ptr=range_check_ptr_after_squash_order_dict,
        ecdsa_ptr=ecdsa_ptr_after_execute_batch)
end
