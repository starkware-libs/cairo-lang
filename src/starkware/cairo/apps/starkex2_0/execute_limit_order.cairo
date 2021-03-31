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

# Executes a limit order of a single party. Each settlement will invoke this function twice, once
# per each party.
# A limit order can be described by the following statement:
#   "I want to sell a maximum of amount_sell tokens of type token_sell, and in return I expect
#   to receive at least amount_buy tokens of type token_buy (relative to the actual number of tokens
#   sold)."
#
# The actual amounts that were transferred are amount_sold, amount_bought.
#
# sell_change and buy_change are DictAccess pointers into the vault_dict.
# They are given as two distinct pointers to allow the caller to control the order in which the
# vault updates are applied.
#
# Assumptions:
# * 0 <= amount_sold, amount_bought < BALANCE_BOUND.
# * 0 <= global_expiration_timestamp, and it has not expired yet.
func execute_limit_order(
        hash_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*,
        sell_change : DictAccess*, buy_change : DictAccess*, order_dict : DictAccess*, amount_sold,
        amount_bought, token_sell, token_buy, dex_context_ptr : DexContext*) -> (
        hash_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*,
        order_dict : DictAccess*):
    # Local variables.
    alloc_locals
    local amount_sell
    local amount_buy
    local vault_id_sell
    local vault_id_buy
    local stark_key
    local nonce
    local order_id
    local expiration_timestamp
    local prev_fulfilled_amount
    local new_fulfilled_amount

    let dex_context : DexContext* = dex_context_ptr

    # Define an inclusive amount bound reference for amount range-checks.
    tempvar inclusive_amount_bound = BALANCE_BOUND - 1

    # Check that 0 <= amount_sell < BALANCE_BOUND.
    assert [range_check_ptr] = amount_sell
    # Guarantee that amount_sell <= inclusive_amount_bound < BALANCE_BOUND.
    assert [range_check_ptr + 1] = inclusive_amount_bound - amount_sell

    # Check that 0 <= amount_buy < BALANCE_BOUND.
    assert [range_check_ptr + 2] = amount_buy
    # Guarantee that amount_buy <= inclusive_amount_bound < BALANCE_BOUND.
    assert [range_check_ptr + 3] = inclusive_amount_bound - amount_buy

    # Check that the party has not sold more than the sell amount limit specified in their order.
    new_fulfilled_amount = prev_fulfilled_amount + amount_sold
    # Guarantee that new_fulfilled_amount <= amount_sell, which also implies that
    # amount_sold <= amount_sell.
    assert [range_check_ptr + 4] = amount_sell - new_fulfilled_amount

    # Check that 0 <= nonce < NONCE_BOUND.
    tempvar inclusive_nonce_bound = NONCE_BOUND - 1
    assert [range_check_ptr + 5] = nonce
    # Guarantee that nonce <= inclusive_nonce_bound < NONCE_BOUND.
    assert [range_check_ptr + 6] = inclusive_nonce_bound - nonce

    # Check that the order has not expired yet.
    tempvar global_expiration_timestamp = dex_context.global_expiration_timestamp
    # Guarantee that global_expiration_timestamp <= expiration_timestamp, which also implies that
    # 0 <= expiration_timestamp.
    assert [range_check_ptr + 7] = expiration_timestamp - global_expiration_timestamp

    # Check that expiration_timestamp < EXPIRATION_TIMESTAMP_BOUND.
    tempvar inclusive_expiration_timestamp_bound = EXPIRATION_TIMESTAMP_BOUND - 1
    # Guarantee that expiration_timestamp <= inclusive_expiration_timestamp_bound <
    # EXPIRATION_TIMESTAMP_BOUND.
    assert [range_check_ptr + 8] = inclusive_expiration_timestamp_bound - expiration_timestamp

    # Check that the actual ratio (amount_bought / amount_sold) is better than (or equal to) the
    # requested ratio (amount_buy / amount_sell) by checking that
    # amount_sell * amount_bought >= amount_sold * amount_buy.
    assert [range_check_ptr + 9] = amount_sell * amount_bought - amount_sold * amount_buy

    # Update orders dict.
    let order_dict_access : DictAccess* = order_dict
    order_id = order_dict_access.key
    prev_fulfilled_amount = order_dict_access.prev_value
    new_fulfilled_amount = order_dict_access.new_value

    # Call vault_update for selling, to update the vault tree with the new balance of the sell
    # vault.
    let sell_vault_update_ret = vault_update_diff(
        range_check_ptr=range_check_ptr + 10,
        diff=amount_sold * (-1),
        stark_key=stark_key,
        token_id=token_sell,
        vault_index=vault_id_sell,
        vault_change_ptr=sell_change)

    # Call vault_update for buying, to update the vault tree with the new balance of the buy vault.
    # range_check_ptr is already in [ap - 1].
    let buy_vault_update_ret = vault_update_diff(
        range_check_ptr=sell_vault_update_ret.range_check_ptr,
        diff=amount_bought,
        stark_key=stark_key,
        token_id=token_buy,
        vault_index=vault_id_buy,
        vault_change_ptr=buy_change)

    let verify_order_signature_ret = verify_order_signature(
        hash_ptr=hash_ptr,
        range_check_ptr=buy_vault_update_ret.range_check_ptr,
        ecdsa_ptr=ecdsa_ptr,
        public_key=stark_key,
        order_type=PackedOrderMsg.SETTLEMENT_ORDER_TYPE,
        vault0=vault_id_sell,
        vault1=vault_id_buy,
        amount0=amount_sell,
        amount1=amount_buy,
        token0=token_sell,
        token1_or_pub_key=token_buy,
        nonce=nonce,
        expiration_timestamp=expiration_timestamp,
        order_id=order_id,
        condition=0)

    return (
        hash_ptr=verify_order_signature_ret.hash_ptr,
        range_check_ptr=verify_order_signature_ret.range_check_ptr,
        ecdsa_ptr=verify_order_signature_ret.ecdsa_ptr,
        order_dict=order_dict + DictAccess.SIZE)
end
