from dataclasses import field
from enum import Enum

import marshmallow_dataclass

from starkware.python.utils import from_bytes
from starkware.starknet.definitions import constants, fields
from starkware.starkware_utils.config_base import Config

DOCKER_GENERAL_CONFIG_PATH = "/general_config.yml"


class StarknetChainId(Enum):
    MAINNET = from_bytes(b"MAINNET")
    TESTNET = from_bytes(b"TESTNET")


# Default configuration values.

# In order to be able to use Keccak builtin, which uses bitwise, which is sparse.
DEFAULT_MAX_STEPS = 10 ** 6
DEFAULT_CHAIN_ID = StarknetChainId.TESTNET


# Configuration schema definition.


@marshmallow_dataclass.dataclass(frozen=True)
class StarknetGeneralConfig(Config):
    contract_storage_commitment_tree_height: int = field(
        metadata=fields.contract_storage_commitment_tree_height_metadata,
        default=constants.CONTRACT_STATES_MERKLE_TREE_HEIGHT,
    )

    global_state_commitment_tree_height: int = field(
        metadata=fields.global_state_commitment_tree_height_metadata,
        default=constants.CONTRACT_ADDRESS_BITS,
    )

    invoke_tx_max_n_steps: int = field(
        metadata=fields.invoke_tx_n_steps_metadata, default=DEFAULT_MAX_STEPS
    )

    chain_id: StarknetChainId = field(default=DEFAULT_CHAIN_ID)
