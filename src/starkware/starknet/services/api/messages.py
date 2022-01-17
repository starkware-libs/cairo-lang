import dataclasses
from dataclasses import field
from enum import Enum, auto
from typing import List

from services.everest.definitions import fields as everest_fields
from starkware.cairo.bootloader.compute_fact import keccak_ints
from starkware.starknet.business_logic.internal_transaction import InternalInvokeFunction
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.services.api.contract_definition import EntryPointType
from starkware.starkware_utils.error_handling import stark_assert
from starkware.starkware_utils.validated_dataclass import ValidatedDataclass


class MessageType(Enum):
    L1_TO_L2 = 0
    L2_TO_L1 = auto()


@dataclasses.dataclass(frozen=True)
class StarknetMessageToL1(ValidatedDataclass):
    """
    A StarkNet Message from L2 to L1.
    """

    from_address: int = field(
        metadata=everest_fields.felt_metadata(name_in_error_message="from_address")
    )
    to_address: int = field(
        metadata=everest_fields.EthAddressIntField.metadata(field_name="to_address")
    )
    payload: List[int] = field(metadata=fields.felt_list_metadata)

    def encode(self) -> List[int]:
        return [self.from_address, self.to_address, len(self.payload)] + self.payload

    def get_hash(self) -> str:
        return keccak_ints(values=self.encode())


@dataclasses.dataclass(frozen=True)
class StarknetMessageToL2(ValidatedDataclass):
    """
    A StarkNet Message from L1 to L2.
    """

    from_address: int = field(
        metadata=everest_fields.EthAddressIntField.metadata(field_name="from_address")
    )
    to_address: int = field(
        metadata=everest_fields.felt_metadata(name_in_error_message="to_address")
    )
    l1_handler_selector: int
    payload: List[int] = field(metadata=fields.felt_list_metadata)
    nonce: int = field(metadata=everest_fields.felt_metadata(name_in_error_message="nonce"))

    def encode(self) -> List[int]:
        return [
            self.from_address,
            self.to_address,
            self.nonce,
            self.l1_handler_selector,
            len(self.payload),
            *self.payload,
        ]

    def get_hash(self) -> str:
        return keccak_ints(values=self.encode())

    @staticmethod
    def get_message_hash_from_tx(tx: InternalInvokeFunction) -> str:
        assert (
            tx.entry_point_type is EntryPointType.L1_HANDLER
        ), f"Transaction must be of type L1_HANDLER. Got: {tx.entry_point_type.name}."

        stark_assert(
            tx.nonce is not None,
            code=StarknetErrorCode.UNEXPECTED_FAILURE,
            message="L1 handlers must include a nonce.",
        )

        assert tx.nonce is not None, "L1 handlers must include a nonce."

        return StarknetMessageToL2(
            from_address=tx.calldata[0],
            to_address=tx.contract_address,
            l1_handler_selector=tx.entry_point_selector,
            payload=tx.calldata[1:],
            nonce=tx.nonce,
        ).get_hash()
