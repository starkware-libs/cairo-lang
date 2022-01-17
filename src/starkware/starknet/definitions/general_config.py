from dataclasses import field
from enum import Enum

import marshmallow_dataclass

from starkware.python.utils import from_bytes
from starkware.starknet.definitions import constants, fields
from starkware.starkware_utils.config_base import Config
from starkware.starkware_utils.field_validators import validate_non_negative
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
