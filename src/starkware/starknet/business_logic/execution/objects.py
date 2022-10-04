import dataclasses
import functools
import logging
import operator
from dataclasses import field
from enum import Enum, auto
from typing import FrozenSet, Iterable, Iterator, List, Mapping, Optional, Set, cast

import marshmallow.fields as mfields
import marshmallow_dataclass

from services.everest.business_logic.transaction_execution_objects import (
    EverestTransactionExecutionInfo,
)
from services.everest.definitions import fields as everest_fields
from starkware.cairo.lang.vm.cairo_pie import ExecutionResources
from starkware.cairo.lang.vm.utils import RunResources
from starkware.python.utils import as_non_optional
from starkware.starknet.business_logic.fact_state.contract_state_objects import StateSelector
from starkware.starknet.business_logic.state.state import StorageEntry
from starkware.starknet.definitions import constants, fields
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.public.abi import CONSTRUCTOR_ENTRY_POINT_SELECTOR
from starkware.starknet.services.api.contract_class import EntryPointType
from starkware.starknet.services.api.gateway.transaction import DEFAULT_DECLARE_SENDER_ADDRESS
from starkware.starkware_utils.marshmallow_dataclass_fields import (
    SetField,
    additional_metadata,
    nonrequired_list_metadata,
    nonrequired_optional_metadata,
)
from starkware.starkware_utils.marshmallow_fields_metadata import sequential_id_metadata
from starkware.starkware_utils.serializable_dataclass import SerializableMarshmallowDataclass
from starkware.starkware_utils.validated_dataclass import (
    ValidatedDataclass,
    ValidatedMarshmallowDataclass,
)

logger = logging.getLogger(__name__)
ResourcesMapping = Mapping[str, int]


class CallType(Enum):
    CALL = 0
    DELEGATE = auto()


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
    # The maximal fee to be paid in Wei for the execution.
    max_fee: int = field(metadata=fields.fee_metadata)
    # The nonce of the transaction.
    nonce: int
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
        nonce: Optional[int],
        n_steps: int,
        version: int,
    ) -> "TransactionExecutionContext":
        nonce = 0 if version in [0, constants.QUERY_VERSION_BASE] else as_non_optional(nonce)
        return cls(
            account_contract_address=account_contract_address,
            transaction_hash=transaction_hash,
            signature=signature,
            max_fee=max_fee,
            nonce=nonce,
            version=version,
            run_resources=RunResources(n_steps=n_steps),
            n_emitted_events=0,
            n_sent_messages=0,
        )

    @classmethod
    def create_for_testing(
        cls,
        account_contract_address: int = 0,
        max_fee: int = 0,
        nonce: int = 0,
        n_steps: int = 100000,
        version: int = constants.TRANSACTION_VERSION,
    ) -> "TransactionExecutionContext":
        return cls(
            account_contract_address=account_contract_address,
            transaction_hash=0,
            signature=[],
            max_fee=max_fee,
            nonce=nonce,
            version=version,
            run_resources=RunResources(n_steps=n_steps),
            n_emitted_events=0,
            n_sent_messages=0,
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
    call_type: Optional[CallType] = field(metadata=nonrequired_optional_metadata)
    contract_address: int
    # Holds the hash of the executed class; in the case of a library call, it may differ from the
    # class hash of the called contract state.
    class_hash: Optional[bytes] = field(metadata=fields.optional_class_hash_metadata)
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
        metadata=additional_metadata(
            marshmallow_field=SetField(
                everest_fields.felt_metadata("storage_accessed_address")["marshmallow_field"]
            )
        )
    )

    # Internal calls made by this call.

    internal_calls: List["CallInfo"] = field(
        metadata=additional_metadata(
            marshmallow_field=mfields.List(mfields.Nested(lambda: CallInfo.Schema()))
        )
    )

    # Deprecated fields.
    # The address that holds the executed code; relevant just for delegate calls (version 1), where
    # it may differ from the code of the to_address contract.
    code_address: Optional[int]

    def get_visited_storage_entries(self) -> Set[StorageEntry]:
        storage_entries = {(self.contract_address, key) for key in self.accessed_storage_keys}
        internal_visited_storage_entries = CallInfo.get_visited_storage_entries_of_many(
            call_infos=self.internal_calls
        )
        return storage_entries | internal_visited_storage_entries

    def get_state_selector(self) -> StateSelector:
        code_address = self.contract_address if self.code_address is None else self.code_address
        assert self.class_hash is not None, "Class hash is missing from call info."
        selector = StateSelector.create(
            contract_addresses={self.contract_address, code_address}
            - {DEFAULT_DECLARE_SENDER_ADDRESS},
            class_hashes=[self.class_hash],
        )

        return selector | CallInfo.get_state_selector_of_many(call_infos=self.internal_calls)

    @staticmethod
    def get_visited_storage_entries_of_many(call_infos: Iterable["CallInfo"]) -> Set[StorageEntry]:
        return functools.reduce(
            operator.__or__,
            (call_info.get_visited_storage_entries() for call_info in call_infos),
            set(),
        )

    @staticmethod
    def get_state_selector_of_many(call_infos: Iterable["CallInfo"]) -> StateSelector:
        return functools.reduce(
            operator.__or__,
            (call_info.get_state_selector() for call_info in call_infos),
            StateSelector.empty(),
        )

    def gen_call_topology(self) -> Iterator["CallInfo"]:
        """
        Yields the contract calls in DFS (preorder).
        """
        yield self
        for call in self.internal_calls:
            yield from call.gen_call_topology()

    @classmethod
    def empty(
        cls,
        contract_address: int,
        caller_address: int,
        class_hash: Optional[bytes],
        call_type: Optional[CallType] = None,
        entry_point_type: Optional[EntryPointType] = None,
        entry_point_selector: Optional[int] = None,
    ) -> "CallInfo":
        return cls(
            caller_address=caller_address,
            call_type=call_type,
            contract_address=contract_address,
            class_hash=class_hash,
            code_address=None,
            entry_point_type=entry_point_type,
            entry_point_selector=entry_point_selector,
            calldata=[],
            retdata=[],
            execution_resources=ExecutionResources.empty(),
            events=[],
            l2_to_l1_messages=[],
            storage_read_values=[],
            accessed_storage_keys=set(),
            internal_calls=[],
        )

    @classmethod
    def empty_for_testing(cls) -> "CallInfo":
        return cls.empty(contract_address=1, caller_address=0, class_hash=None)

    @classmethod
    def empty_constructor_call(
        cls, contract_address: int, caller_address: int, class_hash: bytes
    ) -> "CallInfo":
        return cls.empty(
            contract_address=contract_address,
            caller_address=caller_address,
            class_hash=class_hash,
            call_type=CallType.CALL,
            entry_point_type=EntryPointType.CONSTRUCTOR,
            entry_point_selector=CONSTRUCTOR_ENTRY_POINT_SELECTOR,
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

    # Transaction-specific validation call info.
    validate_info: Optional[CallInfo]
    # Transaction-specific execution call info, None for Declare.
    call_info: Optional[CallInfo]
    # Fee transfer call info, executed by the BE for account contract transactions (e.g., declare
    # and invoke).
    fee_transfer_info: Optional[CallInfo]
    # The actual fee that was charged in Wei.
    actual_fee: int = field(metadata=fields.FeeField.metadata(field_name="actual_fee"))
    # Actual resources the transaction is charged for, including L1 gas
    # and OS additional resources estimation.
    actual_resources: ResourcesMapping = field(metadata=fields.name_to_resources_metadata)
    # Transaction type is used to determine the order of the calls.
    tx_type: Optional[TransactionType]

    @property
    def non_optional_calls(self) -> Iterable[CallInfo]:
        if self.tx_type is TransactionType.DEPLOY_ACCOUNT:
            # In deploy account tx, validation will take place after execution of the constructor.
            ordered_optional_calls = (self.call_info, self.validate_info, self.fee_transfer_info)
        else:
            ordered_optional_calls = (self.validate_info, self.call_info, self.fee_transfer_info)
        return tuple(call for call in ordered_optional_calls if call is not None)

    def get_state_selector(self) -> StateSelector:
        return CallInfo.get_state_selector_of_many(call_infos=self.non_optional_calls)

    def get_executed_class_hashes(self) -> FrozenSet[bytes]:
        return frozenset(self.get_state_selector().class_hashes)

    def get_visited_storage_entries(self) -> Set[StorageEntry]:
        return CallInfo.get_visited_storage_entries_of_many(call_infos=self.non_optional_calls)

    @classmethod
    def from_call_infos(
        cls,
        execute_call_info: Optional[CallInfo],
        tx_type: Optional[TransactionType],
        validate_info: Optional[CallInfo] = None,
        fee_transfer_info: Optional[CallInfo] = None,
    ) -> "TransactionExecutionInfo":
        return cls(
            validate_info=validate_info,
            call_info=execute_call_info,
            fee_transfer_info=fee_transfer_info,
            actual_fee=0,
            actual_resources={},
            tx_type=tx_type,
        )

    @classmethod
    def empty(cls) -> "TransactionExecutionInfo":
        return cls(
            validate_info=None,
            call_info=None,
            fee_transfer_info=None,
            actual_fee=0,
            actual_resources={},
            tx_type=None,
        )

    @classmethod
    def create_concurrent_stage_execution_info(
        cls,
        validate_info: Optional[CallInfo],
        call_info: Optional[CallInfo],
        actual_resources: ResourcesMapping,
        tx_type: TransactionType,
    ) -> "TransactionExecutionInfo":
        """
        Returns TransactionExecutionInfo for the concurrent stage (without
        fee_transfer_info and without fee).
        """
        return cls(
            validate_info=validate_info,
            call_info=call_info,
            fee_transfer_info=None,
            actual_fee=0,
            actual_resources=actual_resources,
            tx_type=tx_type,
        )

    @classmethod
    def from_concurrent_stage_execution_info(
        cls,
        concurrent_execution_info: "TransactionExecutionInfo",
        actual_fee: int,
        fee_transfer_info: Optional[CallInfo],
    ) -> "TransactionExecutionInfo":
        """
        Fills the given concurrent_execution_info with actual_fee and fee_transfer_info.
        Used when the call infos (except for the fee handling) executed in the concurrent stage.
        """
        return cls(
            validate_info=concurrent_execution_info.validate_info,
            call_info=concurrent_execution_info.call_info,
            fee_transfer_info=fee_transfer_info,
            actual_fee=actual_fee,
            actual_resources=concurrent_execution_info.actual_resources,
            tx_type=concurrent_execution_info.tx_type,
        )

    def gen_call_iterator(self) -> Iterator[CallInfo]:
        """
        Yields the contract calls in the order that they are going to be executed in the OS.
        (Preorder of the original call tree followed by the preorder of the call tree that was
        generated while charging the fee).
        """
        for call_info in self.non_optional_calls:
            yield from call_info.gen_call_topology()

    @staticmethod
    def get_state_selector_of_many(
        execution_infos: Iterable["TransactionExecutionInfo"],
    ) -> StateSelector:
        return functools.reduce(
            operator.__or__,
            (execution_info.get_state_selector() for execution_info in execution_infos),
            StateSelector.empty(),
        )

    @staticmethod
    def get_visited_storage_entries_of_many(
        execution_infos: Iterable["TransactionExecutionInfo"],
    ) -> Set[StorageEntry]:
        return functools.reduce(
            operator.__or__,
            (execution_info.get_visited_storage_entries() for execution_info in execution_infos),
            set(),
        )

    def get_sorted_events(self) -> List[Event]:
        return [
            event
            for call_info in self.non_optional_calls
            for event in call_info.get_sorted_events()
        ]

    def get_sorted_l2_to_l1_messages(self) -> List[L2ToL1MessageInfo]:
        return [
            message
            for call_info in self.non_optional_calls
            for message in call_info.get_sorted_l2_to_l1_messages()
        ]


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
    entry_point_selector: Optional[int] = field(metadata=nonrequired_optional_metadata)
    entry_point_type: Optional[EntryPointType] = field(metadata=nonrequired_optional_metadata)
    calldata: List[int]
    signature: List[int]

    # Execution info.

    cairo_usage: ExecutionResources
    # Note that the order starts from a transaction-global offset.
    events: List[OrderedEvent] = field(metadata=nonrequired_list_metadata)
    l2_to_l1_messages: List[L2ToL1MessageInfo] = field(metadata=nonrequired_list_metadata)

    # Information kept for the StarkNet OS run in the GpsAmbassador.

    # The response of the direct internal calls invoked by this call; kept in the order
    # the OS "guesses" them.
    internal_call_responses: List[ContractCallResponse]
    # A list of values read from storage by this call, **excluding** readings from nested calls.
    storage_read_values: List[int]
    # A set of storage addresses accessed by this call, **excluding** addresses from nested calls;
    # kept in order to calculate and prepare the commitment tree facts before the StarkNet OS run.
    storage_accessed_addresses: Set[int] = field(
        metadata=additional_metadata(
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
        return StateSelector.create(
            contract_addresses=[self.to_address, code_address], class_hashes=[]
        )


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
