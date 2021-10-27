from typing import List

import pytest

from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.crypto.signature.fast_pedersen_hash import pedersen_hash
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.services.api.gateway.transaction_hash import (
    calculate_transaction_hash,
    get_tx_hash_prefix,
)


@pytest.mark.parametrize("tx_type", list(TransactionType))
@pytest.mark.parametrize("calldata", [[], [659], [540, 338], [73, 443, 234, 350, 841]])
def test_transaction_hash(tx_type: TransactionType, calldata: List[int]):
    contract_address = 42
    entry_point_selector = 100
    chain_id = 1

    expected_tx_hash = compute_hash_on_elements(
        data=[
            get_tx_hash_prefix(tx_type=tx_type),
            contract_address,
            entry_point_selector,
            compute_hash_on_elements(data=calldata, hash_func=pedersen_hash),
            chain_id,
        ],
        hash_func=pedersen_hash,
    )
    assert expected_tx_hash == calculate_transaction_hash(
        tx_type=tx_type,
        contract_address=contract_address,
        entry_point_selector=entry_point_selector,
        calldata=calldata,
        chain_id=chain_id,
        hash_function=pedersen_hash,
    )
