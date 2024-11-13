import os
from dataclasses import field
from typing import Optional

import marshmallow_dataclass

from services.everest.definitions.general_config import EverestGeneralConfig
from starkware.cairo.lang.instances import dynamic_instance
from starkware.python.utils import from_bytes
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.chain_ids import (
    CHAIN_ID_TO_PRIVATE_VERSIONED_CONSTANTS,
    StarknetChainId,
)
from starkware.starknet.definitions.constants import VERSIONED_CONSTANTS
from starkware.starknet.definitions.overridable_versioned_constants import (
    OverridableVersionedConstants,
)
from starkware.starkware_utils.config_base import Config, load_config
from starkware.starkware_utils.marshmallow_dataclass_fields import (
    RequiredBoolean,
    additional_metadata,
    load_int_value,
)

GENERAL_CONFIG_FILE_NAME = "general_config.yml"
DOCKER_GENERAL_CONFIG_PATH = os.path.join("/", GENERAL_CONFIG_FILE_NAME)
GENERAL_CONFIG_PATH = os.path.join(os.path.dirname(__file__), GENERAL_CONFIG_FILE_NAME)
N_STEPS_RESOURCE = "n_steps"
STATE_DIFF_SIZE_WEIGHT_NAME = "state_diff_size"
STATE_DIFF_SIZE_WITH_KZG_WEIGHT_NAME = "state_diff_size_with_kzg"
N_EVENTS_NAME = "n_events"
MESSAGE_SEGMENT_LENGTH_NAME = "message_segment_length"
GAS_WEIGHT_NAME = "gas_weight"

STARKNET_LAYOUT_INSTANCE = dynamic_instance

# Reference to the default general config.
default_general_config = load_config(
    config_file_path=GENERAL_CONFIG_PATH, load_logging_config=False
)


# Fee token account constants.
TOKEN_NAME = from_bytes(b"Wrapped Ether")
TOKEN_SYMBOL = from_bytes(b"WETH")
TOKEN_DECIMALS = 18
ETH_TOKEN_SALT = 0
STRK_TOKEN_SALT = 1


# Default configuration values.

DEFAULT_CHAIN_ID = StarknetChainId.TESTNET.value
DEFAULT_DEPRECATED_FEE_TOKEN_ADDRESS = load_int_value(
    field_metadata=fields.fee_token_address_metadata,
    value=default_general_config["starknet_os_config"]["deprecated_fee_token_address"],
)
DEFAULT_FEE_TOKEN_ADDRESS = load_int_value(
    field_metadata=fields.fee_token_address_metadata,
    value=default_general_config["starknet_os_config"]["fee_token_address"],
)
DEFAULT_SEQUENCER_ADDRESS = load_int_value(
    field_metadata=fields.fee_token_address_metadata,
    value=default_general_config["sequencer_address"],
)
DEFAULT_ENFORCE_L1_FEE = True
DEFAULT_USE_KZG_DA = True

# Given in units of wei.
DEFAULT_DEPRECATED_L1_GAS_PRICE = 10**9
DEFAULT_DEPRECATED_L1_DATA_GAS_PRICE = 1

DEFAULT_ETH_IN_FRI = 10**21
DEFAULT_MIN_FRI_L1_GAS_PRICE = 10**6
DEFAULT_MAX_FRI_L1_GAS_PRICE = 10**21
DEFAULT_MIN_FRI_L1_DATA_GAS_PRICE = 1
DEFAULT_MAX_FRI_L1_DATA_GAS_PRICE = 10**21


# Configuration schema definition.


@marshmallow_dataclass.dataclass
class StarknetOsConfig(Config):
    chain_id: int = field(default=DEFAULT_CHAIN_ID)

    deprecated_fee_token_address: int = field(
        metadata=additional_metadata(
            **fields.fee_token_address_metadata, description="Starknet old fee token L2 address."
        ),
        default=DEFAULT_DEPRECATED_FEE_TOKEN_ADDRESS,
    )

    fee_token_address: int = field(
        metadata=additional_metadata(
            **fields.fee_token_address_metadata, description="Starknet fee token L2 address."
        ),
        default=DEFAULT_FEE_TOKEN_ADDRESS,
    )


@marshmallow_dataclass.dataclass
class GasPriceBounds:
    min_wei_l1_gas_price: int = field(
        metadata=fields.gas_price, default=DEFAULT_DEPRECATED_L1_GAS_PRICE
    )

    min_fri_l1_gas_price: int = field(
        metadata=fields.gas_price, default=DEFAULT_MIN_FRI_L1_GAS_PRICE
    )

    max_fri_l1_gas_price: int = field(
        metadata=fields.gas_price, default=DEFAULT_MAX_FRI_L1_GAS_PRICE
    )

    min_wei_l1_data_gas_price: int = field(
        metadata=fields.gas_price, default=DEFAULT_DEPRECATED_L1_DATA_GAS_PRICE
    )

    min_fri_l1_data_gas_price: int = field(
        metadata=fields.gas_price, default=DEFAULT_MIN_FRI_L1_DATA_GAS_PRICE
    )

    max_fri_l1_data_gas_price: int = field(
        metadata=fields.gas_price, default=DEFAULT_MAX_FRI_L1_DATA_GAS_PRICE
    )


@marshmallow_dataclass.dataclass
class StarknetGeneralConfig(EverestGeneralConfig):
    starknet_os_config: StarknetOsConfig = field(default_factory=StarknetOsConfig)

    gas_price_bounds: GasPriceBounds = field(default_factory=GasPriceBounds)

    # IMPORTANT: when editing this in production, make sure to only decrease the value.
    # Increasing it in production may cause issue to nodes during execution, so only increase it
    # during a new release.
    # This value should not be used directly, Use `get_validate_max_n_steps`.
    validate_max_n_steps_override: Optional[int] = field(
        metadata=fields.validate_max_n_steps_override_metadata, default=None
    )

    # The default price of one ETH (10**18 Wei) in STRK units. Used in case of oracle failure.
    default_eth_price_in_fri: int = field(
        metadata=fields.eth_price_in_fri, default=DEFAULT_ETH_IN_FRI
    )

    sequencer_address: int = field(
        metadata=additional_metadata(
            **fields.sequencer_address_metadata, description="Starknet sequencer address."
        ),
        default=DEFAULT_SEQUENCER_ADDRESS,
    )

    enforce_l1_handler_fee: bool = field(
        metadata=additional_metadata(
            marshmallow_field=RequiredBoolean(), description="Enabler for L1 fee enforcement."
        ),
        default=DEFAULT_ENFORCE_L1_FEE,
    )

    @property
    def chain_id(self) -> StarknetChainId:
        return StarknetChainId(self.starknet_os_config.chain_id)

    @property
    def deprecated_fee_token_address(self) -> int:
        return self.starknet_os_config.deprecated_fee_token_address

    @property
    def fee_token_address(self) -> int:
        return self.starknet_os_config.fee_token_address

    @property
    def min_wei_l1_gas_price(self) -> int:
        return self.gas_price_bounds.min_wei_l1_gas_price

    @property
    def min_fri_l1_gas_price(self) -> int:
        return self.gas_price_bounds.min_fri_l1_gas_price

    @property
    def max_fri_l1_gas_price(self) -> int:
        return self.gas_price_bounds.max_fri_l1_gas_price

    @property
    def min_wei_l1_data_gas_price(self) -> int:
        return self.gas_price_bounds.min_wei_l1_data_gas_price

    @property
    def min_fri_l1_data_gas_price(self) -> int:
        return self.gas_price_bounds.min_fri_l1_data_gas_price

    @property
    def max_fri_l1_data_gas_price(self) -> int:
        return self.gas_price_bounds.max_fri_l1_data_gas_price

    def get_private_versioned_constants(self) -> Optional[OverridableVersionedConstants]:
        return CHAIN_ID_TO_PRIVATE_VERSIONED_CONSTANTS.get(self.chain_id)

    def get_validate_max_n_steps(self) -> int:
        if self.validate_max_n_steps_override is not None:
            return self.validate_max_n_steps_override

        private_versioned_constants = self.get_private_versioned_constants()
        if private_versioned_constants is not None:
            if private_versioned_constants.validate_max_n_steps is not None:
                return private_versioned_constants.validate_max_n_steps

        return VERSIONED_CONSTANTS.validate_max_n_steps

    def get_invoke_tx_max_n_steps(self) -> int:
        private_versioned_constants = self.get_private_versioned_constants()
        if private_versioned_constants is not None:
            if private_versioned_constants.invoke_tx_max_n_steps is not None:
                return private_versioned_constants.invoke_tx_max_n_steps

        return VERSIONED_CONSTANTS.invoke_tx_max_n_steps
