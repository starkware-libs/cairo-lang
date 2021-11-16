from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.crypto.signature.fast_pedersen_hash import pedersen_hash
from starkware.starknet.business_logic.test_utils import build_contract_definition
from starkware.starknet.core.os.contract_hash import compute_contract_hash
from starkware.starknet.services.api.gateway.contract_address import (
    CONTRACT_ADDRESS_PREFIX,
    calculate_contract_address,
)


def test_calculate_contract_address():
    contract_definition = build_contract_definition(program_data=[10, 20, 30, 40, 50])
    constructor_calldata = [60, 70, DEFAULT_PRIME - 1]
    caller_address = 0
    salt = 1337

    actual_address = calculate_contract_address(
        salt=salt,
        contract_definition=contract_definition,
        constructor_calldata=constructor_calldata,
        caller_address=caller_address,
        hash_function=pedersen_hash,
    )

    contract_hash = compute_contract_hash(
        contract_definition=contract_definition, hash_func=pedersen_hash
    )
    constructor_calldata_hash = compute_hash_on_elements(
        data=constructor_calldata, hash_func=pedersen_hash
    )
    expected_address = compute_hash_on_elements(
        data=[
            CONTRACT_ADDRESS_PREFIX,
            caller_address,
            salt,
            contract_hash,
            constructor_calldata_hash,
        ],
        hash_func=pedersen_hash,
    )
    assert actual_address == expected_address
