import copy
import os
from dataclasses import field
from typing import Any, Dict

import marshmallow.fields as mfields
import marshmallow_dataclass

from services.everest.definitions.general_config import EverestGeneralConfig
from starkware.cairo.lang.builtins.all_builtins import (
    ALL_BUILTINS,
    BITWISE_BUILTIN,
    EC_OP_BUILTIN,
    ECDSA_BUILTIN,
    KECCAK_BUILTIN,
    OUTPUT_BUILTIN,
    PEDERSEN_BUILTIN,
    POSEIDON_BUILTIN,
    RANGE_CHECK_BUILTIN,
    with_suffix,
)
from starkware.cairo.lang.instances import starknet_instance, starknet_with_keccak_instance
from starkware.python.utils import from_bytes
from starkware.starknet.definitions import constants, fields
from starkware.starknet.definitions.chain_ids import StarknetChainId
from starkware.starkware_utils.config_base import Config, load_config
from starkware.starkware_utils.field_validators import validate_dict, validate_non_negative
from starkware.starkware_utils.marshmallow_dataclass_fields import (
    RequiredBoolean,
    StrictRequiredInteger,
    additional_metadata,
    load_int_value,
)

GENERAL_CONFIG_FILE_NAME = "general_config.yml"
DOCKER_GENERAL_CONFIG_PATH = os.path.join("/", GENERAL_CONFIG_FILE_NAME)
GENERAL_CONFIG_PATH = os.path.join(os.path.dirname(__file__), GENERAL_CONFIG_FILE_NAME)
N_STEPS_RESOURCE = "n_steps"
STARKNET_LAYOUT_INSTANCE_WITHOUT_KECCAK = starknet_instance
STARKNET_LAYOUT_INSTANCE = starknet_with_keccak_instance

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

DEFAULT_VALIDATE_MAX_STEPS = 10**6
DEFAULT_TX_MAX_STEPS = 3 * 10**6
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

# Given in units of wei.
DEFAULT_DEPRECATED_L1_GAS_PRICE = 10**11
DEFAULT_CAIRO_RESOURCE_FEE_WEIGHTS = {
    N_STEPS_RESOURCE: 0.005,
    **{builtin: 0.0 for builtin in ALL_BUILTINS.with_suffix()},
    with_suffix(PEDERSEN_BUILTIN): 0.16,
    with_suffix(RANGE_CHECK_BUILTIN): 0.08,
    with_suffix(ECDSA_BUILTIN): 10.24,
    with_suffix(KECCAK_BUILTIN): 10.24,
    with_suffix(BITWISE_BUILTIN): 0.32,
    with_suffix(EC_OP_BUILTIN): 5.12,
    with_suffix(POSEIDON_BUILTIN): 0.16,
}

DEFAULT_ETH_IN_STRK_WEI = 10**21
DEFAULT_MIN_STRK_L1_GAS_PRICE = 10**6
DEFAULT_MAX_STRK_L1_GAS_PRICE = 10**18


# Configuration schema definition.


@marshmallow_dataclass.dataclass(frozen=True)
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


@marshmallow_dataclass.dataclass(frozen=True)
class StarknetGeneralConfig(EverestGeneralConfig):
    starknet_os_config: StarknetOsConfig = field(default_factory=StarknetOsConfig)

    contract_storage_commitment_tree_height: int = field(
        metadata=fields.contract_storage_commitment_tree_height_metadata,
        default=constants.CONTRACT_STATES_COMMITMENT_TREE_HEIGHT,
    )

    compiled_class_hash_commitment_tree_height: int = field(
        metadata=fields.compiled_class_hash_commitment_tree_height_metadata,
        default=constants.COMPILED_CLASS_HASH_COMMITMENT_TREE_HEIGHT,
    )

    global_state_commitment_tree_height: int = field(
        metadata=fields.global_state_commitment_tree_height_metadata,
        default=constants.CONTRACT_ADDRESS_BITS,
    )

    invoke_tx_max_n_steps: int = field(
        metadata=fields.invoke_tx_n_steps_metadata, default=DEFAULT_TX_MAX_STEPS
    )

    validate_max_n_steps: int = field(
        metadata=fields.validate_n_steps_metadata, default=DEFAULT_VALIDATE_MAX_STEPS
    )

    min_eth_l1_gas_price: int = field(
        metadata=fields.gas_price, default=DEFAULT_DEPRECATED_L1_GAS_PRICE
    )

    min_strk_l1_gas_price: int = field(
        metadata=fields.gas_price, default=DEFAULT_MIN_STRK_L1_GAS_PRICE
    )

    max_strk_l1_gas_price: int = field(
        metadata=fields.gas_price, default=DEFAULT_MAX_STRK_L1_GAS_PRICE
    )

    # The default price of one ETH (10**18 Wei) in STRK units. Used in case of oracle failure.
    default_eth_price_in_strk_wei: int = field(
        metadata=fields.eth_price_in_strk_wei, default=DEFAULT_ETH_IN_STRK_WEI
    )

    constant_gas_price: bool = field(
        metadata=additional_metadata(
            marshmallow_field=RequiredBoolean(),
            description=(
                "If true, sets ETH gas price and STRK gas price to their minimum price "
                "configurations, regardless of the sampled gas prices."
            ),
        ),
        default=False,
    )

    sequencer_address: int = field(
        metadata=additional_metadata(
            **fields.sequencer_address_metadata, description="Starknet sequencer address."
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
        {resource: 0.0 for resource in [N_STEPS_RESOURCE] + ALL_BUILTINS.with_suffix()}
    )

    # Update relevant entries.
    cairo_resource_fee_weights.update(
        {
            N_STEPS_RESOURCE: n_steps_weight,
            # All other weights are deduced from n_steps.
            **{
                with_suffix(name): n_steps_weight * instance_def.ratio
                for name, instance_def in STARKNET_LAYOUT_INSTANCE.builtins.items()
                if name != OUTPUT_BUILTIN
            },
        }
    )

    return StarknetGeneralConfig.load(data=raw_general_config)
