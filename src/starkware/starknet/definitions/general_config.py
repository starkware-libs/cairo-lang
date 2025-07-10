import os
from dataclasses import field
from typing import Any, Dict, Optional

import marshmallow_dataclass
from marshmallow import pre_load

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
SIERRA_GAS_NAME = "sierra_gas"
N_TXS_NAME = "n_txs"
PROVING_GAS_NAME = "proving_gas"

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
    value=default_general_config["deprecated_fee_token_address"],
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

# Given in units of wei.
DEFAULT_DEPRECATED_L1_GAS_PRICE = 10**9
DEFAULT_DEPRECATED_L2_GAS_PRICE = 1
DEFAULT_DEPRECATED_L1_DATA_GAS_PRICE = 1

# Given in units of wei.
DEFAULT_L2_GAS_PRICE = int(((10**9) * 15) * 0.000025)

DEFAULT_MIN_FRI_L1_GAS_PRICE = 10**6
DEFAULT_MAX_FRI_L1_GAS_PRICE = 10**21
DEFAULT_MIN_FRI_L2_GAS_PRICE = 10**4
DEFAULT_MAX_FRI_L2_GAS_PRICE = 10**17
DEFAULT_MIN_FRI_L1_DATA_GAS_PRICE = 1
DEFAULT_MAX_FRI_L1_DATA_GAS_PRICE = 10**21


# Configuration schema definition.


@marshmallow_dataclass.dataclass
class StarknetOsConfig(Config):
    chain_id: int = field(default=DEFAULT_CHAIN_ID)

    fee_token_address: int = field(
        metadata=additional_metadata(
            **fields.fee_token_address_metadata, description="Starknet fee token L2 address."
        ),
        default=DEFAULT_FEE_TOKEN_ADDRESS,
    )

    def starknet_chain_id(self) -> StarknetChainId:
        """
        Returns the starknet chain ID.
        """
        return StarknetChainId(self.chain_id)


@marshmallow_dataclass.dataclass
class StarknetGeneralConfig(EverestGeneralConfig):
    starknet_os_config: StarknetOsConfig = field(default_factory=StarknetOsConfig)

    # This field used to be part of the OS config, but now the OS does not support deprecated
    # transactions. Keep it here since the Blockifier infra still needs it (e.g., for reexecution).
    deprecated_fee_token_address: int = field(
        metadata=additional_metadata(
            **fields.fee_token_address_metadata, description="Starknet old fee token L2 address."
        ),
        default=DEFAULT_DEPRECATED_FEE_TOKEN_ADDRESS,
    )

    # IMPORTANT: when editing this in production, make sure to only decrease the value.
    # Increasing it in production may cause issue to nodes during execution, so only increase it
    # during a new release.
    # This value should not be used directly, Use `get_validate_max_n_steps`.
    validate_max_n_steps_override: Optional[int] = field(
        metadata=fields.validate_max_n_steps_override_metadata, default=None
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

    @pre_load
    def load_0_13_5_config(self, data: Dict[str, Any], many: bool, **kwargs) -> Dict[str, Any]:
        deprecated_token_field = "deprecated_fee_token_address"
        os_config_field = "starknet_os_config"
        if deprecated_token_field not in data:
            assert deprecated_token_field in data[os_config_field]
            data[deprecated_token_field] = data[os_config_field].pop(deprecated_token_field)
        return data

    @property
    def chain_id(self) -> StarknetChainId:
        return StarknetChainId(self.starknet_os_config.chain_id)

    @property
    def fee_token_address(self) -> int:
        return self.starknet_os_config.fee_token_address

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

    def get_max_n_events(self) -> int:
        private_versioned_constants = self.get_private_versioned_constants()
        if private_versioned_constants is not None:
            if private_versioned_constants.max_n_events is not None:
                return private_versioned_constants.max_n_events

        return VERSIONED_CONSTANTS.max_n_events
