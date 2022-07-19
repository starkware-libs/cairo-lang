import logging
from typing import List, Mapping, Optional, Tuple, cast

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.starknet.business_logic.execution.gas_usage import calculate_tx_gas_usage
from starkware.starknet.business_logic.execution.objects import CallInfo
from starkware.starknet.business_logic.execution.os_usage import (
    calculate_execute_txs_inner_resources,
    calculate_syscall_resources,
    get_tx_syscall_counter,
)
from starkware.starknet.business_logic.state.objects import ContractClassFact
from starkware.starknet.business_logic.state.state import CarriedState
from starkware.starknet.core.os.transaction_hash.transaction_hash import TransactionHashPrefix
from starkware.starknet.definitions import constants
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.public import abi as starknet_abi
from starkware.starknet.services.api.contract_class import ContractClass, EntryPointType
from starkware.starkware_utils.error_handling import stark_assert, wrap_with_stark_exception
from starkware.storage.storage import FactFetchingContext, Storage

logger = logging.getLogger(__name__)

FEE_TRANSFER_N_STORAGE_CHANGES = 2  # Sender and sequencer balance update.
# Exclude the sequencer balance update, since it's charged once throughout the batch.
FEE_TRANSFER_N_STORAGE_CHANGES_TO_CHARGE = FEE_TRANSFER_N_STORAGE_CHANGES - 1


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


def validate_version(version: int, only_query: bool):
    allowed_versions = [constants.TRANSACTION_VERSION]
    if only_query:
        error_code = StarknetErrorCode.INVALID_TRANSACTION_QUERYING_VERSION
        allowed_versions += [constants.QUERY_VERSION_BASE + v for v in allowed_versions]
    else:
        error_code = StarknetErrorCode.INVALID_TRANSACTION_VERSION

    stark_assert(
        version in allowed_versions,
        code=error_code,
        message=(
            f"Transaction version {version} is not supported. "
            f"Supported versions: {allowed_versions}."
        ),
    )


def preprocess_invoke_function_fields(
    entry_point_type: EntryPointType,
    entry_point_selector: int,
    message_from_l1_nonce: Optional[int],
    max_fee: int,
    version: int,
    only_query: bool,
) -> Tuple[TransactionHashPrefix, List[int]]:
    """
    Performs validation on fields related to function invocation transaction.
    Deduces and returns entry point type-related fields required for hash calculation of
    InvokeFunction transaction. The query flag is used to determine the transaction's type.
    If True, the transaction is assumed to be used for query rather than
    being invoked in the StarkNet OS.
    """
    # Validate version.
    validate_version(version=version, only_query=only_query)

    # Validate entry point type-related fields.
    if entry_point_type is EntryPointType.EXTERNAL:
        assert message_from_l1_nonce is None, "An InvokeFunction transaction cannot have a nonce."
        validate_selector_for_fee(selector=entry_point_selector, max_fee=max_fee)

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


def validate_selector_for_fee(selector: int, max_fee: int):
    if max_fee == 0:
        return

    stark_assert(
        selector == starknet_abi.EXECUTE_ENTRY_POINT_SELECTOR,
        code=StarknetErrorCode.UNSUPPORTED_SELECTOR_FOR_FEE,
        message=(
            "All transactions should go through the "
            f"{starknet_abi.EXECUTE_ENTRY_POINT_NAME} entrypoint."
        ),
    )


def get_invoke_tx_total_resources(
    state: CarriedState, call_info: CallInfo
) -> Tuple[int, Mapping[str, int]]:
    """
    Returns the total resources needed to include the most recent InvokeFunction transaction in
    a StarkNet batch (recent w.r.t. application on the given state) - L1 gas usage and Cairo
    execution resources.
    Used for transaction fee; calculation is made as if the transaction is the first in batch, for
    consistency.
    """
    assert state.parent_state is not None, "State is expected to be a child of another state."

    # Number of modified contracts by the most recently applied-on-state transaction.
    n_modified_contracts_by_tx = len(state.modified_contracts.maps[0].keys())

    tx_syscall_counter = get_tx_syscall_counter(state=state)
    constructor_calldata_total_length, n_deployments = get_call_deployment_info(call_info=call_info)
    assert n_deployments == tx_syscall_counter.get("deploy", 0)

    l1_gas_usage = calculate_tx_gas_usage(
        l2_to_l1_messages=call_info.get_sorted_l2_to_l1_messages(),
        n_modified_contracts=n_modified_contracts_by_tx,
        n_storage_writes=tx_syscall_counter.get("storage_write", 0)
        + FEE_TRANSFER_N_STORAGE_CHANGES_TO_CHARGE,
        # L1 handlers cannot be called.
        l1_handler_payload_size=None,
        constructor_calldata_total_length=constructor_calldata_total_length,
        n_deployments=n_deployments,
    )

    # Add additional Cairo resources needed for the OS to run the transaction.
    execution_resources = call_info.execution_resources
    execution_resources += calculate_syscall_resources(syscall_counter=tx_syscall_counter)
    execution_resources += calculate_execute_txs_inner_resources(
        tx_type=TransactionType.INVOKE_FUNCTION
    )

    return l1_gas_usage, execution_resources.to_dict()


async def read_contract_class(class_hash: bytes, storage: Storage) -> ContractClass:
    contract_class_fact = await ContractClassFact.get_or_fail(storage=storage, suffix=class_hash)
    return contract_class_fact.contract_definition


async def write_contract_class_fact(
    contract_class: ContractClass, ffc: FactFetchingContext
) -> bytes:
    contract_class_fact = ContractClassFact(contract_definition=contract_class)
    return await contract_class_fact.set_fact(ffc=ffc)


def get_call_deployment_info(call_info: CallInfo) -> Tuple[int, int]:
    # The sum of all constructor calldata lengths deployed in the transaction.
    constructor_calldata_total_length = 0
    # The number of the contracts deployed in the transaction.
    n_deployments = 0

    for call_info in call_info.gen_call_topology():
        if call_info.entry_point_type is EntryPointType.CONSTRUCTOR:
            constructor_calldata_total_length += len(call_info.calldata)
            n_deployments += 1

    return constructor_calldata_total_length, n_deployments
