from typing import List

import pytest

from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.crypto.signature.fast_pedersen_hash import pedersen_hash
from starkware.starknet.services.api.gateway.transaction_hash import (
    TransactionHashPrefix,
    calculate_deploy_transaction_hash,
    calculate_transaction_hash_common,
)


@pytest.mark.parametrize("tx_hash_prefix", set(TransactionHashPrefix))
@pytest.mark.parametrize("calldata", [[], [659], [540, 338], [73, 443, 234, 350, 841]])
@pytest.mark.parametrize("additional_data", [[], [17]])
def test_transaction_hash_common_flow(
    tx_hash_prefix: TransactionHashPrefix, calldata: List[int], additional_data: List[int]
):
    contract_address = 42
    entry_point_selector = 100
    chain_id = 1

    expected_tx_hash = compute_hash_on_elements(
        data=[
            tx_hash_prefix.value,
            contract_address,
            entry_point_selector,
            compute_hash_on_elements(data=calldata, hash_func=pedersen_hash),
            chain_id,
            *additional_data,
        ],
        hash_func=pedersen_hash,
    )
    assert expected_tx_hash == calculate_transaction_hash_common(
        tx_hash_prefix=tx_hash_prefix,
        contract_address=contract_address,
        entry_point_selector=entry_point_selector,
        calldata=calldata,
        chain_id=chain_id,
        hash_function=pedersen_hash,
        additional_data=additional_data,
    )


def test_deploy_transaction_hash():
    expected_hash = 0x334E744938EE65F038037AD1CC85D949A3554D5CF6508471BB00B0AD91B483
    assert (
        calculate_deploy_transaction_hash(
            contract_address=1,
            constructor_calldata=[1, 2],
            chain_id=1,
        )
        == expected_hash
    )
