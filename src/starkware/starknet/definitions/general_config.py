import copy
import os
from dataclasses import field
from enum import Enum
from typing import Any, Dict

import marshmallow.fields as mfields
import marshmallow_dataclass

from services.everest.definitions.general_config import EverestGeneralConfig
from starkware.cairo.lang.instances import all_instance
from starkware.python.utils import from_bytes
from starkware.starknet.definitions import constants, fields
from starkware.starkware_utils.config_base import Config, load_config
from starkware.starkware_utils.field_validators import validate_dict, validate_non_negative
from starkware.starkware_utils.marshmallow_dataclass_fields import (
    StrictRequiredInteger,
    load_int_value,
)

GENERAL_CONFIG_FILE_NAME = "general_config.yml"
DOCKER_GENERAL_CONFIG_PATH = os.path.join("/", GENERAL_CONFIG_FILE_NAME)
GENERAL_CONFIG_PATH = os.path.join(os.path.dirname(__file__), GENERAL_CONFIG_FILE_NAME)

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
DEFAULT_MAX_STEPS = 10 ** 6
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
DEFAULT_GAS_PRICE = 100 * 10 ** 9

class CairoResource(Enum):
    N_STEPS = "n_steps"
    PEDERSEN_BUILTIN = "pedersen_builtin"
    RANGE_CHECK_BUILTIN = "range_check_builtin"
    ECDSA_BUILTIN = "ecdsa_builtin"
    BITWISE_BUILTIN = "bitwise_builtin"
    OUTPUT_BUILTIN = "output_builtin"
    EC_OP_BUILTIN = "ec_op_builtin"


DEFAULT_CAIRO_RESOURCE_FEE_WEIGHTS = {
    CairoResource.N_STEPS.value: 1.0,
    CairoResource.PEDERSEN_BUILTIN.value: 0.0,
    CairoResource.RANGE_CHECK_BUILTIN.value: 0.0,
    CairoResource.ECDSA_BUILTIN.value: 0.0,
    CairoResource.BITWISE_BUILTIN.value: 0.0,
    CairoResource.OUTPUT_BUILTIN.value: 0.0,
    CairoResource.EC_OP_BUILTIN.value: 0.0,
}


# Configuration schema definition.


@marshmallow_dataclass.dataclass(frozen=True)
class StarknetOsConfig(Config):
    chain_id: StarknetChainId = field(default=DEFAULT_CHAIN_ID)

    fee_token_address: int = field(
        metadata=dict(
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

    min_gas_price: int = field(metadata=fields.gas_price, default=DEFAULT_GAS_PRICE)

    sequencer_address: int = field(
        metadata=dict(
            **fields.sequencer_address_metadata, description="StarkNet sequencer address."
        ),
        default=DEFAULT_SEQUENCER_ADDRESS,
    )

    tx_commitment_tree_height: int = field(
        metadata=dict(
            marshmallow_field=StrictRequiredInteger(
                validate=validate_non_negative("Transaction commitment tree height"),
            ),
            description="Height of Patricia tree of the transaction commitment in a block.",
        ),
        default=constants.TRANSACTION_COMMITMENT_TREE_HEIGHT,
    )

    tx_version: int = field(
        metadata=dict(
            marshmallow_field=StrictRequiredInteger(
                validate=validate_non_negative("Trasaction version."),
            ),
            description=(
                "Current transaction version - "
                "in order to identify transactions from unsupported versions."
            ),
        ),
        default=constants.TRANSACTION_VERSION,
    )

    event_commitment_tree_height: int = field(
        metadata=dict(
            marshmallow_field=StrictRequiredInteger(
                validate=validate_non_negative("Event commitment tree height"),
            ),
            description="Height of Patricia tree of the event commitment in a block.",
        ),
        default=constants.EVENT_COMMITMENT_TREE_HEIGHT,
    )

    cairo_resource_fee_weights: Dict[str, float] = field(
        metadata=dict(
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
    n_steps_key = CairoResource.N_STEPS.value
    assert cairo_resource_fee_weights.keys() == {
        n_steps_key
    }, f"Only {n_steps_key} weight should be given."

    n_steps_weight = cairo_resource_fee_weights[n_steps_key]

    # Zero all entries.
    cairo_resource_fee_weights.update({resource.value: 0.0 for resource in CairoResource})
    # Update relevant entries.
    cairo_resource_fee_weights.update(
        {
            n_steps_key: n_steps_weight,
            # All other weights are deduced from n_steps.
            CairoResource.PEDERSEN_BUILTIN.value: n_steps_weight
            * all_instance.builtins["pedersen"].ratio,
            CairoResource.RANGE_CHECK_BUILTIN.value: n_steps_weight
            * all_instance.builtins["range_check"].ratio,
            CairoResource.ECDSA_BUILTIN.value: n_steps_weight
            * all_instance.builtins["ecdsa"].ratio,
            CairoResource.BITWISE_BUILTIN.value: n_steps_weight
            * all_instance.builtins["bitwise"].ratio,
        }
    )

    return StarknetGeneralConfig.load(data=raw_general_config)
