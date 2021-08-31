from dataclasses import field

import marshmallow_dataclass

from starkware.starknet.definitions import constants, fields
from starkware.starkware_utils.config_base import Config

DOCKER_GENERAL_CONFIG_PATH = "/general_config.yml"

# In order to be able to use Keccak builtin, which uses bitwise, which is sparse.
DEFAULT_MAX_STEPS = 10 ** 6


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
