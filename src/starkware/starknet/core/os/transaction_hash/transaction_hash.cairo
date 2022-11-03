from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.hash_state import (
    hash_finalize,
    hash_init,
    hash_update,
    hash_update_single,
    hash_update_with_hashchain,
)

func get_transaction_hash{hash_ptr: HashBuiltin*}(
    tx_hash_prefix: felt,
    version: felt,
    contract_address: felt,
    entry_point_selector: felt,
    calldata_size: felt,
    calldata: felt*,
    max_fee: felt,
    chain_id: felt,
    additional_data_size: felt,
    additional_data: felt*,
) -> (tx_hash: felt) {
    let (hash_state_ptr) = hash_init();
    let (hash_state_ptr) = hash_update_single(hash_state_ptr=hash_state_ptr, item=tx_hash_prefix);
    let (hash_state_ptr) = hash_update_single(hash_state_ptr=hash_state_ptr, item=version);
    let (hash_state_ptr) = hash_update_single(hash_state_ptr=hash_state_ptr, item=contract_address);
    let (hash_state_ptr) = hash_update_single(
        hash_state_ptr=hash_state_ptr, item=entry_point_selector
    );
    let (hash_state_ptr) = hash_update_with_hashchain(
        hash_state_ptr=hash_state_ptr, data_ptr=calldata, data_length=calldata_size
    );
    let (hash_state_ptr) = hash_update_single(hash_state_ptr=hash_state_ptr, item=max_fee);
    let (hash_state_ptr) = hash_update_single(hash_state_ptr=hash_state_ptr, item=chain_id);

    let (hash_state_ptr) = hash_update(
        hash_state_ptr=hash_state_ptr, data_ptr=additional_data, data_length=additional_data_size
    );

    let (tx_hash) = hash_finalize(hash_state_ptr=hash_state_ptr);

    return (tx_hash=tx_hash);
}
