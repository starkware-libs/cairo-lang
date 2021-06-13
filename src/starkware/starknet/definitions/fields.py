import marshmallow.fields as mfields

from starkware.starknet.definitions import constants
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starkware_utils.field_validators import validate_non_negative, validate_positive
from starkware.starkware_utils.marshmallow_dataclass_fields import BytesAsHex, IntAsStr
from starkware.starkware_utils.validated_fields import (
    RangeValidatedField, int_as_hex_metadata, sequential_id_metadata)

# Fields data: validation data, dataclass metadata.

block_id_metadata = sequential_id_metadata(field_name='block_id')

previous_block_id_metadata = sequential_id_metadata(
    field_name='previous_block_id', allow_previous_id=True)

sequence_number_metadata = sequential_id_metadata(field_name='sequence_number')

CallDataElementField = RangeValidatedField(
    lower_bound=constants.CALL_DATA_ELEMENT_LOWER_BOUND,
    upper_bound=constants.CALL_DATA_ELEMENT_UPPER_BOUND,
    name_in_error_message='Call data element',
    out_of_range_error_code=StarknetErrorCode.OUT_OF_RANGE_ENTRY_POINT_SELECTOR)

call_data_metadata = dict(
    marshmallow_field=mfields.List(IntAsStr(validate=CallDataElementField.validate)))

ContractAddressField = RangeValidatedField(
    lower_bound=constants.CONTRACT_ADDRESS_LOWER_BOUND,
    upper_bound=constants.CONTRACT_ADDRESS_UPPER_BOUND,
    name_in_error_message='Contract address',
    out_of_range_error_code=StarknetErrorCode.OUT_OF_RANGE_CONTRACT_ADDRESS)

contract_address_metadata = int_as_hex_metadata(validated_field=ContractAddressField)

contract_definitions_metadata = dict(marshmallow_field=mfields.Dict(keys=BytesAsHex))

contract_hash_metadata = dict(marshmallow_field=BytesAsHex(required=True))

contract_storage_merkle_height_metadata = dict(
    marshmallow_field=mfields.Integer(
        strict=True, required=True, validate=validate_positive('contract_storage_merkle_height')))

EntryPointSelectorField = RangeValidatedField(
    lower_bound=constants.ENTRY_POINT_SELECTOR_LOWER_BOUND,
    upper_bound=constants.ENTRY_POINT_SELECTOR_UPPER_BOUND,
    name_in_error_message='Entry point selector',
    out_of_range_error_code=StarknetErrorCode.OUT_OF_RANGE_ENTRY_POINT_SELECTOR)

entry_point_selector_metadata = int_as_hex_metadata(validated_field=EntryPointSelectorField)

EntryPointOffsetField = RangeValidatedField(
    lower_bound=constants.ENTRY_POINT_OFFSET_LOWER_BOUND,
    upper_bound=constants.ENTRY_POINT_OFFSET_UPPER_BOUND,
    name_in_error_message='Entry point offset',
    out_of_range_error_code=StarknetErrorCode.OUT_OF_RANGE_ENTRY_POINT_OFFSET)

entry_point_offset_metadata = int_as_hex_metadata(validated_field=EntryPointOffsetField)

global_state_merkle_height_metadata = dict(
    marshmallow_field=mfields.Integer(
        strict=True, required=True, validate=validate_non_negative('global_state_merkle_height')))

state_root_metadata = dict(marshmallow_field=BytesAsHex(required=True))

timestamp_metadata = dict(
    marshmallow_field=mfields.Integer(
        strict=True, required=True, validate=validate_non_negative('timestamp')))

invoke_tx_n_steps_metadata = dict(
    marshmallow_field=mfields.Integer(
        strict=True, required=True, validate=validate_non_negative('invoke_tx_n_steps')))
