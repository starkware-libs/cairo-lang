from dataclasses import field
from typing import Optional

import marshmallow_dataclass

from starkware.cairo.lang.version import __version__ as STARKNET_VERSION
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.general_config import (
    DEFAULT_GAS_PRICE,
    DEFAULT_SEQUENCER_ADDRESS,
)
from starkware.starkware_utils.error_handling import stark_assert_eq, stark_assert_le
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass


@marshmallow_dataclass.dataclass(frozen=True)
class BlockInfo(ValidatedMarshmallowDataclass):
    # The sequence number of the last block created.
    block_number: int = field(metadata=fields.block_number_metadata)

    # Timestamp of the beginning of the last block creation attempt.
    block_timestamp: int = field(metadata=fields.timestamp_metadata)

    # L1 gas price (in Wei) measured at the beginning of the last block creation attempt.
    gas_price: int = field(metadata=fields.gas_price_metadata)

    # The sequencer address of this block.
    sequencer_address: Optional[int] = field(metadata=fields.optional_sequencer_address_metadata)

    # The version of StarkNet system (e.g. "0.10.1").
    starknet_version: Optional[str] = field(metadata=fields.starknet_version_metadata)

    @classmethod
    def empty(cls, sequencer_address: Optional[int]) -> "BlockInfo":
        """
        Returns an empty BlockInfo object; i.e., the one before the first in the chain.
        """
        return cls(
            block_number=-1,
            block_timestamp=0,
            gas_price=0,
            sequencer_address=sequencer_address,
            starknet_version=STARKNET_VERSION,
        )

    @classmethod
    def create_for_testing(
        cls,
        block_number: int,
        block_timestamp: int,
        gas_price: int = DEFAULT_GAS_PRICE,
        sequencer_address: int = DEFAULT_SEQUENCER_ADDRESS,
    ) -> "BlockInfo":
        """
        Returns a BlockInfo object with default gas_price.
        """
        return cls(
            block_number=block_number,
            block_timestamp=block_timestamp,
            gas_price=gas_price,
            sequencer_address=sequencer_address,
            starknet_version=STARKNET_VERSION,
        )

    def validate_legal_progress(self, next_block_info: "BlockInfo"):
        """
        Validates that next_block_info is a legal progress of self.
        """
        # Check that the block number increases by 1.
        stark_assert_eq(
            next_block_info.block_number,
            self.block_number + 1,
            code=StarknetErrorCode.INVALID_BLOCK_NUMBER,
            message="Block number must increase by 1.",
        )

        # Check that block timestamp in not decreasing.
        stark_assert_le(
            self.block_timestamp,
            next_block_info.block_timestamp,
            code=StarknetErrorCode.INVALID_BLOCK_TIMESTAMP,
            message="Block timestamp must not decrease.",
        )
