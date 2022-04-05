import math
from typing import Mapping

from starkware.starknet.business_logic.execution.execute_entry_point import ExecuteEntryPoint
from starkware.starknet.business_logic.execution.objects import (
    CallInfo,
    TransactionExecutionContext,
)
from starkware.starknet.business_logic.state.state import CarriedState
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.public import abi as starknet_abi
from starkware.starknet.services.api.contract_definition import EntryPointType
from starkware.starkware_utils.error_handling import StarkException, stark_assert_le


async def charge_fee(
    general_config: StarknetGeneralConfig,
    state: CarriedState,
    account_contract_address: int,
    actual_fee: int,
    max_fee: int,
) -> CallInfo:
    """
    Transfers the amount actual_fee from the caller account to the sequencer.
    Returns the resulting CallInfo of the transfer call.
    """
    stark_assert_le(
        actual_fee,
        max_fee,
        code=StarknetErrorCode.FEE_TRANSFER_FAILURE,
        message="Actual fee exceeded max fee.",
    )

    tx_execution_context = TransactionExecutionContext.create_for_call(
        account_contract_address=account_contract_address,
        n_steps=general_config.invoke_tx_max_n_steps,
    )

    fee_token_address = general_config.fee_token_address
    fee_transfer_call = ExecuteEntryPoint(
        caller_address=account_contract_address,  # The account contract address.
        contract_address=fee_token_address,
        code_address=fee_token_address,
        entry_point_selector=starknet_abi.TRANSFER_ENTRY_POINT_SELECTOR,
        entry_point_type=EntryPointType.EXTERNAL,
        calldata=[general_config.sequencer_address, actual_fee, 0],  # Recipient, amount (128-bit).
    )
    try:
        fee_transfer_info = await fee_transfer_call.execute(
            state=state, general_config=general_config, tx_execution_context=tx_execution_context
        )
    except StarkException as exception:
        raise StarkException(code=StarknetErrorCode.FEE_TRANSFER_FAILURE, message=str(exception))

    return fee_transfer_info


def calculate_tx_fee_by_cairo_usage(
    general_config: StarknetGeneralConfig,
    cairo_resource_usage: Mapping[str, int],
    l1_gas_usage: int,
    gas_price: int,
) -> int:
    """
    Calculates the transaction fee by considering the heaviest Cairo resource (in terms of L1 gas),
    as the size of a proof is determined similarly - by the (normalized) largest segment.
    We add to that the given l1_gas_usage (which may include, for example, the direct cost of
    L2-to-L1 messages) and multiply by the L1 gas price.
    """
    cairo_resource_fee_weights = general_config.cairo_resource_fee_weights
    cairo_resource_names = set(cairo_resource_usage.keys())
    assert cairo_resource_names.issubset(
        cairo_resource_fee_weights.keys()
    ), "Cairo resource names must be contained in fee weights dict."

    # Convert Cairo usage to L1 gas usage.
    cairo_l1_gas_usage = max(
        cairo_resource_fee_weights[key] * cairo_resource_usage.get(key, 0)
        for key in cairo_resource_fee_weights
    )

    total_l1_gas_usage = cairo_l1_gas_usage + l1_gas_usage
    return math.ceil(total_l1_gas_usage * gas_price)
