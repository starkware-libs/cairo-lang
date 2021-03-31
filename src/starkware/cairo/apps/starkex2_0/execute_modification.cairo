# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

from starkware.cairo.apps.starkex2_0.common.dict import DictAccess
from starkware.cairo.apps.starkex2_0.dex_constants import BALANCE_BOUND
from starkware.cairo.apps.starkex2_0.dex_context import DexContext
from starkware.cairo.apps.starkex2_0.vault_update import vault_update_balances

namespace ModificationConstants:
    const BALANCE_SHIFT = %[ 2**64 %]
    const VAULT_SHIFT = %[ 2**31 %]
    const FULL_WITHDRAWAL_SHIFT = BALANCE_SHIFT * VAULT_SHIFT
end

# Represents the struct of data written to the program output for each modification.
struct ModificationOutput:
    # The stark_key of the changed vault.
    member stark_key : felt
    # The token_id of the token which was deposited or withdrawn.
    member token_id : felt
    # A packed field which consists of the balances and vault_id.
    # The format is as follows:
    # +--------------------+------------------+----------------LSB-+
    # | full_withdraw (1b) |  vault_idx (31b) | balance_diff (64b) |
    # +--------------------+------------------+--------------------+
    # where balance_diff is represented using a 2**63 biased-notation.
    member action : felt
end

# Executes a modification (deposit or withdrawal) which changes the balance in a single vault
# and writes the details of that change to the program output, so that the inverse operation
# may be performed by the solidity contract on the on-chain deposit/withdrawal vaults.
func execute_modification(
        range_check_ptr, modification_ptr : ModificationOutput*, dex_context_ptr : DexContext*,
        vault_dict : DictAccess*) -> (
        range_check_ptr, modification_ptr : ModificationOutput*, vault_dict : DictAccess*):
    # Local variables.
    alloc_locals
    local balance_before
    local balance_after
    local vault_index
    local is_full_withdrawal

    let dex_context : DexContext* = dex_context_ptr
    let output : ModificationOutput* = modification_ptr

    # Copy constants to allow overriding them in the tests.
    const BALANCE_SHIFT = ModificationConstants.BALANCE_SHIFT
    const VAULT_SHIFT = ModificationConstants.VAULT_SHIFT

    # Perform range checks on balance_before, balance_after and vault_index to make sure
    # their values are valid, and that they do not overlap in the modification action field.
    tempvar inclusive_balance_bound = BALANCE_BOUND - 1

    # Check that 0 <= balance_before < BALANCE_BOUND.
    assert [range_check_ptr] = balance_before
    # Guarantee that balance_before <= inclusive_balance_bound < BALANCE_BOUND.
    assert [range_check_ptr + 1] = inclusive_balance_bound - balance_before

    # Check that 0 <= balance_after < BALANCE_BOUND.
    assert [range_check_ptr + 2] = balance_after
    # Guarantee that balance_after <= inclusive_balance_bound < BALANCE_BOUND.
    assert [range_check_ptr + 3] = inclusive_balance_bound - balance_after

    # Note: This range-check is redundant as it is also checked in vault_update_balances.
    # We keep it here for consistency with the other fields and to avoid the unnecessary dependency
    # on the guarantees of vault_update_balances().
    assert [range_check_ptr + 4] = vault_index
    # Guarantee that vault_index < VAULT_SHIFT.
    assert [range_check_ptr + 5] = (VAULT_SHIFT - 1) - vault_index

    # Assert that is_full_withdrawal is a bit.
    is_full_withdrawal = is_full_withdrawal * is_full_withdrawal

    # If is_full_withdrawal is set, balance_after must be 0.
    assert is_full_withdrawal * balance_after = 0

    # balance_before and balance_after were range checked and are guaranteed to be in the range
    # [0, BALANCE_BOUND) => diff is in the range (-BALANCE_BOUND, BALANCE_BOUND)
    # => biased_diff is in the range [1, 2*BALANCE_BOUND).
    tempvar diff = balance_after - balance_before
    tempvar biased_diff = diff + BALANCE_BOUND
    assert output.action = ((is_full_withdrawal * VAULT_SHIFT) + vault_index) * BALANCE_SHIFT +
        biased_diff

    vault_update_balances(
        balance_before=balance_before,
        balance_after=balance_after,
        stark_key=output.stark_key,
        token_id=output.token_id,
        vault_index=vault_index,
        vault_change_ptr=vault_dict)

    return (
        range_check_ptr=range_check_ptr + 6,
        modification_ptr=modification_ptr + ModificationOutput.SIZE,
        vault_dict=vault_dict + DictAccess.SIZE)
end
