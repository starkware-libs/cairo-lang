import logging
from typing import List, Optional, Tuple, cast

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.starknet.core.os.transaction_hash import TransactionHashPrefix
from starkware.starknet.definitions import constants
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.public import abi as starknet_abi
from starkware.starknet.services.api.contract_definition import EntryPointType
from starkware.starkware_utils.error_handling import stark_assert, wrap_with_stark_exception

logger = logging.getLogger(__name__)


def get_return_values(runner: CairoFunctionRunner) -> List[int]:
    """
    Extracts the return values of a StarkNet contract function from the Cairo runner.
    """
    with wrap_with_stark_exception(
        code=StarknetErrorCode.INVALID_RETURN_DATA,
        message="Error extracting return data.",
        logger=logger,
        exception_types=[Exception],
    ):
        ret_data_size, ret_data_ptr = runner.get_return_values(2)
        values = runner.memory.get_range(ret_data_ptr, ret_data_size)

    stark_assert(
        all(isinstance(value, int) for value in values),
        code=StarknetErrorCode.INVALID_RETURN_DATA,
        message="Return data expected to be non-relocatable.",
    )

    return cast(List[int], values)


def preprocess_invoke_function_fields(
    entry_point_type: EntryPointType,
    entry_point_selector: int,
    message_from_l1_nonce: Optional[int],
    max_fee: int,
    version: int,
) -> Tuple[TransactionHashPrefix, List[int]]:
    """
    Performs validation on fields related to function invocation transaction.
    Deduces and returns entry point type-related fields required for hash calculation of
    InvokeFunction transaction.
    """
    # Validate version.
    assert (
        version == constants.TRANSACTION_VERSION
    ), f"Transaction version {version} is not supported."

    # Validate entry point type-related fields.
    if entry_point_type is EntryPointType.EXTERNAL:
        assert message_from_l1_nonce is None, "An InvokeFunction transaction cannot have a nonce."
        if max_fee != 0:
            stark_assert(
                entry_point_selector == starknet_abi.EXECUTE_ENTRY_POINT_SELECTOR,
                code=StarknetErrorCode.UNSUPPORTED_SELECTOR_FOR_FEE,
                message=(
                    "Transactions with positive fee should go through the "
                    f"{starknet_abi.EXECUTE_ENTRY_POINT_NAME} entrypoint."
                ),
            )

        tx_hash_prefix = TransactionHashPrefix.INVOKE
        additional_data = []
    elif entry_point_type is EntryPointType.L1_HANDLER:
        assert message_from_l1_nonce is not None, "An L1 handler transaction must have a nonce."
        assert max_fee == 0, "An L1 handler transaction must have max_fee=0."

        tx_hash_prefix = TransactionHashPrefix.L1_HANDLER
        additional_data = [message_from_l1_nonce]
    else:
        raise NotImplementedError(f"Entry point type {entry_point_type.name} is not supported.")

    return tx_hash_prefix, additional_data
