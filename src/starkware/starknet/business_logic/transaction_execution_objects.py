import dataclasses
import functools
import logging
import operator
from dataclasses import field
from typing import List, Optional, Set, cast

import marshmallow_dataclass

from services.everest.business_logic.internal_transaction import EverestTransactionExecutionInfo
from services.everest.definitions import fields as everest_fields
from starkware.cairo.lang.vm.cairo_pie import ExecutionResources
from starkware.cairo.lang.vm.utils import RunResources
from starkware.starknet.business_logic.state import StateSelector
from starkware.starknet.definitions import fields
from starkware.starknet.services.api.contract_definition import EntryPointType
from starkware.starkware_utils.marshmallow_dataclass_fields import SetField
from starkware.starkware_utils.validated_dataclass import ValidatedDataclass
from starkware.starkware_utils.validated_fields import sequential_id_metadata

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class TransactionExecutionContext(ValidatedDataclass):
    """
    A context for transaction execution, which is shared between internal calls.
    """

    run_resources: RunResources
    # Used for tracking global events order.
    n_emitted_events: int = field(metadata=sequential_id_metadata("Number of emitted events"))

    @classmethod
    def create(cls, n_steps: int) -> "TransactionExecutionContext":
        return cls(run_resources=RunResources(n_steps=n_steps), n_emitted_events=0)


@dataclasses.dataclass(frozen=True)
class OrderedEventContent(ValidatedDataclass):
    """
    Contains the raw content of an event, without the context its origin
    (emitting contract, etc.) along with its order in the transaction execution.
    """

    order: int = field(metadata=sequential_id_metadata("Event order"))
    # The keys by which the event will be indexed.
    keys: List[int] = field(metadata=fields.felt_list_metadata)
    # The data of the event.
    data: List[int] = field(metadata=fields.felt_list_metadata)


@dataclasses.dataclass(frozen=True)
class Event(ValidatedDataclass):
    """
    Represents a StarkNet event; contains all the fields that will be included in the
    block hash.
    """

    # Emitting contract address.
    from_address: int = field(metadata=fields.contract_address_metadata)
    # The keys by which the event will be indexed.
    keys: List[int] = field(metadata=fields.felt_list_metadata)
    # The data of the event.
    data: List[int] = field(metadata=fields.felt_list_metadata)

    @classmethod
    def create(cls, event_content: OrderedEventContent, emitting_contract_address: int):
        return cls(
            from_address=emitting_contract_address,
            keys=event_content.keys,
            data=event_content.data,
        )


@dataclasses.dataclass(frozen=True)
class L2ToL1MessageInfo(ValidatedDataclass):
    """
    Represents a StarkNet L2-to-L1 message.
    """

    from_address: int = field(metadata=fields.contract_address_metadata)
    to_address: int = field(metadata=everest_fields.EthAddressIntField.metadata("to_address"))
    payload: List[int] = field(metadata=fields.felt_list_metadata)


@dataclasses.dataclass(frozen=True)
class ContractCallResponse(ValidatedDataclass):
    """
    Contains the information needed by the OS to guess the response of a contract call.
    """

    retdata: List[int]


@dataclasses.dataclass(frozen=True)
class ContractCall(ValidatedDataclass):
    """
    Represents a contract call, either internal or external.
    Holds the information needed for the execution of the represented contract call by the OS.
    The addresses are of L2 contracts.
    No need for validations here, as the fields are taken from validated objects.
    """

    # Static info.

    from_address: int  # Should be zero if the call represents the parent transaction itself.
    to_address: int  # The called contract address.
    # The address that holds the executed code; relevant just for delegate calls, where it may
    # differ from the code of the to_address contract.
    code_address: Optional[int] = field(metadata=fields.optional_contract_address_metadata)
    entry_point_selector: Optional[int] = field(metadata=dict(load_default=None, required=False))
    entry_point_type: Optional[EntryPointType] = field(
        metadata=dict(load_default=None, required=False)
    )
    calldata: List[int]
    signature: List[int]

    # Execution info.

    cairo_usage: ExecutionResources
    # Note that the order starts from a transaction-global offset.
    events: List[OrderedEventContent] = field(metadata=dict(load_default=list, required=False))
    l2_to_l1_messages: List[L2ToL1MessageInfo] = field(
        metadata=dict(load_default=list, required=False)
    )

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
                everest_fields.felt_metadata("storage_accessed_address")["marshmallow_field"]
            )
        )
    )

    @classmethod
    def empty(cls, to_address: int) -> "ContractCall":
        return cls(
            from_address=0,
            to_address=to_address,
            code_address=None,
            entry_point_type=None,
            entry_point_selector=None,
            calldata=[],
            signature=[],
            cairo_usage=ExecutionResources.empty(),
            events=[],
            l2_to_l1_messages=[],
            internal_call_responses=[],
            storage_read_values=[],
            storage_accessed_addresses=set(),
        )

    @classmethod
    def empty_for_tests(cls) -> "ContractCall":
        return cls.empty(to_address=0)

    @property
    def state_selector(self) -> StateSelector:
        code_address = self.to_address if self.code_address is None else self.code_address
        return StateSelector(contract_addresses={self.to_address, code_address})


@marshmallow_dataclass.dataclass(frozen=True)
class TransactionExecutionInfo(EverestTransactionExecutionInfo):
    """
    Contains the information gathered by the execution of a transation. Main uses:
    1. Supplies hints for the OS run on the corresponding transaction; e.g., internal call results.
    2. Stores useful information for users; e.g., L2-to-L1 messages it sent and emitted events.
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
        return functools.reduce(
            operator.__or__,
            (contract_call.state_selector for contract_call in self.contract_calls),
            StateSelector.empty(),
        )

    def get_sorted_events(self) -> List[Event]:
        """
        Returns a list of StarkNet Event objects collected during the execution, sorted by the order
        in which they were emitted.
        """
        n_events = sum(len(contract_call.events) for contract_call in self.contract_calls)
        starknet_events: List[Optional[Event]] = [None] * n_events

        for contract_call in self.contract_calls:
            for ordered_event_content in contract_call.events:
                # Convert OrderedEventContent -> Event. I.e., add emitting contract address
                # and remove order.
                starknet_events[ordered_event_content.order] = Event.create(
                    emitting_contract_address=contract_call.to_address,
                    event_content=ordered_event_content,
                )

        assert all(
            starknet_event is not None for starknet_event in starknet_events
        ), "Unexpected holes in the event order."
        return cast(List[Event], starknet_events)

    @staticmethod
    def get_state_selector_of_many(
        execution_infos: List["TransactionExecutionInfo"],
    ) -> StateSelector:
        return functools.reduce(
            operator.__or__,
            (execution_info.state_selector for execution_info in execution_infos),
            StateSelector.empty(),
        )
