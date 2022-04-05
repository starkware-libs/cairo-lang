import dataclasses
from typing import Any, Dict, Type

import marshmallow
import marshmallow.fields as mfields
import marshmallow.utils

from services.everest.definitions import fields as everest_fields
from starkware.python.utils import from_bytes
from starkware.starknet.definitions import constants
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starkware_utils.field_validators import (
    validate_length,
    validate_non_negative,
    validate_positive,
)
from starkware.starkware_utils.marshmallow_dataclass_fields import (
    BytesAsHex,
    IntAsStr,
    StrictRequiredInteger,
)
from starkware.starkware_utils.validated_fields import (
    OptionalField,
    RangeValidatedField,
    sequential_id_metadata,
)

# Fields data: validation data, dataclass metadata.


# Common.

felt_as_hex_list_metadata = dict(
    marshmallow_field=mfields.List(
        everest_fields.FeltField.get_marshmallow_field(
            required=True, load_default=marshmallow.utils.missing
        )
    )
)

felt_list_metadata = dict(
    marshmallow_field=mfields.List(IntAsStr(validate=everest_fields.FeltField.validate))
)


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


timestamp_metadata = dict(
    marshmallow_field=StrictRequiredInteger(validate=validate_non_negative("timestamp"))
)


# Address.

AddressField = RangeValidatedField(
    lower_bound=constants.ADDRESS_LOWER_BOUND,
    upper_bound=constants.ADDRESS_UPPER_BOUND,
    name="Address",
    error_code=StarknetErrorCode.OUT_OF_RANGE_ADDRESS,
    formatter=hex,
)


def address_metadata(name: str, error_code: StarknetErrorCode) -> Dict[str, Any]:
    return dataclasses.replace(AddressField, name=name, error_code=error_code).metadata()


sequencer_address_metadata = address_metadata(
    name="Sequencer address", error_code=StarknetErrorCode.OUT_OF_RANGE_SEQUENCER_ADDRESS
)

caller_address_metadata = address_metadata(
    name="Caller address", error_code=StarknetErrorCode.OUT_OF_RANGE_CALLER_ADDRESS
)

fee_token_address_metadata = address_metadata(
    name="Fee token address", error_code=StarknetErrorCode.OUT_OF_RANGE_CONTRACT_ADDRESS
)


# Nonce.

NonceField = RangeValidatedField(
    lower_bound=constants.NONCE_LOWER_BOUND,
    upper_bound=constants.NONCE_UPPER_BOUND,
    name="Nonce",
    error_code=StarknetErrorCode.OUT_OF_RANGE_NONCE,
    formatter=hex,
)
nonce_metadata = NonceField.metadata()

OptionalNonceField = OptionalField(field=NonceField, none_probability=0)
optional_nonce_metadata = OptionalNonceField.metadata()


# Block.

block_number_metadata = sequential_id_metadata(field_name="Block number", allow_previous_id=True)
default_optional_block_number_metadata = sequential_id_metadata(
    field_name="Block number", required=False, load_default=None
)

BlockHashField = RangeValidatedField(
    lower_bound=0,
    upper_bound=constants.BLOCK_HASH_UPPER_BOUND,
    name="Block hash",
    error_code=StarknetErrorCode.OUT_OF_RANGE_BLOCK_HASH,
    formatter=hex,
)
block_hash_metadata = BlockHashField.metadata()

OptionalBlockHashField = OptionalField(field=BlockHashField, none_probability=0)
optional_block_hash_metadata = OptionalBlockHashField.metadata()

default_optional_transaction_index_metadata = sequential_id_metadata(
    field_name="Transaction index", required=False, load_default=None
)


# InvokeFunction.

call_data_metadata = felt_list_metadata
call_data_as_hex_metadata = felt_as_hex_list_metadata
signature_as_hex_metadata = felt_as_hex_list_metadata
signature_metadata = felt_list_metadata
retdata_as_hex_metadata = felt_as_hex_list_metadata


# Contract address.

L2AddressField = RangeValidatedField(
    lower_bound=constants.L2_ADDRESS_LOWER_BOUND,
    upper_bound=constants.L2_ADDRESS_UPPER_BOUND,
    name="Contract address",
    error_code=StarknetErrorCode.OUT_OF_RANGE_CONTRACT_ADDRESS,
    formatter=hex,
)
contract_address_metadata = L2AddressField.metadata(field_name="contract address")

OptionalCodeAddressField = OptionalField(
    field=dataclasses.replace(L2AddressField, name="Code address"), none_probability=0
)
optional_code_address_metadata = OptionalCodeAddressField.metadata()

ContractAddressSalt = everest_fields.felt(name_in_error_message="Contract salt")
contract_address_salt_metadata = ContractAddressSalt.metadata()


# Contract hash.


def validate_contract_hash(contract_hash: bytes):
    if from_bytes(value=contract_hash, byte_order="big") >= constants.CONTRACT_HASH_UPPER_BOUND:
        raise ValueError(
            f"Contract hash must represent a field element; got: 0x{contract_hash.hex()}."
        )


contract_hash_metadata = dict(
    marshmallow_field=BytesAsHex(required=True, validate=validate_contract_hash),
)

non_required_contract_hash_metadata = dict(
    marshmallow_field=BytesAsHex(required=False, validate=validate_contract_hash),
)


ClassHashField = RangeValidatedField(
    lower_bound=0,
    upper_bound=constants.CONTRACT_HASH_UPPER_BOUND,
    name="class_hash",
    error_code=StarknetErrorCode.OUT_OF_RANGE_CONTRACT_HASH,
    formatter=hex,
)

OptionalClassHashField = OptionalField(field=ClassHashField, none_probability=0)


# Entry point.

EntryPointSelectorField = RangeValidatedField(
    lower_bound=constants.ENTRY_POINT_SELECTOR_LOWER_BOUND,
    upper_bound=constants.ENTRY_POINT_SELECTOR_UPPER_BOUND,
    name="Entry point selector",
    error_code=StarknetErrorCode.OUT_OF_RANGE_ENTRY_POINT_SELECTOR,
    formatter=hex,
)
entry_point_selector_metadata = EntryPointSelectorField.metadata()

OptionalEntryPointSelectorField = OptionalField(field=EntryPointSelectorField, none_probability=0)
optional_entry_point_selector_metadata = OptionalEntryPointSelectorField.metadata()

EntryPointOffsetField = RangeValidatedField(
    lower_bound=constants.ENTRY_POINT_OFFSET_LOWER_BOUND,
    upper_bound=constants.ENTRY_POINT_OFFSET_UPPER_BOUND,
    name="Entry point offset",
    error_code=StarknetErrorCode.OUT_OF_RANGE_ENTRY_POINT_OFFSET,
    formatter=hex,
)
entry_point_offset_metadata = EntryPointOffsetField.metadata()


# Fee.

FeeField = RangeValidatedField(
    lower_bound=constants.FEE_LOWER_BOUND,
    upper_bound=constants.FEE_UPPER_BOUND,
    name="Fee",
    error_code=StarknetErrorCode.OUT_OF_RANGE_FEE,
    formatter=hex,
)
fee_metadata = FeeField.metadata(required=False, load_default=0)

OptionalFeeField = OptionalField(field=FeeField, none_probability=0)
optional_fee_metadata = OptionalFeeField.metadata()

# Gas price.

GasPriceField = RangeValidatedField(
    lower_bound=constants.GAS_PRICE_LOWER_BOUND,
    upper_bound=constants.GAS_PRICE_UPPER_BOUND,
    name="Gas price",
    error_code=StarknetErrorCode.OUT_OF_RANGE_GAS_PRICE,
    formatter=hex,
)
gas_price_metadata = GasPriceField.metadata(required=False, load_default=0)


# Transaction version.

TransactionVersionField = RangeValidatedField(
    lower_bound=constants.TRANSACTION_VERSION_LOWER_BOUND,
    upper_bound=constants.TRANSACTION_VERSION_UPPER_BOUND,
    name="Transaction version",
    error_code=StarknetErrorCode.OUT_OF_RANGE_TRANSACTION_VERSION,
    formatter=hex,
)
tx_version_metadata = TransactionVersionField.metadata(
    required=False, load_default=constants.TRANSACTION_VERSION
)


# State root.

state_root_metadata = dict(marshmallow_field=BytesAsHex(required=True))
optional_state_root_metadata = dict(marshmallow_field=BytesAsHex(required=False, allow_none=True))


# Transaction hash.

TransactionHashField = RangeValidatedField(
    lower_bound=constants.TRANSACTION_HASH_LOWER_BOUND,
    upper_bound=constants.TRANSACTION_HASH_UPPER_BOUND,
    name="Transaction hash",
    error_code=StarknetErrorCode.OUT_OF_RANGE_TRANSACTION_HASH,
    formatter=hex,
)
transaction_hash_metadata = TransactionHashField.metadata()

OptionalTransactionHashField = OptionalField(field=TransactionHashField, none_probability=0)
optional_transaction_hash_metadata = OptionalTransactionHashField.metadata()


# General config.

contract_storage_commitment_tree_height_metadata = dict(
    marshmallow_field=StrictRequiredInteger(
        validate=validate_positive("contract_storage_commitment_tree_height")
    )
)

global_state_commitment_tree_height_metadata = dict(
    marshmallow_field=StrictRequiredInteger(
        validate=validate_non_negative("global_state_commitment_tree_height"),
    )
)

invoke_tx_n_steps_metadata = dict(
    marshmallow_field=StrictRequiredInteger(validate=validate_non_negative("invoke_tx_n_steps"))
)

gas_price = dict(
    marshmallow_field=StrictRequiredInteger(validate=validate_non_negative("gas_price"))
)
