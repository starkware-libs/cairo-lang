from typing import Dict, Iterable, List, Optional

import pytest

from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.starknet.compiler.validation_utils import verify_account_contract
from starkware.starknet.public import abi as starknet_abi


def create_mock_contract_abi(
    entry_point_names: Iterable[str],
    deform_entry_point_name: Optional[str] = None,
    inputs: List[Dict[str, str]] = [],
) -> starknet_abi.AbiType:
    mock_abi = [
        {
            "type": "function",
            "name": entry_point_name,
            "inputs": [{"name": "class_hash", "type": "felt"}],
        }
        for entry_point_name in entry_point_names
        if entry_point_name != deform_entry_point_name
    ]
    if deform_entry_point_name is not None:
        mock_abi.append(
            {
                "type": "function",
                "name": deform_entry_point_name,
                "inputs": inputs,
            }
        )
    return mock_abi


def test_positive_flow_verify_account_contract():
    # Account contract.
    mock_account_contract_abi = create_mock_contract_abi(
        entry_point_names=starknet_abi.ACCOUNT_ENTRY_POINT_NAMES
    )
    verify_account_contract(contract_abi=mock_account_contract_abi, is_account_contract=True)

    # Non-account contract.
    mock_account_contract_abi = create_mock_contract_abi(entry_point_names=["mock_entry_point"])
    verify_account_contract(contract_abi=mock_account_contract_abi, is_account_contract=False)


def test_negative_flow_verify_account_contract():
    """
    Test malformed account contracts ABI.
    """
    # Contract missing one or more of the account entry points:
    #   "__execute__", "__validate__", "__validate_declare__".
    mock_defected_account_contract_abi = create_mock_contract_abi(
        entry_point_names={
            starknet_abi.VALIDATE_ENTRY_POINT_NAME,
            starknet_abi.EXECUTE_ENTRY_POINT_NAME,
        }
    )
    with pytest.raises(
        PreprocessorError, match="Account contracts must have external functions named"
    ):
        verify_account_contract(
            contract_abi=mock_defected_account_contract_abi, is_account_contract=True
        )
    with pytest.raises(PreprocessorError, match="Only account contracts may have functions named"):
        verify_account_contract(
            contract_abi=mock_defected_account_contract_abi, is_account_contract=False
        )

    # Contract where "__declare__" and "__execute__" have different calldata.
    mock_defected_account_contract_abi = create_mock_contract_abi(
        entry_point_names=starknet_abi.ACCOUNT_ENTRY_POINT_NAMES,
        deform_entry_point_name=starknet_abi.EXECUTE_ENTRY_POINT_NAME,
        inputs=[
            {"name": "class_hash", "type": "felt"},
            {"name": "contract_address", "type": "felt"},
        ],
    )
    with pytest.raises(
        PreprocessorError, match="Account contracts must have the exact same calldata for"
    ):
        verify_account_contract(
            contract_abi=mock_defected_account_contract_abi, is_account_contract=True
        )

    # Contract where "__validate_declare__" have malformed calldata.
    mock_defected_account_contract_abi = create_mock_contract_abi(
        entry_point_names=starknet_abi.ACCOUNT_ENTRY_POINT_NAMES,
        deform_entry_point_name=starknet_abi.VALIDATE_DECLARE_ENTRY_POINT_NAME,
        inputs=[
            {"name": "class_hash", "type": "felt"},
            {"name": "contract_address", "type": "felt"},
        ],
    )
    with pytest.raises(
        PreprocessorError,
        match=f"'{starknet_abi.VALIDATE_DECLARE_ENTRY_POINT_NAME}' function must have one argument "
        "`class_hash: felt`.",
    ):
        verify_account_contract(
            contract_abi=mock_defected_account_contract_abi, is_account_contract=True
        )
