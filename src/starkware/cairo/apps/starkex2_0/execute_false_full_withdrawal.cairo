# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

from starkware.cairo.apps.starkex2_0.common.dict import DictAccess
from starkware.cairo.apps.starkex2_0.dex_constants import BALANCE_BOUND
from starkware.cairo.apps.starkex2_0.dex_context import DexContext
from starkware.cairo.apps.starkex2_0.execute_modification import (
    ModificationConstants, ModificationOutput)
from starkware.cairo.apps.starkex2_0.vault_update import vault_update_balances

# Executes a false full withdrawal.
# Validates that the guessed requester_stark_key is not the same as the stark key in the vault
# and writes the requester_stark_key to the program output.
# Assumptions: keys in the vault_dict are range-checked to be < VAULT_SHIFT.
func execute_false_full_withdrawal(
        modification_ptr : ModificationOutput*, dex_context_ptr : DexContext*,
        vault_dict : DictAccess*) -> (
        vault_dict : DictAccess*, modification_ptr : ModificationOutput*):
    let dex_context : DexContext* = dex_context_ptr
    let output : ModificationOutput* = modification_ptr

    const FULL_WITHDRAWAL_SHIFT = ModificationConstants.FULL_WITHDRAWAL_SHIFT
    const BALANCE_SHIFT = ModificationConstants.BALANCE_SHIFT

    alloc_locals
    local stark_key
    local balance_before
    local token_id
    local vault_index

    assert output.token_id = 0

    # Note that we assume vault_index is range-checked during the merkle_multi_update,
    # which will force the full withdrawal bit to be 1.
    assert output.action = vault_index * BALANCE_SHIFT + BALANCE_BOUND + FULL_WITHDRAWAL_SHIFT

    # In false full withdrawal balance_before must be equal to balance_after.
    vault_update_balances(
        balance_before=balance_before,
        balance_after=balance_before,
        stark_key=stark_key,
        token_id=token_id,
        vault_index=vault_index,
        vault_change_ptr=vault_dict)

    # Guess the requester_stark_key, write it to the output and make sure it's not the same as the
    # stark_key.
    let requester_stark_key = output.stark_key
    tempvar key_diff = requester_stark_key - stark_key
    if key_diff == 0:
        # Add an unsatisfiable assertion when key_diff == 0.
        key_diff = 1
    end

    return (
        vault_dict=vault_dict + DictAccess.SIZE,
        modification_ptr=modification_ptr + ModificationOutput.SIZE)
end
