import copy
import os
from dataclasses import field
from enum import Enum
from typing import Any, Dict

import marshmallow.fields as mfields
import marshmallow_dataclass

from services.everest.definitions.general_config import EverestGeneralConfig
from starkware.cairo.lang.builtins.all_builtins import (
    ALL_BUILTINS,
    KECCAK_BUILTIN,
    OUTPUT_BUILTIN,
    with_suffix,
)
from starkware.cairo.lang.instances import all_instance
from starkware.python.utils import from_bytes
from starkware.starknet.definitions import constants, fields
from starkware.starkware_utils.config_base import Config, load_config
from starkware.starkware_utils.field_validators import validate_dict, validate_non_negative
from starkware.starkware_utils.marshmallow_dataclass_fields import (
    StrictRequiredInteger,
    additional_metadata,
    load_int_value,
)

GENERAL_CONFIG_FILE_NAME = "general_config.yml"
DOCKER_GENERAL_CONFIG_PATH = os.path.join("/", GENERAL_CONFIG_FILE_NAME)
GENERAL_CONFIG_PATH = os.path.join(os.path.dirname(__file__), GENERAL_CONFIG_FILE_NAME)
N_STEPS_RESOURCE = "n_steps"

# Reference to the default general config.
default_general_config = load_config(
    config_file_path=GENERAL_CONFIG_PATH, load_logging_config=False
)


class StarknetChainId(Enum):
    MAINNET = from_bytes(b"SN_MAIN")
    TESTNET = from_bytes(b"SN_GOERLI")


# Fee token account constants.
TOKEN_NAME = from_bytes(b"Wrapped Ether")
TOKEN_SYMBOL = from_bytes(b"WETH")
TOKEN_DECIMALS = 18


# Default configuration values.

# In order to be able to use Keccak builtin, which uses bitwise, which is sparse.
DEFAULT_MAX_STEPS = 10**6
DEFAULT_VALIDATE_MAX_STEPS = DEFAULT_MAX_STEPS
DEFAULT_CHAIN_ID = StarknetChainId.TESTNET
DEFAULT_FEE_TOKEN_ADDRESS = load_int_value(
    field_metadata=fields.fee_token_address_metadata,
    value=default_general_config["starknet_os_config"]["fee_token_address"],
)
DEFAULT_SEQUENCER_ADDRESS = load_int_value(
    field_metadata=fields.fee_token_address_metadata,
    value=default_general_config["sequencer_address"],
)

# Given in units of wei.
DEFAULT_GAS_PRICE = 100 * 10**9
DEFAULT_CAIRO_RESOURCE_FEE_WEIGHTS = {
    N_STEPS_RESOURCE: 1.0,
    **{builtin: 0.0 for builtin in ALL_BUILTINS.except_for(KECCAK_BUILTIN).with_suffix()},
}


# Configuration schema definition.


@marshmallow_dataclass.dataclass(frozen=True)
class StarknetOsConfig(Config):
    chain_id: StarknetChainId = field(default=DEFAULT_CHAIN_ID)

    fee_token_address: int = field(
        metadata=additional_metadata(
            **fields.fee_token_address_metadata, description="StarkNet fee token L2 address."
        ),
        default=DEFAULT_FEE_TOKEN_ADDRESS,
    )


@marshmallow_dataclass.dataclass(frozen=True)
class StarknetGeneralConfig(EverestGeneralConfig):
    starknet_os_config: StarknetOsConfig = field(default_factory=StarknetOsConfig)

    contract_storage_commitment_tree_height: int = field(
        metadata=fields.contract_storage_commitment_tree_height_metadata,
        default=constants.CONTRACT_STATES_COMMITMENT_TREE_HEIGHT,
    )

    global_state_commitment_tree_height: int = field(
        metadata=fields.global_state_commitment_tree_height_metadata,
        default=constants.CONTRACT_ADDRESS_BITS,
    )

    invoke_tx_max_n_steps: int = field(
        metadata=fields.invoke_tx_n_steps_metadata, default=DEFAULT_MAX_STEPS
    )

    validate_max_n_steps: int = field(
        metadata=fields.validate_n_steps_metadata, default=DEFAULT_VALIDATE_MAX_STEPS
    )

    min_gas_price: int = field(metadata=fields.gas_price, default=DEFAULT_GAS_PRICE)

    sequencer_address: int = field(
        metadata=additional_metadata(
            **fields.sequencer_address_metadata, description="StarkNet sequencer address."
        ),
        default=DEFAULT_SEQUENCER_ADDRESS,
    )

    tx_commitment_tree_height: int = field(
        metadata=additional_metadata(
            marshmallow_field=StrictRequiredInteger(
                validate=validate_non_negative("Transaction commitment tree height"),
            ),
            description="Height of Patricia tree of the transaction commitment in a block.",
        ),
        default=constants.TRANSACTION_COMMITMENT_TREE_HEIGHT,
    )

    tx_version: int = field(
        metadata=additional_metadata(
            marshmallow_field=StrictRequiredInteger(
                validate=validate_non_negative("Transaction version."),
            ),
            description=(
                "Current transaction version - "
                "in order to identify transactions from unsupported versions."
            ),
        ),
        default=constants.TRANSACTION_VERSION,
    )

    event_commitment_tree_height: int = field(
        metadata=additional_metadata(
            marshmallow_field=StrictRequiredInteger(
                validate=validate_non_negative("Event commitment tree height"),
            ),
            description="Height of Patricia tree of the event commitment in a block.",
        ),
        default=constants.EVENT_COMMITMENT_TREE_HEIGHT,
    )

    cairo_resource_fee_weights: Dict[str, float] = field(
        metadata=additional_metadata(
            marshmallow_field=mfields.Dict(
                keys=mfields.String,
                values=mfields.Float,
                validate=validate_dict(
                    "Cairo resource fee weights", value_validator=validate_non_negative
                ),
            ),
            description=(
                "A mapping from a Cairo resource to its coefficient in this transaction "
                "fee calculation."
            ),
        ),
        default_factory=lambda: DEFAULT_CAIRO_RESOURCE_FEE_WEIGHTS.copy(),
    )

    @property
    def chain_id(self) -> StarknetChainId:
        return self.starknet_os_config.chain_id

    @property
    def fee_token_address(self) -> int:
        return self.starknet_os_config.fee_token_address


def build_general_config(raw_general_config: Dict[str, Any]) -> StarknetGeneralConfig:
    """
    Updates the fee weights and builds the general config.
    """
    raw_general_config = copy.deepcopy(raw_general_config)
    cairo_resource_fee_weights: Dict[str, float] = raw_general_config["cairo_resource_fee_weights"]
    assert cairo_resource_fee_weights.keys() == {
        N_STEPS_RESOURCE
    }, f"Only {N_STEPS_RESOURCE} weight should be given."

    n_steps_weight = cairo_resource_fee_weights[N_STEPS_RESOURCE]

    # Zero all entries.
    cairo_resource_fee_weights.update(
        {
            resource: 0.0
            for resource in [N_STEPS_RESOURCE]
            + ALL_BUILTINS.except_for(KECCAK_BUILTIN).with_suffix()
        }
    )
    # Update relevant entries.
    cairo_resource_fee_weights.update(
        {
            N_STEPS_RESOURCE: n_steps_weight,
            # All other weights are deduced from n_steps.
            **{
                with_suffix(builtin): n_steps_weight * all_instance.builtins[builtin].ratio
                for builtin in ALL_BUILTINS.except_for(OUTPUT_BUILTIN, KECCAK_BUILTIN)
            },
        }
    )

    return StarknetGeneralConfig.load(data=raw_general_config)
