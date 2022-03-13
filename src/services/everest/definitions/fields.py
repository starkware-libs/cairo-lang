import dataclasses
import random
import string
from typing import Any, ClassVar, Dict, List, Optional

import marshmallow.fields as mfields
from eth_typing import ChecksumAddress
from web3 import Web3

from services.everest.definitions import constants
from starkware.crypto.signature.signature import FIELD_PRIME
from starkware.python.utils import initialize_random
from starkware.starkware_utils.error_handling import StarkErrorCode
from starkware.starkware_utils.field_validators import validate_non_negative
from starkware.starkware_utils.marshmallow_dataclass_fields import StrictRequiredInteger
from starkware.starkware_utils.validated_fields import Field, RangeValidatedField

# Fields data: validation data, dataclass metadata.
tx_id_marshmallow_field = StrictRequiredInteger(validate=validate_non_negative("tx_id"))
tx_id_field_metadata = dict(marshmallow_field=tx_id_marshmallow_field)


# Fact Registry Address.
class EthAddressTypeField(Field[str]):
    """
    A field representation of an Ethereum address.
    """

    error_message: ClassVar[str] = "{name} {value} is out of range / not checksummed."

    def __init__(self, name, error_code):
        super().__init__(name, error_code)

    # Randomization.
    def get_random_value(self, random_object: Optional[random.Random] = None) -> str:
        r = initialize_random(random_object=random_object)
        raw_address = "".join(r.choices(population=string.hexdigits, k=40))
        return Web3.toChecksumAddress(value=f"0x{raw_address}")

    # Validation.
    def is_valid(self, value: str) -> bool:
        return Web3.isChecksumAddress(value)

    def get_invalid_values(self) -> List[str]:
        return [
            "0x0Fa81Ec60fe5422d49174F1abdfdC06a9F1c52F2",  # Not checksummed.
            self.get_random_value()[:-1],  # Too short address.
            self.get_random_value() + "0",  # type: ignore # Too long address.
        ]

    def format_invalid_value_error_message(self, value: str, name: Optional[str] = None) -> str:
        return self.error_message.format(
            name=self.name if name is None else name,
            value=value,
        )

    # Serialization.
    def get_marshmallow_field(self, required: bool, load_default: Any) -> mfields.Field:
        return mfields.String(required=required, load_default=load_default)

    def convert_valid_to_checksum(self, value: str) -> ChecksumAddress:
        self.validate(value=value)
        # This won't change value. It will only allow the function to return value as return
        # ChecksumAddress.
        return Web3.toChecksumAddress(value=value)

    def format(self, value: str) -> str:
        return value


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


def felt(name_in_error_message: str) -> RangeValidatedField:
    return dataclasses.replace(FeltField, name=name_in_error_message)


def felt_metadata(name_in_error_message: str) -> Dict[str, Any]:
    return felt(name_in_error_message=name_in_error_message).metadata()
