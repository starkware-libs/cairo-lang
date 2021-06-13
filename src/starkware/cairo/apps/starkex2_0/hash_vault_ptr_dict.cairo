# ***********************************************************************
# * This code is licensed under the Cairo Program License.              *
# * The license can be found in: licenses/CairoProgramLicense.txt       *
# ***********************************************************************

from starkware.cairo.apps.starkex2_0.common.cairo_builtins import HashBuiltin
from starkware.cairo.apps.starkex2_0.common.dict import DictAccess
from starkware.cairo.apps.starkex2_0.vault_update import VaultState, compute_vault_hash

# Gets a single pointer to a vault state and outputs the hash of that vault.
func hash_vault_state_ptr(hash_ptr : HashBuiltin*, vault_state_ptr : VaultState*) -> (
        vault_hash, hash_ptr : HashBuiltin*):
    let hash_builtin : HashBuiltin* = hash_ptr
    let vault_state : VaultState* = vault_state_ptr

    assert hash_builtin.x = vault_state.stark_key
    assert hash_builtin.y = vault_state.token_id

    # Compute new hash.
    return compute_vault_hash(
        hash_ptr=hash_ptr + HashBuiltin.SIZE,
        key_token_hash=hash_builtin.result,
        amount=vault_state.balance)
end

# Takes a vault_ptr_dict with pointers to vault states and writes a new vault_hash_dict with
# hashed vaults instead of pointers.
# The size of the vault_hash_dict is the same as the original dict and the DictAccess keys are
# copied as is.
func hash_vault_ptr_dict(
        hash_ptr : HashBuiltin*, vault_ptr_dict : DictAccess*, n_entries,
        vault_hash_dict : DictAccess*) -> (hash_ptr : HashBuiltin*):
    if n_entries == 0:
        return (hash_ptr=hash_ptr)
    end

    let hash_builtin : HashBuiltin* = hash_ptr
    let vault_access : DictAccess* = vault_ptr_dict
    let hashed_vault_access : DictAccess* = vault_hash_dict

    # Copy the key.
    assert hashed_vault_access.key = vault_access.key
    let prev_hash_res = hash_vault_state_ptr(
        hash_ptr=hash_ptr, vault_state_ptr=cast(vault_access.prev_value, VaultState*))
    hashed_vault_access.prev_value = prev_hash_res.vault_hash

    # Make a copy of the first argument to avoid a compiler optimization that was added after the
    # code was deployed.
    [ap] = prev_hash_res.hash_ptr; ap++
    let hash_ptr = cast([ap - 1], HashBuiltin*)
    let new_hash_res = hash_vault_state_ptr(
        hash_ptr=hash_ptr, vault_state_ptr=cast(vault_access.new_value, VaultState*))
    hashed_vault_access.new_value = new_hash_res.vault_hash

    # Tail call.
    # Make a copy of the first argument to avoid a compiler optimization that was added after the
    # code was deployed.
    [ap] = new_hash_res.hash_ptr; ap++
    let hash_ptr = cast([ap - 1], HashBuiltin*)
    return hash_vault_ptr_dict(
        hash_ptr=hash_ptr,
        vault_ptr_dict=vault_ptr_dict + DictAccess.SIZE,
        n_entries=n_entries - 1,
        vault_hash_dict=vault_hash_dict + DictAccess.SIZE)
end
