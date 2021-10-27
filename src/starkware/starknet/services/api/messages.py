import dataclasses
from dataclasses import field
from enum import Enum, auto
from typing import List

from services.everest.definitions import fields as everest_fields
from starkware.cairo.bootloader.compute_fact import keccak_ints
from starkware.starknet.business_logic.internal_transaction import InternalInvokeFunction
from starkware.starknet.definitions import fields
from starkware.starknet.services.api.contract_definition import EntryPointType
from starkware.starkware_utils.validated_dataclass import ValidatedDataclass


class MessageType(Enum):
    L1_TO_L2 = 0
    L2_TO_L1 = auto()


@dataclasses.dataclass(frozen=True)
class StarknetMessage(ValidatedDataclass):
    """
    The direct constructor is private; to create a StarknetMessage object, use the appropriate
    classmethod.
    """

    from_address: int = field(metadata=fields.felt_metadata(name_in_error_message="from address"))
    to_address: int = field(metadata=fields.felt_metadata(name_in_error_message="to address"))
    payload: List[int] = field(metadata=fields.felt_list_metadata)
    message_type: MessageType

    def __post_init__(self):
        """
        The validation changes according to the message type.
        """
        if self.message_type is MessageType.L1_TO_L2:
            l1_address, l2_address = self.from_address, self.to_address
        elif self.message_type is MessageType.L2_TO_L1:
            l1_address, l2_address = self.to_address, self.from_address
        else:
            raise NotImplementedError

        assert everest_fields.EthAddressIntField.is_valid(
            value=l1_address
        ), f"L1 address is not valid. Got: {l1_address}."
        assert fields.ContractAddressField.is_valid(
            value=l2_address
        ), f"L2 address is not valid. Got: {l2_address}."

    def encode(self) -> List[int]:
        return [self.from_address, self.to_address, len(self.payload)] + self.payload

    def get_hash(self) -> str:
        return keccak_ints(values=self.encode())

    @classmethod
    def create_message_to_l1(
        cls, from_address: int, to_address: int, payload: List[int]
    ) -> "StarknetMessage":
        return cls(
            from_address=from_address,
            to_address=to_address,
            payload=payload,
            message_type=MessageType.L2_TO_L1,
        )

    @classmethod
    def create_message_to_l2(
        cls, from_address: int, to_address: int, l1_handler_selector: int, payload: List[int]
    ) -> "StarknetMessage":
        return cls(
            from_address=from_address,
            to_address=to_address,
            payload=[l1_handler_selector, *payload],
            message_type=MessageType.L1_TO_L2,
        )

    @staticmethod
    def get_message_hash_from_tx(tx: InternalInvokeFunction) -> str:
        assert (
            tx.entry_point_type is EntryPointType.L1_HANDLER
        ), f"Transaction must be of type L1_HANDLER. Got: {tx.entry_point_type.name}."

        return StarknetMessage.create_message_to_l2(
            from_address=tx.calldata[0],
            to_address=tx.contract_address,
            l1_handler_selector=tx.entry_point_selector,
            payload=tx.calldata[1:],
        ).get_hash()
