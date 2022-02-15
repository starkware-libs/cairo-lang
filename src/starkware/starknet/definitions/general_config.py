from dataclasses import field
from enum import Enum
from typing import Dict

import marshmallow.fields as mfields
import marshmallow_dataclass

from starkware.python.utils import from_bytes
from starkware.starknet.definitions import constants, fields
from starkware.starkware_utils.config_base import Config
from starkware.starkware_utils.field_validators import validate_dict, validate_non_negative
from starkware.starkware_utils.marshmallow_dataclass_fields import StrictRequiredInteger

DOCKER_GENERAL_CONFIG_PATH = "/general_config.yml"


class StarknetChainId(Enum):
    MAINNET = from_bytes(b"SN_MAIN")
    TESTNET = from_bytes(b"SN_GOERLI")


# Default configuration values.

# Note: tokens sent to this default address will be burned.
DEFAULT_SEQUENCER_ADDRESS = 0

# In order to be able to use Keccak builtin, which uses bitwise, which is sparse.
DEFAULT_MAX_STEPS = 10 ** 6
DEFAULT_CHAIN_ID = StarknetChainId.TESTNET

class CairoResource(Enum):
    N_STEPS = "n_steps"
    GAS_WEIGHT = "gas_weight"
    PEDERSEN_BUILTIN = "pedersen_builtin"
    RANGE_CHECK_BUILTIN = "range_check_builtin"
    ECDSA_BUILTIN = "ecdsa_builtin"
    BITWISE_BUILTIN = "bitwise_builtin"
    OUTPUT_BUILTIN = "output_builtin"
    EC_OP_BUILTIN = "ec_op_builtin"


DEFAULT_CAIRO_USAGE_RESOURCE_FEE_WEIGHTS = {
    CairoResource.N_STEPS.value: 0.0,
    CairoResource.GAS_WEIGHT.value: 0.0,
    CairoResource.PEDERSEN_BUILTIN.value: 0.0,
    CairoResource.RANGE_CHECK_BUILTIN.value: 0.0,
    CairoResource.ECDSA_BUILTIN.value: 0.0,
    CairoResource.BITWISE_BUILTIN.value: 0.0,
}


# Configuration schema definition.


@marshmallow_dataclass.dataclass(frozen=True)
class StarknetGeneralConfig(Config):
    chain_id: StarknetChainId = field(default=DEFAULT_CHAIN_ID)

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

    event_commitment_tree_height: int = field(
        metadata=dict(
            marshmallow_field=StrictRequiredInteger(
                validate=validate_non_negative("Event commitment tree height"),
            ),
            description="Height of Patricia tree of the event commitment in a block.",
        ),
        default=constants.EVENT_COMMITMENT_TREE_HEIGHT,
    )

    cairo_usage_resource_fee_weights: Dict[str, float] = field(
        metadata=dict(
            marshmallow_field=mfields.Dict(
                keys=mfields.String,
                values=mfields.Float,
                validate=validate_dict(
                    "Cairo usage resource fee weights", value_validator=validate_non_negative
                ),
            ),
            description=(
                "A mapping from a Cairo usage resource to its coefficient in this transaction "
                "fee calculation."
            ),
        ),
        default_factory=lambda: DEFAULT_CAIRO_USAGE_RESOURCE_FEE_WEIGHTS.copy(),
    )
