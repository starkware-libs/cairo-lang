import asyncio
import dataclasses
from abc import ABC, abstractmethod
from dataclasses import field
from typing import List, TypeVar

from starkware.starknet.business_logic.execution.objects import (
    CallInfo,
    TransactionExecutionContext,
)
from starkware.starknet.business_logic.state.state import CarriedState, StateSelector
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.services.api.contract_definition import EntryPointType

TExecuteEntryPoint = TypeVar("TExecuteEntryPoint", bound="ExecuteEntryPointBase")


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@dataclasses.dataclass(frozen=True)  # type: ignore[misc]
class ExecuteEntryPointBase(ABC):
    """
    Represents a StarkNet contract call. This interface is meant to prevent a cyclic dependency
    with the BusinessLogicSyscallHandler.
    """

    # For fields that are shared with InternalInvokeFunction, see documentation there.
    contract_address: int = field(metadata=fields.contract_address_metadata)
    # The address that holds the code to execute.
    # It may differ from contract_address in the case of delegate call.
    code_address: int = field(metadata=fields.L2AddressField.metadata(field_name="code_address"))
    entry_point_selector: int = field(metadata=fields.entry_point_selector_metadata)
    entry_point_type: EntryPointType
    calldata: List[int] = field(metadata=fields.call_data_metadata)
    # The caller contract address.
    caller_address: int = field(metadata=fields.caller_address_metadata)

    def get_call_state_selector(self) -> StateSelector:
        """
        Returns the state selector of the call (i.e., subset of state commitment tree leaves
        it affects).
        """
        return StateSelector(contract_addresses={self.contract_address, self.code_address})

    @abstractmethod
    def sync_execute(
        self,
        state: CarriedState,
        general_config: StarknetGeneralConfig,
        loop: asyncio.AbstractEventLoop,
        tx_execution_context: TransactionExecutionContext,
    ) -> CallInfo:
        """
        Executes the entry point. Should be called from within the given loop.
        """
