# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

from starkware.cairo.apps.starkex2_0.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.apps.starkex2_0.common.dict import DictAccess
from starkware.cairo.apps.starkex2_0.dex_context import DexContext
from starkware.cairo.apps.starkex2_0.execute_false_full_withdrawal import (
    execute_false_full_withdrawal)
from starkware.cairo.apps.starkex2_0.execute_modification import (
    ModificationOutput, execute_modification)
from starkware.cairo.apps.starkex2_0.execute_settlement import execute_settlement
from starkware.cairo.apps.starkex2_0.execute_transfer import execute_transfer

# Executes a batch of transactions (settlements, transfers, modifications).
func execute_batch(
        modification_ptr : ModificationOutput*, conditional_transfer_ptr : felt*,
        hash_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*,
        vault_dict : DictAccess*, order_dict : DictAccess*, dex_context_ptr : DexContext*) -> (
        modification_ptr : ModificationOutput*, conditional_transfer_ptr : felt*,
        hash_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*,
        vault_dict : DictAccess*, order_dict : DictAccess*):
    # Guess if the first transaction is a settlement.
    jmp handle_settlement if [ap] != 0; ap++

    # Guess if the first transaction is a transfer.
    jmp handle_transfer if [ap] != 0; ap++

    # Guess if the first transaction is a modification.
    jmp handle_modification if [ap] != 0; ap++

    # Otherwise, check that there are no other (undefined) transactions and return.
    return (
        modification_ptr=modification_ptr,
        conditional_transfer_ptr=conditional_transfer_ptr,
        hash_ptr=hash_ptr,
        range_check_ptr=range_check_ptr,
        ecdsa_ptr=ecdsa_ptr,
        vault_dict=vault_dict,
        order_dict=order_dict)

    handle_settlement:
    # Call execute_settlement.
    let settlement_res = execute_settlement(
        hash_ptr=hash_ptr,
        range_check_ptr=range_check_ptr,
        ecdsa_ptr=ecdsa_ptr,
        vault_dict=vault_dict,
        order_dict=order_dict,
        dex_context_ptr=dex_context_ptr)

    # Call execute_batch recursively.
    return execute_batch(
        modification_ptr=modification_ptr,
        conditional_transfer_ptr=conditional_transfer_ptr,
        hash_ptr=settlement_res.hash_ptr,
        range_check_ptr=settlement_res.range_check_ptr,
        ecdsa_ptr=settlement_res.ecdsa_ptr,
        vault_dict=settlement_res.vault_dict,
        order_dict=settlement_res.order_dict,
        dex_context_ptr=dex_context_ptr)

    handle_transfer:
    # Call execute_transfer.
    let transfer_res = execute_transfer(
        hash_ptr=hash_ptr,
        range_check_ptr=range_check_ptr,
        ecdsa_ptr=ecdsa_ptr,
        conditional_transfer_ptr=conditional_transfer_ptr,
        vault_dict=vault_dict,
        order_dict=order_dict,
        dex_context_ptr=dex_context_ptr)

    # Call execute_batch recursively.
    return execute_batch(
        modification_ptr=modification_ptr,
        conditional_transfer_ptr=transfer_res.conditional_transfer_ptr,
        hash_ptr=transfer_res.hash_ptr,
        range_check_ptr=transfer_res.range_check_ptr,
        ecdsa_ptr=transfer_res.ecdsa_ptr,
        vault_dict=transfer_res.vault_dict,
        order_dict=transfer_res.order_dict,
        dex_context_ptr=dex_context_ptr)

    handle_modification:
    # Guess if the first modification is a false full withdrawal.
    jmp handle_false_full_withdrawal if [ap] != 0; ap++

    # Call execute_modification.
    let (range_check_ptr, modification_ptr, vault_dict) = execute_modification(
        range_check_ptr=range_check_ptr,
        modification_ptr=modification_ptr,
        dex_context_ptr=dex_context_ptr,
        vault_dict=vault_dict)

    # Call execute_batch recursively.
    return execute_batch(
        modification_ptr=modification_ptr,
        conditional_transfer_ptr=conditional_transfer_ptr,
        hash_ptr=hash_ptr,
        range_check_ptr=range_check_ptr,
        ecdsa_ptr=ecdsa_ptr,
        vault_dict=vault_dict,
        order_dict=order_dict,
        dex_context_ptr=dex_context_ptr)

    handle_false_full_withdrawal:
    # Call execute_false_full_withdrawal.
    let (vault_dict, modification_ptr) = execute_false_full_withdrawal(
        modification_ptr=modification_ptr, dex_context_ptr=dex_context_ptr, vault_dict=vault_dict)

    # Call execute_batch recursively.
    # Make a copy of the first argument to avoid a compiler optimization that was added after the
    # code was deployed.
    [ap] = modification_ptr; ap++
    let modification_ptr = cast([ap - 1], ModificationOutput*)
    return execute_batch(
        modification_ptr=modification_ptr,
        conditional_transfer_ptr=conditional_transfer_ptr,
        hash_ptr=hash_ptr,
        range_check_ptr=range_check_ptr,
        ecdsa_ptr=ecdsa_ptr,
        vault_dict=vault_dict,
        order_dict=order_dict,
        dex_context_ptr=dex_context_ptr)
end
