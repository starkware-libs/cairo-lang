import contextlib
import logging
from typing import Dict, Iterable, List, Optional, Tuple, cast

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.lang.vm.cairo_pie import ExecutionResources
from starkware.python.utils import sub_counters
from starkware.starknet.business_logic.execution.gas_usage import calculate_tx_gas_usage
from starkware.starknet.business_logic.execution.objects import (
    CallInfo,
    ResourcesMapping,
    TransactionExecutionInfo,
)
from starkware.starknet.business_logic.execution.os_usage import get_additional_os_resources
from starkware.starknet.business_logic.fact_state.contract_state_objects import ContractClassFact
from starkware.starknet.business_logic.fact_state.state import ExecutionResourcesManager
from starkware.starknet.business_logic.state.state import UpdatesTrackerState
from starkware.starknet.business_logic.state.state_api import SyncState
from starkware.starknet.definitions import constants, fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.public import abi as starknet_abi
from starkware.starknet.services.api.contract_class import ContractClass, EntryPointType
from starkware.starkware_utils.error_handling import (
    StarkException,
    stark_assert,
    wrap_with_stark_exception,
)
from starkware.storage.storage import FactFetchingContext

logger = logging.getLogger(__name__)

FEE_TRANSFER_N_STORAGE_CHANGES = 2  # Sender and sequencer balance update.
# Exclude the sequencer balance update, since it's charged once throughout the batch.
FEE_TRANSFER_N_STORAGE_CHANGES_TO_CHARGE = FEE_TRANSFER_N_STORAGE_CHANGES - 1

VALIDATE_BLACKLISTED_SYSCALLS: Tuple[str, ...] = ("call_contract",)


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


def verify_version(version: int, only_query: bool, old_supported_versions: List[int]):
    """
    Validates the given transaction version.

    The query flag is used to determine the transaction's type.
    If True, the transaction is assumed to be used for query rather than
    being invoked in the StarkNet OS.
    """
    assert constants.TRANSACTION_VERSION == 1
    allowed_versions = [*old_supported_versions, constants.TRANSACTION_VERSION]
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
    entry_point_selector: int,
    nonce: Optional[int],
    max_fee: int,
    version: int,
) -> Tuple[int, List[int]]:
    """
    Performs validation on fields related to function invocation transaction.
    Deduces and returns fields required for hash calculation of
    InvokeFunction transaction.
    """
    # Validate entry point type-related fields.
    additional_data: List[int]
    validate_selector_for_fee(selector=entry_point_selector, max_fee=max_fee)

    if version in [0, constants.QUERY_VERSION_BASE]:
        stark_assert(
            nonce is None,
            code=StarknetErrorCode.INVALID_TRANSACTION_NONCE,
            message="An InvokeFunction transaction (version = 0) cannot have a nonce.",
        )
        additional_data = []
        entry_point_selector_field = entry_point_selector
    else:
        stark_assert(
            nonce is not None,
            code=StarknetErrorCode.INVALID_TRANSACTION_NONCE,
            message="An InvokeFunction transaction (version != 0) must have a nonce.",
        )
        additional_data = [cast(int, nonce)]
        entry_point_selector_field = 0

    return entry_point_selector_field, additional_data


def validate_selector_for_fee(selector: int, max_fee: int):
    if max_fee == 0:
        return

    stark_assert(
        selector == starknet_abi.EXECUTE_ENTRY_POINT_SELECTOR,
        code=StarknetErrorCode.UNAUTHORIZED_ENTRY_POINT_FOR_INVOKE,
        message=(
            "All transactions should go through the "
            f"{starknet_abi.EXECUTE_ENTRY_POINT_NAME} entrypoint."
        ),
    )


def total_cairo_usage_from_execution_infos(
    execution_infos: Iterable[TransactionExecutionInfo],
) -> ExecutionResources:
    """
    Returns the sum of the Cairo usage (pure Cairo of the EP run, without OS cost) of calls in
    the given execution Infos. Excludes the fee_transfer_info resources,
    since it is part of the OS additional cost.
    """
    cairo_usage = ExecutionResources.empty()

    for execution_info in execution_infos:
        if execution_info.validate_info is not None:
            cairo_usage += execution_info.validate_info.execution_resources
        if execution_info.call_info is not None:
            cairo_usage += execution_info.call_info.execution_resources

    return cairo_usage


def calculate_tx_resources(
    resources_manager: ExecutionResourcesManager,
    call_infos: Iterable[Optional[CallInfo]],
    tx_type: TransactionType,
    state: UpdatesTrackerState,
    l1_handler_payload_size: Optional[int] = None,
) -> ResourcesMapping:
    """
    Returns the total resources needed to include the most recent transaction in a StarkNet batch
    (recent w.r.t. application on the given state) i.e., L1 gas usage and Cairo execution resources.
    Used for transaction fee; calculation is made as if the transaction is the first in batch, for
    consistency.
    """
    (n_modified_contracts, n_storage_changes) = state.count_actual_storage_changes()

    non_optional_call_infos = [call for call in call_infos if call is not None]
    n_deployments = 0
    for call_info in non_optional_call_infos:
        n_deployments += get_call_n_deployments(call_info=call_info)

    l2_to_l1_messages = []
    for call_info in non_optional_call_infos:
        l2_to_l1_messages += call_info.get_sorted_l2_to_l1_messages()

    l1_gas_usage = calculate_tx_gas_usage(
        l2_to_l1_messages=l2_to_l1_messages,
        n_modified_contracts=n_modified_contracts,
        n_storage_changes=n_storage_changes + FEE_TRANSFER_N_STORAGE_CHANGES_TO_CHARGE,
        l1_handler_payload_size=l1_handler_payload_size,
        n_deployments=n_deployments,
    )

    cairo_usage = resources_manager.cairo_usage
    tx_syscall_counter = resources_manager.syscall_counter
    # Add additional Cairo resources needed for the OS to run the transaction.
    cairo_usage += get_additional_os_resources(syscall_counter=tx_syscall_counter, tx_type=tx_type)

    return dict(l1_gas_usage=l1_gas_usage, **cairo_usage.filter_unused_builtins().to_dict())


def extract_l1_gas_and_cairo_usage(resources: ResourcesMapping) -> Tuple[int, ResourcesMapping]:
    cairo_resource_usage = dict(resources)
    return cairo_resource_usage.pop("l1_gas_usage"), cairo_resource_usage


def get_deployed_class_hash_at_address(state: SyncState, contract_address: int) -> bytes:
    class_hash = state.get_class_hash_at(contract_address=contract_address)
    stark_assert(
        class_hash != constants.UNINITIALIZED_CLASS_HASH,
        code=StarknetErrorCode.UNINITIALIZED_CONTRACT,
        message=(
            "Requested contract address "
            f"{fields.L2AddressField.format(contract_address)} is not deployed."
        ),
    )

    return class_hash


def validate_contract_deployed(state: SyncState, contract_address: int):
    get_deployed_class_hash_at_address(state=state, contract_address=contract_address)


async def write_contract_class_fact(
    contract_class: ContractClass, ffc: FactFetchingContext
) -> bytes:
    contract_class_fact = ContractClassFact(contract_definition=contract_class)
    return await contract_class_fact.set_fact(ffc=ffc)


def get_call_n_deployments(call_info: CallInfo) -> int:
    # The number of the contracts deployed in the transaction.
    n_deployments = 0

    for call_info in call_info.gen_call_topology():
        if call_info.entry_point_type is EntryPointType.CONSTRUCTOR:
            n_deployments += 1

    return n_deployments


def get_validate_entrypoint_blacklisted_syscall_counter(
    resources_manager: ExecutionResourcesManager,
) -> Dict[str, int]:
    return {
        syscall_name: resources_manager.syscall_counter.get(syscall_name, 0)
        for syscall_name in VALIDATE_BLACKLISTED_SYSCALLS
    }


@contextlib.contextmanager
def validate_entrypoint_execution_context(resources_manager: ExecutionResourcesManager):
    """
    Context manager for assuring a proper validate.
    """
    syscalls_before_execute = get_validate_entrypoint_blacklisted_syscall_counter(
        resources_manager=resources_manager
    )

    # Exceptions being thrown by this yield are allowed and propagated up.
    yield

    syscalls_after_execute = get_validate_entrypoint_blacklisted_syscall_counter(
        resources_manager=resources_manager
    )
    if syscalls_after_execute == syscalls_before_execute:
        return

    diff = sub_counters(syscalls_after_execute, syscalls_before_execute)

    raise StarkException(
        code=StarknetErrorCode.UNAUTHORIZED_ACTION_ON_VALIDATE,
        message=(
            "One or more unauthorized system calls were performed during 'validate' execution: "
            f"{[name for name, count in diff.items() if count > 0]}."
        ),
    )


def verify_no_calls_to_other_contracts(call_info: CallInfo, function_name: str):
    invoked_contract_address = call_info.contract_address
    for internal_call in call_info.gen_call_topology():
        if internal_call.contract_address != invoked_contract_address:
            raise StarkException(
                code=StarknetErrorCode.UNAUTHORIZED_ACTION_ON_VALIDATE,
                message=f"Calling other contracts during {function_name} execution is forbidden.",
            )
