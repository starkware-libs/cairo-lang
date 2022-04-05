import dataclasses
import functools
import logging
import operator
from dataclasses import field
from typing import Iterator, List, Optional, Set, cast

import marshmallow.fields as mfields
import marshmallow_dataclass

from services.everest.business_logic.internal_transaction import EverestTransactionExecutionInfo
from services.everest.definitions import fields as everest_fields
from starkware.cairo.lang.vm.cairo_pie import ExecutionResources
from starkware.cairo.lang.vm.utils import RunResources
from starkware.starknet.business_logic.state.state import StateSelector
from starkware.starknet.definitions import constants, fields
from starkware.starknet.services.api.contract_definition import EntryPointType
from starkware.starkware_utils.marshmallow_dataclass_fields import SetField
from starkware.starkware_utils.serializable_dataclass import SerializableMarshmallowDataclass
from starkware.starkware_utils.validated_dataclass import (
    ValidatedDataclass,
    ValidatedMarshmallowDataclass,
)
from starkware.starkware_utils.validated_fields import sequential_id_metadata

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class TransactionExecutionContext(ValidatedDataclass):
    """
    A context for transaction execution, which is shared between internal calls.
    """

    # The account contract from which this transaction originates.
    account_contract_address: int = field(
        metadata=fields.AddressField.metadata(field_name="account_contract_address")
    )
    # The hash of the transaction.
    transaction_hash: int = field(metadata=fields.transaction_hash_metadata)
    # The signature of the transaction.
    signature: List[int] = field(metadata=fields.signature_metadata)
    max_fee: int = field(metadata=fields.fee_metadata)
    version: int = field(metadata=fields.tx_version_metadata)
    run_resources: RunResources
    # Used for tracking global events order.
    n_emitted_events: int = field(metadata=sequential_id_metadata("Number of emitted events"))
    # Used for tracking global L2-to-L1 messages order.
    n_sent_messages: int = field(metadata=sequential_id_metadata("Number of messages sent to L1"))

    @classmethod
    def create(
        cls,
        account_contract_address: int,
        transaction_hash: int,
        signature: List[int],
        max_fee: int,
        n_steps: int,
        version: int,
    ) -> "TransactionExecutionContext":
        return cls(
            account_contract_address=account_contract_address,
            transaction_hash=transaction_hash,
            signature=signature,
            max_fee=max_fee,
            version=version,
            run_resources=RunResources(n_steps=n_steps),
            n_emitted_events=0,
            n_sent_messages=0,
        )

    @classmethod
    def create_for_call(
        cls, account_contract_address: int, n_steps: int
    ) -> "TransactionExecutionContext":
        """
        Creates a context for transaction execution. To be used when executing an entry point
        without a concrete InternalInvokeFunction object.
        """
        return cls.create(
            account_contract_address=account_contract_address,
            n_steps=n_steps,
            signature=[],
            transaction_hash=0,
            max_fee=0,
            version=constants.TRANSACTION_VERSION,
        )


@dataclasses.dataclass(frozen=True)
class OrderedEvent(ValidatedDataclass):
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
    from_address: int = field(metadata=fields.L2AddressField.metadata(field_name="from_address"))
    # The keys by which the event will be indexed.
    keys: List[int] = field(metadata=fields.felt_as_hex_list_metadata)
    # The data of the event.
    data: List[int] = field(metadata=fields.felt_as_hex_list_metadata)

    @classmethod
    def create(cls, event_content: OrderedEvent, emitting_contract_address: int):
        return cls(
            from_address=emitting_contract_address,
            keys=event_content.keys,
            data=event_content.data,
        )


@dataclasses.dataclass(frozen=True)
class OrderedL2ToL1Message(ValidatedDataclass):
    """
    A class containing the raw content of a L2-to-L1 message, without the context its origin
    (the sending contract, etc.) along with its order in the transaction execution.
    """

    order: int = field(metadata=sequential_id_metadata("L2-to-L1 message order"))
    to_address: int = field(metadata=everest_fields.EthAddressIntField.metadata("to_address"))
    payload: List[int] = field(metadata=fields.felt_list_metadata)


@dataclasses.dataclass(frozen=True)
class L2ToL1MessageInfo(ValidatedDataclass):
    """
    Represents a StarkNet L2-to-L1 message.
    """

    from_address: int = field(metadata=fields.L2AddressField.metadata(field_name="from_address"))
    to_address: int = field(metadata=everest_fields.EthAddressIntField.metadata("to_address"))
    payload: List[int] = field(metadata=fields.felt_list_metadata)

    @classmethod
    def create(cls, message_content: OrderedL2ToL1Message, sending_contract_address: int):
        return cls(
            from_address=sending_contract_address,
            to_address=message_content.to_address,
            payload=message_content.payload,
        )


# NOTE: This dataclass isn't validated due to a forward-declaration issue.
@marshmallow_dataclass.dataclass(frozen=True)
class CallInfo(SerializableMarshmallowDataclass):
    """
    Represents a contract call, either internal or external.
    Holds the information needed for the execution of the represented contract call by the OS.
    No need for validations here, as the fields are taken from validated objects.
    """

    # Static info.

    caller_address: int  # Should be zero if the call represents an external transaction.
    contract_address: int
    # The address that holds the executed code; relevant just for delegate calls, where it may
    # differ from the code of the to_address contract.
    code_address: Optional[int]
    entry_point_selector: Optional[int]
    entry_point_type: Optional[EntryPointType]
    calldata: List[int]
    # Execution info.
    retdata: List[int]
    execution_resources: ExecutionResources
    # Note that the order starts from a transaction-global offset.
    events: List[OrderedEvent]
    l2_to_l1_messages: List[OrderedL2ToL1Message]

    # Information kept for the StarkNet OS run in the GpsAmbassador.

    # A list of values read from storage by this call, **excluding** readings from nested calls.
    storage_read_values: List[int]
    # A set of storage keys accessed by this call, **excluding** keys from nested calls;
    # kept in order to calculate and prepare the commitment tree facts before the StarkNet OS run.
    accessed_storage_keys: Set[int] = field(
        metadata=dict(
            marshmallow_field=SetField(
                everest_fields.felt_metadata("storage_accessed_address")["marshmallow_field"]
            )
        )
    )

    # Internal calls made by this call.

    internal_calls: List["CallInfo"] = field(
        metadata=dict(marshmallow_field=mfields.List(mfields.Nested(lambda: CallInfo.Schema())))
    )

    def get_state_selector(self) -> StateSelector:
        code_address = self.contract_address if self.code_address is None else self.code_address
        selector = StateSelector(contract_addresses={self.contract_address, code_address})
        return functools.reduce(
            StateSelector.__or__,
            (call.get_state_selector() for call in self.internal_calls),
            selector,
        )

    def gen_call_topology(self) -> Iterator["CallInfo"]:
        """
        Yields the contract calls in DFS (preorder).
        """
        yield self
        for call in self.internal_calls:
            yield from call.gen_call_topology()

    @classmethod
    def empty(cls, contract_address: int) -> "CallInfo":
        return cls(
            caller_address=0,
            contract_address=contract_address,
            code_address=None,
            entry_point_type=None,
            entry_point_selector=None,
            calldata=[],
            retdata=[],
            execution_resources=ExecutionResources.empty(),
            events=[],
            l2_to_l1_messages=[],
            storage_read_values=[],
            accessed_storage_keys=set(),
            internal_calls=[],
        )

    def get_sorted_events(self) -> List[Event]:
        """
        Returns a list of StarkNet Event objects collected during the execution, sorted by the order
        in which they were emitted.
        """
        n_events = sum(len(call.events) for call in self.gen_call_topology())
        starknet_events: List[Optional[Event]] = [None] * n_events

        for call in self.gen_call_topology():
            for ordered_event_content in call.events:
                # Convert OrderedEvent -> Event. I.e., add emitting contract address
                # and remove the order.
                starknet_events[ordered_event_content.order] = Event.create(
                    emitting_contract_address=call.contract_address,
                    event_content=ordered_event_content,
                )

        assert all(
            starknet_event is not None for starknet_event in starknet_events
        ), "Unexpected holes in the event order."

        return cast(List[Event], starknet_events)

    def get_sorted_l2_to_l1_messages(self) -> List[L2ToL1MessageInfo]:
        """
        Returns a list of StarkNet L2ToL1MessageInfo objects collected during the execution, sorted
        by the order in which they were sent.
        """
        n_messages = sum(len(call.l2_to_l1_messages) for call in self.gen_call_topology())
        starknet_l2_to_l1_messages: List[Optional[L2ToL1MessageInfo]] = [None] * n_messages

        for call in self.gen_call_topology():
            for ordered_message_content in call.l2_to_l1_messages:
                # Convert OrderedL2ToL1Message -> L2ToL1MessageInfo. I.e., add sending
                # contract address and remove the order.
                starknet_l2_to_l1_messages[
                    ordered_message_content.order
                ] = L2ToL1MessageInfo.create(
                    sending_contract_address=call.contract_address,
                    message_content=ordered_message_content,
                )

        assert all(
            message is not None for message in starknet_l2_to_l1_messages
        ), "Unexpected holes in the L2-to-L1 message order."

        return cast(List[L2ToL1MessageInfo], starknet_l2_to_l1_messages)


@marshmallow_dataclass.dataclass(frozen=True)
class TransactionExecutionInfo(EverestTransactionExecutionInfo):
    """
    Contains the information gathered by the execution of a transation. Main usages:
    1. Supplies hints for the OS run on the corresponding transaction; e.g., internal call results.
    2. Stores useful information for users; e.g., L2-to-L1 messages and emitted events.
    """

    call_info: CallInfo
    # Fee transfer call info, executed by the BE for external InvokeFunction transactions;
    # Optional since currently Deploy transactions do not have fee (and backward compatibility).
    fee_transfer_info: Optional[CallInfo]
    actual_fee: int = field(metadata=fields.FeeField.metadata(field_name="actual_fee"))

    def get_state_selector(self) -> StateSelector:
        call_info_selector = self.call_info.get_state_selector()
        if self.fee_transfer_info is None:
            return call_info_selector

        return call_info_selector | self.fee_transfer_info.get_state_selector()

    def gen_call_iterator(self) -> Iterator[CallInfo]:
        """
        Yields the contract calls in the order that they are going to be executed in the OS.
        (Preorder of the original call tree followed by the preorder of the call tree that was
        generated while charging the fee).
        """
        yield from self.call_info.gen_call_topology()
        if self.fee_transfer_info is None:
            return

        yield from self.fee_transfer_info.gen_call_topology()

    @staticmethod
    def get_state_selector_of_many(
        execution_infos: List["TransactionExecutionInfo"],
    ) -> StateSelector:
        return functools.reduce(
            operator.__or__,
            (execution_info.get_state_selector() for execution_info in execution_infos),
            StateSelector.empty(),
        )

    def get_sorted_events(self) -> List[Event]:
        return self.call_info.get_sorted_events()

    def get_sorted_l2_to_l1_messages(self) -> List[L2ToL1MessageInfo]:
        return self.call_info.get_sorted_l2_to_l1_messages()


# Deprecated classes.


@dataclasses.dataclass(frozen=True)
class ContractCallResponse(ValidatedDataclass):
    """
    Contains the information needed by the OS to guess the response of a contract call.
    """

    retdata: List[int]


@marshmallow_dataclass.dataclass(frozen=True)
class ContractCall(ValidatedMarshmallowDataclass):
    """
    Represents a contract call, either internal or external.
    Holds the information needed for the execution of the represented contract call by the OS.
    No need for validations here, as the fields are taken from validated objects.
    """

    # Static info.

    from_address: int  # Should be zero if the call represents the parent transaction itself.
    to_address: int  # The called contract address.
    # The address that holds the executed code; relevant just for delegate calls, where it may
    # differ from the code of the to_address contract.
    code_address: Optional[int] = field(metadata=fields.optional_code_address_metadata)
    entry_point_selector: Optional[int] = field(metadata=dict(load_default=None, required=False))
    entry_point_type: Optional[EntryPointType] = field(
        metadata=dict(load_default=None, required=False)
    )
    calldata: List[int]
    signature: List[int]

    # Execution info.

    cairo_usage: ExecutionResources
    # Note that the order starts from a transaction-global offset.
    events: List[OrderedEvent] = field(metadata=dict(load_default=list, required=False))
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

    @property
    def state_selector(self) -> StateSelector:
        code_address = self.to_address if self.code_address is None else self.code_address
        return StateSelector(contract_addresses={self.to_address, code_address})


@marshmallow_dataclass.dataclass(frozen=True)
class TransactionExecutionInfoDeprecated(EverestTransactionExecutionInfo):
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
        cls,
        call_info: ContractCall,
        internal_calls: Optional[List[ContractCall]] = None,
    ) -> "TransactionExecutionInfoDeprecated":
        return cls(
            l2_to_l1_messages=[],
            retdata=[],
            call_info=call_info,
            internal_calls=[] if internal_calls is None else internal_calls,
        )

    @property
    def contract_calls(self) -> List[ContractCall]:
        return [self.call_info, *self.internal_calls]

    def get_state_selector(self) -> StateSelector:
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
                # Convert OrderedEvent -> Event. I.e., add emitting contract address
                # and remove the order.
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
        execution_infos: List["TransactionExecutionInfoDeprecated"],
    ) -> StateSelector:
        return functools.reduce(
            operator.__or__,
            (execution_info.get_state_selector() for execution_info in execution_infos),
            StateSelector.empty(),
        )
