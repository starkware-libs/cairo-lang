import asyncio
import dataclasses
from abc import ABC, abstractmethod
from dataclasses import field
from typing import List, Optional, TypeVar

from starkware.starknet.business_logic.execution.objects import (
    CallInfo,
    CallType,
    TransactionExecutionContext,
)
from starkware.starknet.business_logic.state.state import CarriedState, StateSelector
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.services.api.contract_class import EntryPointType
from starkware.starkware_utils.validated_dataclass import ValidatedDataclass

TExecuteEntryPoint = TypeVar("TExecuteEntryPoint", bound="ExecuteEntryPointBase")


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@dataclasses.dataclass(frozen=True)  # type: ignore[misc]
class ExecuteEntryPointBase(ABC, ValidatedDataclass):
    """
    Represents a StarkNet contract call. This interface is meant to prevent a cyclic dependency
    with the BusinessLogicSyscallHandler.
    """

    # For fields that are shared with InternalInvokeFunction, see documentation there.
    call_type: CallType
    contract_address: int = field(metadata=fields.contract_address_metadata)
    # The address that holds the code to execute.
    # It may differ from contract_address in the case of delegate call.
    code_address: Optional[int] = field(metadata=fields.OptionalCodeAddressField.metadata())
    class_hash: Optional[bytes] = field(metadata=fields.optional_class_hash_metadata)
    entry_point_selector: int = field(metadata=fields.entry_point_selector_metadata)
    entry_point_type: EntryPointType
    calldata: List[int] = field(metadata=fields.call_data_metadata)
    # The caller contract address.
    caller_address: int = field(metadata=fields.caller_address_metadata)

    def get_state_selector(self) -> StateSelector:
        """
        Returns the state selector of the call (i.e., subset of state commitment tree leaves
        it affects).
        """
        contract_addresses = {self.contract_address}
        if self.code_address is not None:
            contract_addresses.add(self.code_address)
        class_hashes = set() if self.class_hash is None else {self.class_hash}

        return StateSelector(contract_addresses=contract_addresses, class_hashes=class_hashes)

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
