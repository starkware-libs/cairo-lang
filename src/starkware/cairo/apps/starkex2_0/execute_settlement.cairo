# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

from starkware.cairo.apps.starkex2_0.common.cairo_builtins import HashBuiltin, SignatureBuiltin
from starkware.cairo.apps.starkex2_0.common.dict import DictAccess
from starkware.cairo.apps.starkex2_0.dex_constants import BALANCE_BOUND
from starkware.cairo.apps.starkex2_0.dex_context import DexContext
from starkware.cairo.apps.starkex2_0.execute_limit_order import execute_limit_order

# Executes a settlement between two parties, where each party signed an appropriate limit order
# and those orders match.
func execute_settlement(
        hash_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*,
        vault_dict : DictAccess*, order_dict : DictAccess*, dex_context_ptr : DexContext*) -> (
        hash_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr : SignatureBuiltin*,
        vault_dict : DictAccess*, order_dict : DictAccess*):
    # Local variables.
    alloc_locals
    local party_a_sold
    local party_b_sold
    local token_a  # Token sold by party a, and bought by party b.
    local token_b  # Token sold by party b, and bought by party a.

    # Define an inclusive amount bound reference for amount range-checks.
    tempvar inclusive_amount_bound = BALANCE_BOUND - 1

    # Check that 0 <= party_a_sold < BALANCE_BOUND.
    assert [range_check_ptr] = party_a_sold
    # Guarantee that party_a_sold <= inclusive_amount_bound < BALANCE_BOUND.
    assert [range_check_ptr + 1] = inclusive_amount_bound - party_a_sold

    # Check that 0 <= party_b_sold < BALANCE_BOUND.
    assert [range_check_ptr + 2] = party_b_sold
    # Guarantee that party_b_sold <= inclusive_amount_bound < BALANCE_BOUND.
    assert [range_check_ptr + 3] = inclusive_amount_bound - party_b_sold

    # Call execute_limit_order for party a:
    let return0 = execute_limit_order(
        hash_ptr=hash_ptr,
        range_check_ptr=range_check_ptr + 4,
        ecdsa_ptr=ecdsa_ptr,
        sell_change=vault_dict,
        buy_change=vault_dict + 3 * DictAccess.SIZE,
        order_dict=order_dict,
        amount_sold=party_a_sold,
        amount_bought=party_b_sold,
        token_sell=token_a,
        token_buy=token_b,
        dex_context_ptr=dex_context_ptr)

    # Call execute_limit_order for party b.
    let return1 = execute_limit_order(
        hash_ptr=return0.hash_ptr,
        range_check_ptr=return0.range_check_ptr,
        ecdsa_ptr=return0.ecdsa_ptr,
        sell_change=vault_dict + 2 * DictAccess.SIZE,
        buy_change=vault_dict + 1 * DictAccess.SIZE,
        order_dict=return0.order_dict,
        amount_sold=party_b_sold,
        amount_bought=party_a_sold,
        token_sell=token_b,
        token_buy=token_a,
        dex_context_ptr=dex_context_ptr)

    return (
        hash_ptr=return1.hash_ptr,
        range_check_ptr=return1.range_check_ptr,
        ecdsa_ptr=return1.ecdsa_ptr,
        vault_dict=vault_dict + 4 * DictAccess.SIZE,
        order_dict=return1.order_dict)
end
