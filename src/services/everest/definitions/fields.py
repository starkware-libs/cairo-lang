import dataclasses
import random
import string
from typing import Any, Dict, List, Optional, Type

import marshmallow.fields as mfields
from web3.types import ChecksumAddress

from services.everest.definitions import constants
from starkware.crypto.signature.signature import FIELD_PRIME
from starkware.eth.web3_wrapper import Web3
from starkware.python.utils import initialize_random
from starkware.starkware_utils.error_handling import StarkErrorCode
from starkware.starkware_utils.field_validators import validate_non_negative
from starkware.starkware_utils.marshmallow_dataclass_fields import StrictRequiredInteger
from starkware.starkware_utils.validated_fields import RangeValidatedField, ValidatedField

# Fields data: validation data, dataclass metadata.
tx_id_marshmallow_field = StrictRequiredInteger(validate=validate_non_negative("tx_id"))
tx_id_field_metadata = dict(marshmallow_field=tx_id_marshmallow_field)


# Fact Registry Address.
class EthAddressTypeField(ValidatedField[str]):
    """
    A field representation of an Ethereum address.
    """

    def error_message(self, value: str) -> str:
        return f"{self.name} {value} is out of range / not checksummed."

    # Randomization.
    def get_random_value(self, random_object: Optional[random.Random] = None) -> str:
        r = initialize_random(random_object=random_object)
        raw_address = "".join(r.choices(population=string.hexdigits, k=40))

        return Web3.to_checksum_address(value=f"0x{raw_address}")  # type: ignore

    # Validation.
    def is_valid(self, value: str) -> bool:
        return Web3.is_checksum_address(value)  # type: ignore

    def get_invalid_values(self) -> List[str]:
        return [
            "0x0Fa81Ec60fe5422d49174F1abdfdC06a9F1c52F2",  # Not checksummed.
            self.get_random_value()[:-1],  # Too short address.
            self.get_random_value() + "0",  # type: ignore # Too long address.
        ]

    # Serialization.
    def get_marshmallow_type(self) -> Type[mfields.Field]:
        return mfields.String

    def convert_valid_to_checksum(self, value: str) -> ChecksumAddress:
        self.validate(value=value)
        # This won't change value. It will only allow the function to return value as return
        # ChecksumAddress.
        return Web3.to_checksum_address(value=value)  # type: ignore


FactRegistryField = EthAddressTypeField(
    name="Address of fact registry", error_code=StarkErrorCode.INVALID_CONTRACT_ADDRESS
)

EthAddressField = EthAddressTypeField(
    name="Ethereum address", error_code=StarkErrorCode.INVALID_ETH_ADDRESS
)

EthAddressIntField = RangeValidatedField(
    lower_bound=constants.ETH_ADDRESS_LOWER_BOUND,
    upper_bound=constants.ETH_ADDRESS_UPPER_BOUND,
    name="Ethereum address",
    error_code=StarkErrorCode.OUT_OF_RANGE_ETH_ADDRESS,
    formatter=None,
)

FeltField = RangeValidatedField(
    lower_bound=0,
    upper_bound=FIELD_PRIME,
    name="Field element",
    error_code=StarkErrorCode.OUT_OF_RANGE_FIELD_ELEMENT,
    formatter=hex,
)


def get_bounded_int_range_validator(
    lower_bound: int = 0, upper_bound: int = FIELD_PRIME
) -> RangeValidatedField:
    return RangeValidatedField(
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        name=f"Integer in range [{lower_bound}, {upper_bound})",
        error_code=StarkErrorCode.OUT_OF_RANGE_FIELD_ELEMENT,
        formatter=hex,
    )


def felt(name_in_error_message: str) -> RangeValidatedField:
    return dataclasses.replace(FeltField, name=name_in_error_message)


def felt_metadata(name_in_error_message: str) -> Dict[str, Any]:
    return felt(name_in_error_message=name_in_error_message).metadata()


def format_felt_list(felts: List[int]) -> str:
    return f"[{', '.join([FeltField.format(felt) for felt in felts])}]"
