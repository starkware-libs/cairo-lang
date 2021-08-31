import dataclasses
from typing import Any, Dict, Type

import marshmallow
import marshmallow.fields as mfields

from starkware.starknet.definitions import constants
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starkware_utils.field_validators import (
    validate_length,
    validate_non_negative,
    validate_positive,
)
from starkware.starkware_utils.marshmallow_dataclass_fields import BytesAsHex, IntAsStr
from starkware.starkware_utils.validated_fields import (
    RangeValidatedField,
    int_as_hex_metadata,
    sequential_id_metadata,
)

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
)


def felt_metadata(name_in_error_message: str) -> Dict[str, Any]:
    return int_as_hex_metadata(
        validated_field=dataclasses.replace(FeltField, name_in_error_message=name_in_error_message)
    )


felt_list_metadata = dict(marshmallow_field=mfields.List(IntAsStr(validate=FeltField.validate)))

call_data_metadata = felt_list_metadata

ContractAddressField = RangeValidatedField(
    lower_bound=constants.CONTRACT_ADDRESS_LOWER_BOUND,
    upper_bound=constants.CONTRACT_ADDRESS_UPPER_BOUND,
    name_in_error_message="Contract address",
    out_of_range_error_code=StarknetErrorCode.OUT_OF_RANGE_CONTRACT_ADDRESS,
)

contract_address_metadata = int_as_hex_metadata(validated_field=ContractAddressField)


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

contract_hash_metadata = dict(marshmallow_field=BytesAsHex(required=True))

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
)

entry_point_selector_metadata = int_as_hex_metadata(validated_field=EntryPointSelectorField)

EntryPointOffsetField = RangeValidatedField(
    lower_bound=constants.ENTRY_POINT_OFFSET_LOWER_BOUND,
    upper_bound=constants.ENTRY_POINT_OFFSET_UPPER_BOUND,
    name_in_error_message="Entry point offset",
    out_of_range_error_code=StarknetErrorCode.OUT_OF_RANGE_ENTRY_POINT_OFFSET,
)

entry_point_offset_metadata = int_as_hex_metadata(validated_field=EntryPointOffsetField)

global_state_commitment_tree_height_metadata = dict(
    marshmallow_field=mfields.Integer(
        strict=True,
        required=True,
        validate=validate_non_negative("global_state_commitment_tree_height"),
    )
)

state_root_metadata = dict(marshmallow_field=BytesAsHex(required=True))


def tx_id_dict_keys_metadata(values_schema: Type[marshmallow.Schema]) -> Dict[str, mfields.Dict]:
    return dict(
        marshmallow_field=mfields.Dict(
            keys=mfields.Integer(required=True, validate=validate_non_negative("transaction ID")),
            values=mfields.Nested(values_schema),
        )
    )


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
