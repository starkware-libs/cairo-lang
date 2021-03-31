# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

from starkware.cairo.apps.starkex2_0.common.cairo_builtins import HashBuiltin
from starkware.cairo.apps.starkex2_0.common.dict import DictAccess
from starkware.cairo.apps.starkex2_0.common.merkle_update import merkle_update
from starkware.cairo.apps.starkex2_0.dex_constants import BALANCE_BOUND, ZERO_VAULT_HASH

struct VaultState:
    member stark_key : felt
    member token_id : felt
    member balance : felt
end

# Retrieves a pointer to a VaultState with the corresponding vault.
# Returns an empty vault if balance == 0 (stark_key and token_id are ignored).
func get_vault_state(stark_key, token_id, balance) -> (vault_state_ptr : VaultState*):
    let vault_state_ptr = cast([fp], VaultState*)
    let vault_state_ap_ptr = cast([ap], VaultState*)

    # Allocate 1 slot for our local which is also the return value.
    vault_state_ptr.balance = balance; ap++

    if balance == 0:
        # Balance is 0 here, use it for initialization.
        let zero = balance
        vault_state_ptr.stark_key = zero
        vault_state_ptr.token_id = zero
        return (vault_state_ptr=vault_state_ap_ptr)
    end

    vault_state_ptr.stark_key = stark_key
    vault_state_ptr.token_id = token_id
    return (vault_state_ptr=vault_state_ap_ptr)
end

# Computes the hash h(key_token_hash, amount), where key_token_hash := h(stark_key, token_id).
func compute_vault_hash(hash_ptr : HashBuiltin*, key_token_hash, amount) -> (
        vault_hash, hash_ptr : HashBuiltin*):
    if amount == 0:
        return (vault_hash=ZERO_VAULT_HASH, hash_ptr=hash_ptr)
    end

    key_token_hash = hash_ptr.x
    amount = hash_ptr.y
    return (vault_hash=hash_ptr.result, hash_ptr=hash_ptr + HashBuiltin.SIZE)
end

# Updates the balance in the vault (leaf in the vault tree) corresponding to vault_index,
# by writing the change to vault_change_ptr.
# May also by used to verify the values in a certain vault.
func vault_update_balances(
        balance_before, balance_after, stark_key, token_id, vault_index,
        vault_change_ptr : DictAccess*):
    let vault_access : DictAccess* = vault_change_ptr
    vault_access.key = vault_index
    let (prev_vault_state_ptr) = get_vault_state(
        stark_key=stark_key, token_id=token_id, balance=balance_before)
    vault_access.prev_value = prev_vault_state_ptr
    let (new_vault_state_ptr) = get_vault_state(
        stark_key=stark_key, token_id=token_id, balance=balance_after)
    vault_access.new_value = new_vault_state_ptr
    return ()
end

# Similar to vault_update_balances, except that the expected difference
# (balance_after - balance_before) is given and a range-check is performed on balance_after.
func vault_update_diff(
        range_check_ptr, diff, stark_key, token_id, vault_index,
        vault_change_ptr : DictAccess*) -> (range_check_ptr):
    # Local variables.
    alloc_locals
    local balance_before
    local balance_after

    balance_after = balance_before + diff

    # Check that 0 <= balance_after < BALANCE_BOUND.
    assert [range_check_ptr] = balance_after
    # Apply the range check builtin on (BALANCE_BOUND - 1 - balance_after), which guarantees that
    # balance_after < BALANCE_BOUND.
    assert [range_check_ptr + 1] = (BALANCE_BOUND - 1) - balance_after

    # Call vault_update_balances.
    vault_update_balances(
        balance_before=balance_before,
        balance_after=balance_after,
        stark_key=stark_key,
        token_id=token_id,
        vault_index=vault_index,
        vault_change_ptr=vault_change_ptr)

    return (range_check_ptr=range_check_ptr + 2)
end
