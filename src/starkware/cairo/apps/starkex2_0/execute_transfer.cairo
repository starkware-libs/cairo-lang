# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

from starkware.cairo.apps.starkex2_0.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.apps.starkex2_0.common.dict import DictAccess
from starkware.cairo.apps.starkex2_0.common.merkle_update import merkle_update
from starkware.cairo.apps.starkex2_0.dex_constants import (
    BALANCE_BOUND, EXPIRATION_TIMESTAMP_BOUND, NONCE_BOUND, PackedOrderMsg)
from starkware.cairo.apps.starkex2_0.dex_context import DexContext
from starkware.cairo.apps.starkex2_0.vault_update import vault_update_diff
from starkware.cairo.apps.starkex2_0.verify_order_signature import verify_order_signature

# Executes a (conditional) transfer order.
# A (conditional) transfer order can be described by the following statement:
#   "I want to transfer exactly 'amount' tokens of type 'token' to user 'receiver_stark_key'
#   in vault 'target_vault' (only if the specified 'condition' is satisfied)".
#
# Assumptions:
# * 0 <= global_expiration_timestamp, and it has not expired yet.
func execute_transfer(
        hash_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*,
        conditional_transfer_ptr : felt*, vault_dict : DictAccess*, order_dict : DictAccess*,
        dex_context_ptr : DexContext*) -> (
        hash_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*,
        conditional_transfer_ptr : felt*, vault_dict : DictAccess*, order_dict : DictAccess*):
    # Local variables.
    alloc_locals
    local amount
    local token_id
    local sender_vault_id
    local receiver_vault_id
    local sender_stark_key
    local receiver_stark_key
    local nonce
    local order_id
    local expiration_timestamp
    local order_type
    local condition
    local new_conditional_transfer_pointer : felt*

    let dex_context : DexContext* = dex_context_ptr

    # Check that 0 <= amount < BALANCE_BOUND.
    tempvar inclusive_amount_bound = BALANCE_BOUND - 1
    assert [range_check_ptr] = amount
    # Guarantee that amount <= inclusive_amount_bound < BALANCE_BOUND.
    assert [range_check_ptr + 1] = inclusive_amount_bound - amount

    # Check that 0 <= nonce < NONCE_BOUND.
    tempvar inclusive_nonce_bound = NONCE_BOUND - 1
    assert [range_check_ptr + 2] = nonce
    # Guarantee that nonce <= inclusive_nonce_bound < NONCE_BOUND.
    assert [range_check_ptr + 3] = inclusive_nonce_bound - nonce

    # Check that the order has not expired yet.
    tempvar global_expiration_timestamp = dex_context.global_expiration_timestamp
    # Guarantee that global_expiration_timestamp <= expiration_timestamp, which also implies that
    # 0 <= expiration_timestamp.
    assert [range_check_ptr + 4] = expiration_timestamp - global_expiration_timestamp

    # Check that expiration_timestamp < EXPIRATION_TIMESTAMP_BOUND.
    tempvar inclusive_expiration_timestamp_bound = EXPIRATION_TIMESTAMP_BOUND - 1
    # Guarantee that expiration_timestamp <= inclusive_expiration_timestamp_bound <
    # EXPIRATION_TIMESTAMP_BOUND.
    assert [range_check_ptr + 5] = inclusive_expiration_timestamp_bound - expiration_timestamp

    # Call vault_update for the sender.
    let sender_vault_update_ret = vault_update_diff(
        range_check_ptr=range_check_ptr + 6,
        diff=amount * (-1),
        stark_key=sender_stark_key,
        token_id=token_id,
        vault_index=sender_vault_id,
        vault_change_ptr=vault_dict)

    # Call vault_update for the receiver.
    # Make a copy of the first argument to avoid a compiler optimization that was added after the
    # code was deployed.
    [ap] = sender_vault_update_ret.range_check_ptr; ap++
    let range_check_ptr = [ap - 1]
    let receiver_vault_update_ret = vault_update_diff(
        range_check_ptr=range_check_ptr,
        diff=amount,
        stark_key=receiver_stark_key,
        token_id=token_id,
        vault_index=receiver_vault_id,
        vault_change_ptr=vault_dict + DictAccess.SIZE)

    local range_check_ptr_after_vault_update = receiver_vault_update_ret.range_check_ptr

    # Assert that the correct order_type is given for transfer (condition == 0) and
    # conditional transfer (condition != 0).

    if condition != 0:
        # Conditional transfer.
        order_type = PackedOrderMsg.CONDITIONAL_TRANSFER_ORDER_TYPE
        [conditional_transfer_ptr] = condition
        new_conditional_transfer_pointer = conditional_transfer_ptr + 1
    else:
        # Normal transfer.
        order_type = PackedOrderMsg.TRANSFER_ORDER_TYPE
        new_conditional_transfer_pointer = conditional_transfer_ptr
    end

    let verify_order_signature_ret = verify_order_signature(
        hash_ptr=hash_ptr,
        range_check_ptr=range_check_ptr_after_vault_update,
        ecdsa_ptr=ecdsa_ptr,
        public_key=sender_stark_key,
        order_type=order_type,
        vault0=sender_vault_id,
        vault1=receiver_vault_id,
        amount0=amount,
        amount1=0,
        token0=token_id,
        token1_or_pub_key=receiver_stark_key,
        nonce=nonce,
        expiration_timestamp=expiration_timestamp,
        order_id=order_id,
        condition=condition)

    # Update orders dict.
    let order_dict_access : DictAccess* = order_dict
    order_id = order_dict_access.key
    tempvar zero = 0
    zero = order_dict_access.prev_value
    amount = order_dict_access.new_value

    return (
        hash_ptr=verify_order_signature_ret.hash_ptr,
        range_check_ptr=verify_order_signature_ret.range_check_ptr,
        ecdsa_ptr=verify_order_signature_ret.ecdsa_ptr,
        conditional_transfer_ptr=new_conditional_transfer_pointer,
        vault_dict=vault_dict + 2 * DictAccess.SIZE,
        order_dict=order_dict + DictAccess.SIZE)
end
