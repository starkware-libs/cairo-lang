import asyncio
import dataclasses
from abc import abstractmethod
from dataclasses import field
from typing import Dict, Iterable, List, Optional, Set, Tuple, cast

import marshmallow_dataclass

from services.everest.api.gateway.transaction import EverestTransaction
from services.everest.business_logic.internal_transaction import (
    EverestInternalTransaction,
    EverestTransactionExecutionInfo,
)
from services.everest.business_logic.state import CarriedStateBase
from services.everest.definitions import fields as everest_fields
from starkware.cairo.lang.vm.utils import RunResources
from starkware.starknet.business_logic.state import CarriedState, StateSelector
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.services.api.gateway.transaction import Transaction
from starkware.starkware_utils.config_base import Config
from starkware.starkware_utils.marshmallow_dataclass_fields import SetField
from starkware.starkware_utils.validated_dataclass import ValidatedDataclass


@dataclasses.dataclass(frozen=True)
class L2ToL1MessageInfo(ValidatedDataclass):
    """
    A class representing a StarkNet L2-to-L1 message.
    """

    from_address: int = field(metadata=fields.contract_address_metadata)
    to_address: int = field(metadata=everest_fields.EthAddressIntField.metadata("to_address"))
    payload: List[int] = field(metadata=fields.felt_list_metadata)


@dataclasses.dataclass(frozen=True)
class ContractCallResponse:
    """
    Contains the information needed by the OS to guess the response of a contract call.
    """

    retdata: List[int]
    # Indicates how far the storage_ptr of the **caller** storage has advanced during this call,
    # **including** nested calls; kept to hint the StarkNet OS run as to where to advance the
    # storage_ptr when encountering this system call, while executing the parent call
    # (which is before the actual execution of this call).
    storage_ptr_diff: int


@dataclasses.dataclass(frozen=True)
class ContractCall(ValidatedDataclass):
    """
    Represents a contract call, either internal or external.
    Holds the information needed for the execution of the represented contract call by the OS.
    The addresses are of L2 contracts.
    No need for validations here, as the fields are taken from validated objects.
    """

    # Should be None if the call represents the parent transaction itself.
    from_address: Optional[int]
    # The called contract address.
    to_address: int
    calldata: List[int]

    # Information kept for the StarkNet OS run in the GpsAmbassador.
    # The response of the direct internal calls invoked by this call; kept in the order
    # the OS "guesses" them.
    internal_call_responses: List[ContractCallResponse]
    # A list of values read from storage by this call, **excluding** readings from nested calls.
    storage_read_values: List[int]
    # A set of storage addresses accessed by this call, **excluding** addresses from nested calls;
    # kept in order to calculate and prepare the commitment tree facts before the StarkNet OS run.
    storage_accessed_addresses: Set[int] = field(
        metadata=dict(
            marshmallow_field=SetField(
                fields.felt_metadata("storage_accessed_address")["marshmallow_field"]
            )
        )
    )

    @classmethod
    def empty(cls, to_address: int) -> "ContractCall":
        return cls(
            from_address=None,
            to_address=to_address,
            calldata=[],
            internal_call_responses=[],
            storage_read_values=[],
            storage_accessed_addresses=set(),
        )

    @classmethod
    def empty_for_tests(cls, internal_call_responses: List[ContractCallResponse]) -> "ContractCall":
        return dataclasses.replace(
            cls.empty(to_address=0), internal_call_responses=internal_call_responses
        )


@marshmallow_dataclass.dataclass(frozen=True)
class TransactionExecutionInfo(EverestTransactionExecutionInfo):
    """
    A class containing the information gathered by the execution of a transation.
    For example, the L2-to-L1 messages it sent. In the future: information about gas, events, etc.
    """

    l2_to_l1_messages: List[L2ToL1MessageInfo]
    # The retdata of the main transaction.
    retdata: List[int]
    call_info: ContractCall
    # The internal contract calls; arranged in DFS order, which is the order they are invoked by the
    # OS.
    internal_calls: List[ContractCall]

    @classmethod
    def create(
        cls, call_info: ContractCall, internal_calls: Optional[List[ContractCall]] = None
    ) -> "TransactionExecutionInfo":
        return cls(
            l2_to_l1_messages=[],
            retdata=[],
            call_info=call_info,
            internal_calls=[] if internal_calls is None else internal_calls,
        )

    @property
    def contract_calls(self) -> List[ContractCall]:
        return [self.call_info, *self.internal_calls]

    @property
    def state_selector(self) -> StateSelector:
        return StateSelector(
            contract_addresses={contract_call.to_address for contract_call in self.contract_calls}
        )

    @staticmethod
    def get_state_selector_of_many(
        execution_infos: List["TransactionExecutionInfo"],
    ) -> StateSelector:
        state_selector = StateSelector.empty()
        for execution_info in execution_infos:
            state_selector |= execution_info.state_selector

        return state_selector


class InternalTransactionInterface(EverestInternalTransaction):
    """
    StarkNet internal transaction interface.
    """

    @classmethod
    @abstractmethod
    def from_external(
        cls, external_tx: EverestTransaction, general_config: Config
    ) -> "InternalTransactionInterface":
        """
        Returns an internal transaction genearated based on an external one.
        """

    @abstractmethod
    def to_external(self) -> Transaction:
        """
        Returns an external transaction genearated based on an internal one.
        """

    @staticmethod
    def get_state_selector_of_many(
        txs: Iterable["EverestInternalTransaction"], general_config: Config
    ) -> StateSelector:
        """
        Returns the state selector of a collection of transactions (i.e., union of selectors).
        """
        # Downcast arguments to application-specific types.
        assert isinstance(general_config, StarknetGeneralConfig)

        state_selector = EverestInternalTransaction._get_state_selector_of_many(
            txs=txs, general_config=general_config, state_selector_cls=StateSelector
        )
        return cast(StateSelector, state_selector)

    async def apply_state_updates(
        self, state: CarriedStateBase, general_config: Config
    ) -> TransactionExecutionInfo:
        """
        Applies the transaction on the commitment tree state in an atomic manner.
        """
        # Downcast arguments to application-specific types.
        assert isinstance(state, CarriedState)
        assert isinstance(general_config, StarknetGeneralConfig)

        with state.copy_and_apply() as state_to_update:
            execution_info = await self._apply_specific_state_updates(
                state=state_to_update, general_config=general_config
            )

        return execution_info

    @abstractmethod
    async def _apply_specific_state_updates(
        self, state: CarriedState, general_config: StarknetGeneralConfig
    ) -> TransactionExecutionInfo:
        pass

    @abstractmethod
    def _synchronous_apply_specific_state_updates(
        self,
        state: CarriedState,
        general_config: StarknetGeneralConfig,
        loop: asyncio.AbstractEventLoop,
        caller_address: Optional[int],
        run_resources: RunResources,
    ) -> Tuple[TransactionExecutionInfo, Dict[int, int]]:
        pass

    def verify_signatures(self):
        """
        Verifies the signatures in the transaction.
        Currently not implemented by StarkNet transactions.
        """
