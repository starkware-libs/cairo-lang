import dataclasses
from dataclasses import field
from enum import Enum, auto
from typing import ClassVar, Dict, Iterable, List, Optional, Tuple, Type, TypeVar, Union

import marshmallow
import marshmallow.exceptions
import marshmallow.fields as mfields
import marshmallow.utils
import marshmallow_dataclass
from marshmallow_oneofschema import OneOfSchema
from typing_extensions import Literal
from web3 import Web3

from services.everest.api.feeder_gateway.response_objects import BaseResponseObject
from services.everest.business_logic.transaction_execution_objects import TransactionFailureReason
from services.everest.definitions import fields as everest_fields
from starkware.cairo.lang.vm.cairo_pie import ExecutionResources
from starkware.python.utils import from_bytes, to_bytes
from starkware.starknet.business_logic.execution.objects import (
    CallInfo,
    Event,
    OrderedEvent,
    OrderedL2ToL1Message,
)
from starkware.starknet.business_logic.internal_transaction import (
    InternalDeploy,
    InternalInvokeFunction,
    InternalTransaction,
)
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.services.api.contract_definition import EntryPointType
from starkware.starkware_utils.marshmallow_dataclass_fields import VariadicLengthTupleField
from starkware.starkware_utils.serializable_dataclass import SerializableMarshmallowDataclass
from starkware.starkware_utils.validated_dataclass import ValidatedDataclass
from starkware.starkware_utils.validated_fields import sequential_id_metadata

BlockIdentifier = Union[int, Literal["pending"]]
OptionalBlockIdentifier = Optional[BlockIdentifier]
TBlockInfo = TypeVar("TBlockInfo", bound="StarknetBlock")


class BlockStatus(Enum):
    # A pending block; i.e., a block that is yet to be closed.
    PENDING = 0
    # An aborted block (failed in the L2 pipeline).
    ABORTED = auto()
    # A reverted block (rejected on L1).
    REVERTED = auto()
    # A block that was created on L2, in contrast to PENDING, which is not yet closed.
    ACCEPTED_ON_L2 = auto()
    # A block accepted on L1.
    ACCEPTED_ON_L1 = auto()


class TransactionStatus(Enum):
    # The transaction has not been received yet (i.e., not written to storage).
    NOT_RECEIVED = 0
    # The transaction was received by the sequencer.
    RECEIVED = auto()
    # The transaction passed the validation and entered the pending block.
    PENDING = auto()
    # The transaction failed validation and thus was skipped (applies both to a pending and an
    # actual created block).
    REJECTED = auto()
    # The transaction passed the validation and entered an actual created block.
    ACCEPTED_ON_L2 = auto()
    # The transaction was accepted on-chain.
    ACCEPTED_ON_L1 = auto()

    @property
    def was_executed(self) -> bool:
        """
        Returns whether a transaction with that status has been executed successfully.
        """
        return self in (
            TransactionStatus.PENDING,
            TransactionStatus.ACCEPTED_ON_L2,
            TransactionStatus.ACCEPTED_ON_L1,
        )

    @classmethod
    def from_block_status(cls, block_status: BlockStatus) -> "TransactionStatus":
        """
        Returns a transaction status according to the status of a block containing it.
        """
        if block_status in (
            BlockStatus.PENDING,
            BlockStatus.ACCEPTED_ON_L2,
            BlockStatus.ACCEPTED_ON_L1,
        ):
            # The statuses above are identical for a block and a transaction.
            return TransactionStatus[block_status.name]
        elif block_status in (BlockStatus.REVERTED, BlockStatus.ABORTED):
            # The transaction passed Batcher validations, but the block containing it failed on
            # L1 or L2. Hence, it is yet again waiting to be inserted to a new block.
            return TransactionStatus.RECEIVED

        raise NotImplementedError(f"Handling block status {block_status.name} is not implemented.")

    def __ge__(self, other: object) -> bool:
        if not isinstance(other, TransactionStatus):
            return NotImplemented

        self_not_comparable, other_not_comparable = (
            status not in tx_status_order_relation.keys() for status in (self, other)
        )
        if self_not_comparable or other_not_comparable:
            raise NotImplementedError(
                f"Comparison is not supported between status {self.name} and {other.name}."
            )

        return tx_status_order_relation[self] >= tx_status_order_relation[other]

    def __lt__(self, other: object) -> bool:
        return not self >= other


# Dictionary that represents the TransactionStatus valid flows.
# [NOT_RECEIVED] -> [RECEIVED] -> [PENDING] -> [ACCEPTED_ON_L2] -> [ACCEPTED_ON_L1].
# REJECTED is excluded from the relation since the status of a REJECTED transaction will not
# become ACCEPTED_ON_L2.
tx_status_order_relation: Dict[TransactionStatus, int] = {
    TransactionStatus.NOT_RECEIVED: 0,
    TransactionStatus.RECEIVED: 1,
    TransactionStatus.PENDING: 2,
    TransactionStatus.ACCEPTED_ON_L2: 3,
    TransactionStatus.ACCEPTED_ON_L1: 4,
}


@marshmallow_dataclass.dataclass(frozen=True)
class TransactionInBlockInfo(BaseResponseObject):
    """
    Represents the information regarding a StarkNet transaction that appears in a block.
    """

    # The status of a transaction, see TransactionStatus.
    status: Optional[TransactionStatus]
    # The reason for the transaction failure, if applicable.
    transaction_failure_reason: Optional[TransactionFailureReason]
    # The unique identifier of the block on the active chain containing the transaction.
    block_hash: Optional[int] = field(metadata=fields.optional_block_hash_metadata)
    # The sequence number of the block corresponding to block_hash, which is the number of blocks
    # prior to it in the active chain.
    block_number: Optional[int] = field(metadata=fields.default_optional_block_number_metadata)
    # The index of the transaction within the block corresponding to block_hash.
    transaction_index: Optional[int] = field(
        metadata=fields.default_optional_transaction_index_metadata
    )

    def __post_init__(self):
        super().__post_init__()

        # Validate NOT_RECEIVED/nonexistent status matches missing execution fields.
        execution_fields = (
            self.block_hash,
            self.block_number,
            self.transaction_index,
            self.transaction_failure_reason,
        )
        if self.status is None or self.status in (
            TransactionStatus.NOT_RECEIVED,
            TransactionStatus.RECEIVED,
        ):
            assert all(field is None for field in execution_fields), (
                "Transaction execution fields (block hash, block number, index in block, etc.) "
                "must not appear in a transaction that is not yet in a block, "
                "or when status is None. "
                f"Status: {self.status}. Execution fields: block_hash: {self.block_hash}, "
                f"block_number: {self.block_number}, transaction_index: {self.transaction_index}, "
                f"transaction_failure_reason: {self.transaction_failure_reason}."
            )

            return

        # Validate REJECTED status matches existing failure reason field.
        tx_rejected = self.status is TransactionStatus.REJECTED
        has_failure_info = self.transaction_failure_reason is not None
        assert (
            tx_rejected == has_failure_info
        ), "A rejected transaction must contain failure information, and vice versa."

        # Validate PENDING status matches missing created block fields.
        if self.status is TransactionStatus.PENDING:
            assert (
                self.block_hash is None and self.block_number is None
            ), "Block hash and block number must not appear in a pending transaction."

            return

        # Validate ACCEPTED_ON_L1/2 status matches existing missing created block fields.
        minimal_remaining_status = TransactionStatus.ACCEPTED_ON_L2
        assert tx_rejected or self.status >= minimal_remaining_status, (
            f"Unexpected transaction status: {self.status}; expected status to be at least "
            f"{minimal_remaining_status.name}."
        )
        if not tx_rejected:
            assert all(
                field is not None
                for field in (self.block_hash, self.block_number, self.transaction_index)
            ), (
                "Block hash, block number and transaction index in block must appear in an "
                "accepted transaction."
            )


@marshmallow_dataclass.dataclass(frozen=True)
class TransactionSpecificInfo(BaseResponseObject):
    tx_type: ClassVar[TransactionType]

    @classmethod
    def from_internal(cls, internal_tx: InternalTransaction) -> "TransactionSpecificInfo":
        if isinstance(internal_tx, InternalDeploy):
            return DeploySpecificInfo.from_internal_deploy(internal_tx=internal_tx)
        elif isinstance(internal_tx, InternalInvokeFunction):
            return InvokeSpecificInfo.from_internal_invoke(internal_tx=internal_tx)
        else:
            raise NotImplementedError(f"No response object for {internal_tx}.")


@marshmallow_dataclass.dataclass(frozen=True)
class DeploySpecificInfo(TransactionSpecificInfo):
    contract_address: int = field(metadata=fields.contract_address_metadata)
    contract_address_salt: int = field(metadata=fields.contract_address_salt_metadata)
    class_hash: Optional[int] = field(metadata=fields.OptionalClassHashField.metadata())
    constructor_calldata: List[int] = field(metadata=fields.call_data_as_hex_metadata)
    transaction_hash: int = field(metadata=fields.transaction_hash_metadata)
    tx_type: ClassVar[TransactionType] = TransactionType.DEPLOY

    @classmethod
    def from_internal_deploy(cls, internal_tx: InternalDeploy) -> "DeploySpecificInfo":
        return cls(
            contract_address=internal_tx.contract_address,
            contract_address_salt=internal_tx.contract_address_salt,
            class_hash=from_bytes(internal_tx.contract_hash),
            constructor_calldata=internal_tx.constructor_calldata,
            transaction_hash=internal_tx.hash_value,
        )


@marshmallow_dataclass.dataclass(frozen=True)
class InvokeSpecificInfo(TransactionSpecificInfo):
    contract_address: int = field(metadata=fields.contract_address_metadata)
    entry_point_selector: int = field(metadata=fields.entry_point_selector_metadata)
    entry_point_type: EntryPointType
    calldata: List[int] = field(metadata=fields.call_data_as_hex_metadata)
    signature: List[int] = field(metadata=fields.signature_as_hex_metadata)
    transaction_hash: int = field(metadata=fields.transaction_hash_metadata)
    max_fee: int = field(metadata=fields.fee_metadata)
    tx_type: ClassVar[TransactionType] = TransactionType.INVOKE_FUNCTION

    @classmethod
    def from_internal_invoke(cls, internal_tx: InternalInvokeFunction) -> "InvokeSpecificInfo":
        return cls(
            contract_address=internal_tx.contract_address,
            entry_point_selector=internal_tx.entry_point_selector,
            entry_point_type=internal_tx.entry_point_type,
            calldata=internal_tx.calldata,
            signature=internal_tx.signature,
            transaction_hash=internal_tx.hash_value,
            max_fee=internal_tx.max_fee,
        )


class TransactionSpecificInfoSchema(OneOfSchema):
    type_schemas: Dict[str, Type[marshmallow.Schema]] = {
        TransactionType.DEPLOY.name: DeploySpecificInfo.Schema,
        TransactionType.INVOKE_FUNCTION.name: InvokeSpecificInfo.Schema,
    }

    def get_obj_type(self, obj: TransactionSpecificInfo) -> str:
        return obj.tx_type.name


TransactionSpecificInfo.Schema = TransactionSpecificInfoSchema


@marshmallow_dataclass.dataclass(frozen=True)
class TransactionInfo(TransactionInBlockInfo):
    """
    Represents the information regarding a StarkNet transaction.
    """

    transaction: Optional[TransactionSpecificInfo]

    @classmethod
    def create(
        cls,
        status: Optional[TransactionStatus],
        transaction: Optional[InternalTransaction] = None,
        transaction_failure_reason: Optional[TransactionFailureReason] = None,
        block_hash: Optional[int] = None,
        block_number: Optional[int] = None,
        transaction_index: Optional[int] = None,
    ) -> "TransactionInfo":
        return cls(
            transaction=None
            if transaction is None
            else TransactionSpecificInfo.from_internal(internal_tx=transaction),
            status=status,
            transaction_failure_reason=transaction_failure_reason,
            block_hash=block_hash,
            block_number=block_number,
            transaction_index=transaction_index,
        )

    def __post_init__(self):
        super().__post_init__()

        if self.status is not None and self.status is not TransactionStatus.NOT_RECEIVED:
            assert (
                self.transaction is not None
            ), "A received transaction must be included in TransactionInfo object."


@dataclasses.dataclass(frozen=True)
class L1ToL2Message(BaseResponseObject):
    """
    Represents a StarkNet L1-to-L2 message.
    """

    from_address: str = field(
        metadata=everest_fields.EthAddressField.metadata(field_name="from_address")
    )
    to_address: int = field(metadata=fields.L2AddressField.metadata(field_name="to_address"))
    selector: int = field(metadata=fields.entry_point_selector_metadata)
    payload: List[int] = field(metadata=fields.felt_as_hex_list_metadata)
    nonce: Optional[int] = field(metadata=fields.optional_nonce_metadata)


@dataclasses.dataclass(frozen=True)
class L2ToL1Message(BaseResponseObject):
    """
    Represents a StarkNet L2-to-L1 message.
    """

    from_address: int = field(metadata=fields.L2AddressField.metadata(field_name="from_address"))
    to_address: str = field(
        metadata=everest_fields.EthAddressField.metadata(field_name="to_address")
    )
    payload: List[int] = field(metadata=fields.felt_as_hex_list_metadata)


@marshmallow_dataclass.dataclass(frozen=True)
class TransactionExecution(BaseResponseObject):
    """
    Represents a receipt of an executed transaction.
    """

    # The index of the transaction within the block.
    transaction_index: Optional[int] = field(
        metadata=fields.default_optional_transaction_index_metadata
    )
    # A unique identifier of the transaction.
    transaction_hash: Optional[int] = field(metadata=fields.optional_transaction_hash_metadata)
    # L1-to-L2 messages.
    l1_to_l2_consumed_message: Optional[L1ToL2Message]
    # L2-to-L1 messages.
    l2_to_l1_messages: List[L2ToL1Message]
    # Events emitted during the execution of the transaction.
    events: List[Event]
    # The resources needed by the transaction.
    execution_resources: Optional[ExecutionResources]
    # The actual fee that was charged.
    actual_fee: Optional[int] = field(metadata=fields.optional_fee_metadata)


@marshmallow_dataclass.dataclass(frozen=True)
class TransactionReceipt(TransactionExecution, TransactionInBlockInfo):
    """
    Represents a receipt of a StarkNet transaction;
    i.e., the information regarding its execution and the block it appears in.
    """

    def __post_init__(self):
        super().__post_init__()

        if self.status is TransactionStatus.REJECTED and self.has_execution_info:
            raise AssertionError("A rejected transaction cannot have execution info.")

        assert self.transaction_hash is not None, "A receipt must include a transaction_hash."

    @property
    def has_execution_info(self) -> bool:
        """
        Returns whether the transaction has execution info.
        """
        return (
            self.l1_to_l2_consumed_message is not None
            or self.execution_resources is not None
            or len(self.l2_to_l1_messages) > 0
            or len(self.events) > 0
        )

    @classmethod
    def from_tx_info(
        cls,
        transaction_hash: int,
        tx_info: TransactionInBlockInfo,
        actual_fee: Optional[int],
        l1_to_l2_consumed_message: Optional[L1ToL2Message] = None,
        l2_to_l1_messages: Optional[List[L2ToL1Message]] = None,
        events: Optional[List[Event]] = None,
        execution_resources: Optional[ExecutionResources] = None,
    ) -> "TransactionReceipt":
        return cls(
            l1_to_l2_consumed_message=l1_to_l2_consumed_message,
            l2_to_l1_messages=[] if l2_to_l1_messages is None else l2_to_l1_messages,
            events=[] if events is None else events,
            execution_resources=execution_resources,
            actual_fee=actual_fee,
            transaction_hash=transaction_hash,
            status=tx_info.status,
            transaction_failure_reason=tx_info.transaction_failure_reason,
            block_hash=tx_info.block_hash,
            block_number=tx_info.block_number,
            transaction_index=tx_info.transaction_index,
        )


@marshmallow_dataclass.dataclass(frozen=True)
class StorageEntry(BaseResponseObject):
    """
    Represents a value stored in a single contract storage entry.
    """

    key: int = field(metadata=everest_fields.felt_metadata(name_in_error_message="key"))
    value: int = field(metadata=everest_fields.felt_metadata(name_in_error_message="value"))


@marshmallow_dataclass.dataclass(frozen=True)
class DeployedContract(BaseResponseObject):
    """
    Represents a newly deployed contract in a block state update.
    """

    address: int = field(metadata=fields.L2AddressField.metadata(field_name="address"))
    contract_hash: bytes = field(metadata=fields.contract_hash_metadata)


@marshmallow_dataclass.dataclass(frozen=True)
class StateDiff(BaseResponseObject):
    """
    Represents the difference in the StarkNet state induced by applying a block's transactions.
    """

    storage_diffs: Dict[int, List[StorageEntry]] = field(
        metadata=dict(
            marshmallow_field=mfields.Dict(
                keys=fields.L2AddressField.get_marshmallow_field(
                    required=True,
                    load_default=marshmallow.utils.missing,
                ),
                values=mfields.List(mfields.Nested(StorageEntry.Schema)),
            )
        )
    )

    deployed_contracts: List[DeployedContract]


@marshmallow_dataclass.dataclass(frozen=True)
class BlockStateUpdate(BaseResponseObject):
    """
    Represents a response block state update.
    """

    block_hash: Optional[int] = field(metadata=fields.optional_block_hash_metadata)
    new_root: bytes = field(metadata=fields.state_root_metadata)
    old_root: bytes = field(metadata=fields.state_root_metadata)
    state_diff: StateDiff


@dataclasses.dataclass(frozen=True)
class OrderedL2ToL1MessageResponse(ValidatedDataclass):
    """
    See datails in OrderedL2ToL1Message's documentation.
    """

    order: int = field(metadata=sequential_id_metadata("L2-to-L1 message order"))
    to_address: str = field(metadata=everest_fields.EthAddressField.metadata("to_address"))
    payload: List[int] = field(metadata=fields.felt_as_hex_list_metadata)

    @classmethod
    def from_internal(
        cls, messages: List[OrderedL2ToL1Message]
    ) -> List["OrderedL2ToL1MessageResponse"]:
        return [
            cls(
                order=message.order,
                to_address=Web3.toChecksumAddress(to_bytes(message.to_address, 20)),
                payload=message.payload,
            )
            for message in messages
        ]


@dataclasses.dataclass(frozen=True)
class OrderedEventResponse(ValidatedDataclass):
    """
    See datails in OrderedEvent's documentation.
    """

    order: int = field(metadata=sequential_id_metadata("Event order"))
    keys: List[int] = field(metadata=fields.felt_as_hex_list_metadata)
    data: List[int] = field(metadata=fields.felt_as_hex_list_metadata)

    @classmethod
    def from_internal(cls, events: List[OrderedEvent]) -> List["OrderedEventResponse"]:
        return [cls(order=event.order, keys=event.keys, data=event.data) for event in events]


# NOTE: This dataclass isn't validated due to a forward-declaration issue.
@marshmallow_dataclass.dataclass(frozen=True)
class FunctionInvocation(SerializableMarshmallowDataclass):
    """
    A lean version of CallInfo class, containing merely the information relevant for the user.
    """

    # Static info.
    caller_address: int = field(
        metadata=fields.L2AddressField.metadata(field_name="caller_address")
    )
    contract_address: int = field(metadata=fields.contract_address_metadata)
    code_address: Optional[int] = field(metadata=fields.optional_code_address_metadata)
    selector: Optional[int] = field(metadata=fields.optional_entry_point_selector_metadata)
    entry_point_type: Optional[EntryPointType]
    calldata: List[int] = field(metadata=fields.call_data_as_hex_metadata)

    # Execution info.
    result: List[int] = field(metadata=fields.retdata_as_hex_metadata)
    execution_resources: ExecutionResources
    internal_calls: List["FunctionInvocation"] = field(
        metadata=dict(
            marshmallow_field=mfields.List(mfields.Nested(lambda: FunctionInvocation.Schema()))
        )
    )
    events: List[OrderedEventResponse]
    messages: List[OrderedL2ToL1MessageResponse]

    @classmethod
    def from_internal_version(cls, call_info: CallInfo) -> "FunctionInvocation":
        return cls(
            caller_address=call_info.caller_address,
            contract_address=call_info.contract_address,
            code_address=call_info.code_address,
            selector=call_info.entry_point_selector,
            entry_point_type=call_info.entry_point_type,
            calldata=call_info.calldata,
            result=call_info.retdata,
            execution_resources=call_info.execution_resources,
            internal_calls=[
                cls.from_internal_version(call_info=internal_call)
                for internal_call in call_info.internal_calls
            ],
            events=OrderedEventResponse.from_internal(events=call_info.events),
            messages=OrderedL2ToL1MessageResponse.from_internal(
                messages=call_info.l2_to_l1_messages
            ),
        )


@marshmallow_dataclass.dataclass(frozen=True)
class TransactionTrace(BaseResponseObject):
    """
    Represents the trace of a StarkNet transaction execution,
    including internal calls.
    """

    # An object describing the invocation of a specific function.
    function_invocation: FunctionInvocation
    signature: List[int] = field(metadata=fields.signature_as_hex_metadata)


@marshmallow_dataclass.dataclass(frozen=True)
class StarknetBlock(BaseResponseObject):
    """
    Represents a response StarkNet block.
    """

    block_hash: Optional[int] = field(metadata=fields.optional_block_hash_metadata)
    parent_block_hash: int = field(metadata=fields.block_hash_metadata)
    block_number: Optional[int] = field(metadata=fields.default_optional_block_number_metadata)
    state_root: Optional[bytes] = field(metadata=fields.optional_state_root_metadata)
    status: Optional[BlockStatus]
    transactions: Tuple[TransactionSpecificInfo, ...] = field(
        metadata=dict(
            marshmallow_field=VariadicLengthTupleField(
                mfields.Nested(TransactionSpecificInfo.Schema)
            )
        )
    )
    timestamp: int = field(metadata=fields.timestamp_metadata)
    transaction_receipts: Optional[Tuple[TransactionExecution, ...]] = field(
        metadata=dict(
            marshmallow_field=VariadicLengthTupleField(
                mfields.Nested(TransactionExecution.Schema), allow_none=True
            )
        )
    )

    @classmethod
    def create(
        cls: Type[TBlockInfo],
        block_hash: Optional[int],
        parent_block_hash: int,
        block_number: Optional[int],
        state_root: Optional[bytes],
        transactions: Iterable[InternalTransaction],
        timestamp: int,
        transaction_receipts: Optional[Tuple[TransactionExecution, ...]],
        status: Optional[BlockStatus],
    ) -> TBlockInfo:
        return cls(
            block_hash=block_hash,
            parent_block_hash=parent_block_hash,
            block_number=block_number,
            state_root=state_root,
            transactions=tuple(
                TransactionSpecificInfo.from_internal(internal_tx=tx) for tx in transactions
            ),
            timestamp=timestamp,
            transaction_receipts=transaction_receipts,
            status=status,
        )

    def __post_init__(self):
        super().__post_init__()

        if self.status in (BlockStatus.ABORTED, BlockStatus.REVERTED):
            assert (
                self.transaction_receipts is None
            ), "Aborted and reverted blocks must not have transaction receipts."

            return

        # Validate PENDING status matches missing created block fields.
        created_block_fields = (self.block_hash, self.block_number, self.state_root)
        if self.status is BlockStatus.PENDING:
            assert all(
                field is None for field in created_block_fields
            ), "Block hash, block number, state_root must not appear in a pending block."
        else:
            assert all(
                field is not None for field in created_block_fields
            ), "Block hash, block number, state_root must appear in a created block."
