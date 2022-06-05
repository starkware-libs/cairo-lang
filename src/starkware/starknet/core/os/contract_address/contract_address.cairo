from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.hash_state import (
    hash_finalize,
    hash_init,
    hash_update,
    hash_update_single,
    hash_update_with_hashchain,
)

const CONTRACT_ADDRESS_PREFIX = 'STARKNET_CONTRACT_ADDRESS'

func get_contract_address{hash_ptr : HashBuiltin*}(
    salt : felt,
    class_hash : felt,
    constructor_calldata_size : felt,
    constructor_calldata : felt*,
    deployer_address : felt,
) -> (contract_address : felt):
    let (hash_state_ptr) = hash_init()
    let (hash_state_ptr) = hash_update_single(
        hash_state_ptr=hash_state_ptr, item=CONTRACT_ADDRESS_PREFIX
    )
    let (hash_state_ptr) = hash_update_single(hash_state_ptr=hash_state_ptr, item=deployer_address)
    let (hash_state_ptr) = hash_update_single(hash_state_ptr=hash_state_ptr, item=salt)
    let (hash_state_ptr) = hash_update_single(hash_state_ptr=hash_state_ptr, item=class_hash)
    let (hash_state_ptr) = hash_update_with_hashchain(
        hash_state_ptr=hash_state_ptr,
        data_ptr=constructor_calldata,
        data_length=constructor_calldata_size,
    )
    let (contract_address) = hash_finalize(hash_state_ptr=hash_state_ptr)

    return (contract_address=contract_address)
end
