import dataclasses
from typing import Any, Dict, Type

import marshmallow
import marshmallow.fields as mfields

from starkware.python.utils import from_bytes
from starkware.starknet.definitions import constants
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starkware_utils.field_validators import (
    validate_length,
    validate_non_negative,
    validate_positive,
)
from starkware.starkware_utils.marshmallow_dataclass_fields import BytesAsHex, IntAsStr
from starkware.starkware_utils.validated_fields import RangeValidatedField, sequential_id_metadata

# Fields data: validation data, dataclass metadata.

block_id_metadata = sequential_id_metadata(field_name="block_id")

previous_block_id_metadata = sequential_id_metadata(
    field_name="previous_block_id", allow_previous_id=True
)

sequence_number_metadata = sequential_id_metadata(field_name="sequence_number")

FeltField = RangeValidatedField(
    lower_bound=constants.FELT_LOWER_BOUND,
    upper_bound=constants.FELT_UPPER_BOUND,
    name_in_error_message="Field element",
    out_of_range_error_code=StarknetErrorCode.INVALID_FIELD_ELEMENT,
    formatter=hex,
)


def felt_metadata(name_in_error_message: str) -> Dict[str, Any]:
    return dataclasses.replace(FeltField, name_in_error_message=name_in_error_message).metadata()


felt_list_metadata = dict(marshmallow_field=mfields.List(IntAsStr(validate=FeltField.validate)))

call_data_metadata = felt_list_metadata
signature_metadata = felt_list_metadata

ContractAddressField = RangeValidatedField(
    lower_bound=constants.CONTRACT_ADDRESS_LOWER_BOUND,
    upper_bound=constants.CONTRACT_ADDRESS_UPPER_BOUND,
    name_in_error_message="Contract address",
    out_of_range_error_code=StarknetErrorCode.OUT_OF_RANGE_CONTRACT_ADDRESS,
    formatter=hex,
)

contract_address_metadata = ContractAddressField.metadata()

ContractAddressSalt = RangeValidatedField(
    lower_bound=constants.CONTRACT_ADDRESS_SALT_LOWER_BOUND,
    upper_bound=constants.CONTRACT_ADDRESS_SALT_UPPER_BOUND,
    name_in_error_message="Contract salt",
    out_of_range_error_code=StarknetErrorCode.OUT_OF_RANGE_CONTRACT_ADDRESS_SALT,
    formatter=hex,
)

contract_address_salt_metadata = ContractAddressSalt.metadata()

CallerAddressField = RangeValidatedField(
    lower_bound=constants.CALLER_ADDRESS_LOWER_BOUND,
    upper_bound=constants.CALLER_ADDRESS_UPPER_BOUND,
    name_in_error_message="Caller address",
    out_of_range_error_code=StarknetErrorCode.OUT_OF_RANGE_CALLER_ADDRESS,
    formatter=hex,
)

caller_address_metadata = CallerAddressField.metadata()


def bytes_as_hex_dict_keys_metadata(
    values_schema: Type[marshmallow.Schema],
) -> Dict[str, mfields.Dict]:
    width_validator = validate_length(
        field_name="contract hash", length=constants.CONTRACT_HASH_BYTES
    )
    return dict(
        marshmallow_field=mfields.Dict(
            keys=BytesAsHex(required=True, validate=width_validator),
            values=mfields.Nested(values_schema),
        )
    )


contract_definitions_metadata = dict(marshmallow_field=mfields.Dict(keys=BytesAsHex))


def validate_contract_hash(contract_hash: bytes):
    if from_bytes(value=contract_hash, byte_order="big") >= constants.CONTRACT_HASH_UPPER_BOUND:
        raise ValueError(
            f"Contract hash must represent a field element; got: 0x{contract_hash.hex()}."
        )


contract_hash_metadata = dict(
    marshmallow_field=BytesAsHex(required=True, validate=validate_contract_hash),
)

contract_storage_commitment_tree_height_metadata = dict(
    marshmallow_field=mfields.Integer(
        required=True, validate=validate_positive("contract_storage_commitment_tree_height")
    )
)

EntryPointSelectorField = RangeValidatedField(
    lower_bound=constants.ENTRY_POINT_SELECTOR_LOWER_BOUND,
    upper_bound=constants.ENTRY_POINT_SELECTOR_UPPER_BOUND,
    name_in_error_message="Entry point selector",
    out_of_range_error_code=StarknetErrorCode.OUT_OF_RANGE_ENTRY_POINT_SELECTOR,
    formatter=hex,
)

entry_point_selector_metadata = EntryPointSelectorField.metadata()

EntryPointOffsetField = RangeValidatedField(
    lower_bound=constants.ENTRY_POINT_OFFSET_LOWER_BOUND,
    upper_bound=constants.ENTRY_POINT_OFFSET_UPPER_BOUND,
    name_in_error_message="Entry point offset",
    out_of_range_error_code=StarknetErrorCode.OUT_OF_RANGE_ENTRY_POINT_OFFSET,
    formatter=hex,
)

entry_point_offset_metadata = EntryPointOffsetField.metadata()

global_state_commitment_tree_height_metadata = dict(
    marshmallow_field=mfields.Integer(
        strict=True,
        required=True,
        validate=validate_non_negative("global_state_commitment_tree_height"),
    )
)

state_root_metadata = dict(marshmallow_field=BytesAsHex(required=True))

TransactionHashField = RangeValidatedField(
    lower_bound=constants.TRANSACTION_HASH_LOWER_BOUND,
    upper_bound=constants.TRANSACTION_HASH_UPPER_BOUND,
    name_in_error_message="Transaction hash",
    out_of_range_error_code=StarknetErrorCode.OUT_OF_RANGE_TRANSACTION_HASH,
    formatter=hex,
)

transaction_hash_metadata = TransactionHashField.metadata()


timestamp_metadata = dict(
    marshmallow_field=mfields.Integer(
        strict=True, required=True, validate=validate_non_negative("timestamp")
    )
)

invoke_tx_n_steps_metadata = dict(
    marshmallow_field=mfields.Integer(
        strict=True, required=True, validate=validate_non_negative("invoke_tx_n_steps")
    )
)
