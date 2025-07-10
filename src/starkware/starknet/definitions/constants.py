import dataclasses
import json
from enum import Enum
from pathlib import Path
from typing import Dict, Union

from starkware.crypto.signature.signature import FIELD_PRIME
from starkware.python.utils import from_bytes
from starkware.storage.storage import HASH_BYTES

VERSIONED_CONSTANTS_FILE_NAME = "versioned_constants.json"
VERSIONED_CONSTANTS_PATH = Path(__file__).parent / VERSIONED_CONSTANTS_FILE_NAME

STARKNET_LANG_DIRECTIVE = "starknet"

FIELD_SIZE = FIELD_PRIME
FIELD_SIZE_BITS = 251
ADDRESS_BITS = FIELD_SIZE_BITS
CONTRACT_ADDRESS_BITS = ADDRESS_BITS
NONCE_BITS = FIELD_SIZE_BITS

FELT_LOWER_BOUND = 0
FELT_UPPER_BOUND = FIELD_SIZE
BLOCK_HASH_LOWER_BOUND = 0
BLOCK_HASH_UPPER_BOUND = FIELD_SIZE
COMMITMENT_LOWER_BOUND = 0
COMMITMENT_UPPER_BOUND = FIELD_SIZE
# Address 0 is reserved to distinguish an external transaction from an inner (L2<>L2) one.
L2_ADDRESS_LOWER_BOUND = 1
# The address upper bound is defined to be congruent with the storage var address upper bound (see
# storage.cairo).
L2_ADDRESS_UPPER_BOUND = 2**CONTRACT_ADDRESS_BITS - 256
CLASS_HASH_BYTES = HASH_BYTES
CLASS_HASH_UPPER_BOUND = FIELD_SIZE
CONTRACT_STATES_COMMITMENT_TREE_HEIGHT = FIELD_SIZE_BITS
COMPILED_CLASS_HASH_UPPER_BOUND = FIELD_SIZE
COMPILED_CLASS_HASH_COMMITMENT_TREE_HEIGHT = FIELD_SIZE_BITS
DATA_AVAILABILITY_MODE_BITS = 32
ENTRY_POINT_FUNCTION_IDX_LOWER_BOUND = 0
ENTRY_POINT_FUNCTION_IDX_UPPER_BOUND = FIELD_SIZE
ENTRY_POINT_OFFSET_LOWER_BOUND = 0
ENTRY_POINT_OFFSET_UPPER_BOUND = FIELD_SIZE
ENTRY_POINT_SELECTOR_LOWER_BOUND = 0
ENTRY_POINT_SELECTOR_UPPER_BOUND = FIELD_SIZE
EVENT_COMMITMENT_TREE_HEIGHT = 64
FEE_LOWER_BOUND = 0
FEE_UPPER_BOUND = 2**128
# Default hash to fill the parent_hash field of the first block in the sequence.
GENESIS_PARENT_BLOCK_HASH = 0
GAS_PRICE_LOWER_BOUND = 0
GAS_PRICE_UPPER_BOUND = 2**128
MAX_AMOUNT_BITS = 64
MAX_AMOUNT_LOWER_BOUND = 0
MAX_AMOUNT_UPPER_BOUND = 2**MAX_AMOUNT_BITS
MAX_MESSAGE_TO_L1_LENGTH = 100
MAX_PRICE_PER_UNIT_BITS = 128
MAX_PRICE_PER_UNIT_LOWER_BOUND = 0
MAX_PRICE_PER_UNIT_UPPER_BOUND = 2**MAX_PRICE_PER_UNIT_BITS
MAX_RESOURCE_NAME_BITS = FIELD_SIZE_BITS - MAX_PRICE_PER_UNIT_BITS - MAX_AMOUNT_BITS
MAX_STATE_DIFF_LENGTH = 2**64
NONCE_LOWER_BOUND = 0
NONCE_UPPER_BOUND = 2**NONCE_BITS
SIERRA_ARRAY_LEN_BOUND = 2**32
SYSCALL_SELECTOR_UPPER_BOUND = FIELD_SIZE
TIP_LOWER_BOUND = 0
TIP_UPPER_BOUND = 2**64
TRANSACTION_COMMITMENT_TREE_HEIGHT = 64
TRANSACTION_HASH_LOWER_BOUND = 0
TRANSACTION_HASH_UPPER_BOUND = FIELD_SIZE
TRANSACTION_VERSION_LOWER_BOUND = 0
TRANSACTION_VERSION_UPPER_BOUND = FIELD_SIZE
ADDRESS_LOWER_BOUND = 0
ADDRESS_UPPER_BOUND = 2**ADDRESS_BITS
UNINITIALIZED_CLASS_HASH = bytes(HASH_BYTES)

# In order to identify transactions from unsupported versions.
DEPRECATED_TRANSACTION_VERSION = 1
DEPRECATED_DECLARE_VERSION = 2
TRANSACTION_VERSION = 3
# The version is considered 0 for L1-Handler transaction hash calculation purposes.
L1_HANDLER_VERSION = 0
# Indentation for transactions meant to query and not addressed to the OS.
QUERY_VERSION_BASE = 2**128
DEPRECATED_QUERY_VERSION = QUERY_VERSION_BASE + DEPRECATED_TRANSACTION_VERSION
DEPRECATED_QUERY_DECLARE_VERSION = QUERY_VERSION_BASE + DEPRECATED_DECLARE_VERSION
DEPRECATED_OLD_DECLARE_VERSIONS = (
    0,
    1,
    QUERY_VERSION_BASE,
    QUERY_VERSION_BASE + 1,
)

# Sierra -> Casm compilation version.
SIERRA_VERSION = [1, 7, 0]
# Contract classes with sierra version older than MIN_SIERRA_VERSION are not supported.
MIN_SIERRA_VERSION = [1, 1, 0]

# Versions older than this compute the state diff from scratch at the feeder gateway.
MIN_GET_STATE_UPDATE_CALCULATION_VERSION = "0.12.3"

# The version of contract class leaf.
CONTRACT_CLASS_LEAF_VERSION: bytes = b"CONTRACT_CLASS_LEAF_V0"

# The version of the Starknet global state.
GLOBAL_STATE_VERSION = from_bytes(b"STARKNET_STATE_V0")

# The version of a compiled class.
COMPILED_CLASS_VERSION = from_bytes(b"COMPILED_CLASS_V1")

# State diff commitment.
BLOCK_SIGNATURE_VERSION = 1

# OS-related constants.
L1_TO_L2_MSG_HEADER_SIZE = 5
L2_TO_L1_MSG_HEADER_SIZE = 3
CLASS_UPDATE_SIZE = 1
# Header, unique values (at least one felt), pointers (at least one felt).
COMPRESSED_DA_SEGMENT_MIN_LENGTH = 3

# OS reserved contract addresses.
ORIGIN_ADDRESS = 0
BLOCK_HASH_CONTRACT_ADDRESS = 1
ALIAS_CONTRACT_ADDRESS = 2
OS_RESERVED_CONTRACT_ADDRESSES = [
    ORIGIN_ADDRESS,
    BLOCK_HASH_CONTRACT_ADDRESS,
    ALIAS_CONTRACT_ADDRESS,
]

# Stateful compression constants.
INITIAL_AVAILABLE_ALIAS = 128
MAX_NON_COMPRESSED_CONTRACT_ADDRESS = 15
ALIAS_COUNTER_STORAGE_KEY = 0
# StarkNet solidity contract-related constants.
N_DEFAULT_TOPICS = 1  # Events have one default topic.
# Excluding the default topic.
LOG_MSG_TO_L1_N_TOPICS = 2
CONSUMED_MSG_TO_L2_N_TOPICS = 3
# The headers include the payload size, so we need to add +1 since arrays are encoded with two
# additional parameters (offset and length) in solidity.
LOG_MSG_TO_L1_ENCODED_DATA_SIZE = (L2_TO_L1_MSG_HEADER_SIZE + 1) - LOG_MSG_TO_L1_N_TOPICS
CONSUMED_MSG_TO_L2_ENCODED_DATA_SIZE = (L1_TO_L2_MSG_HEADER_SIZE + 1) - CONSUMED_MSG_TO_L2_N_TOPICS

# Expected return values of a 'validate' entry point.
VALIDATE_RETDATA = [from_bytes(b"VALID")]

# The block number -> block hash mapping is written for the current block number minus this number.
STORED_BLOCK_HASH_BUFFER = 10

# Fee resources.
L1_GAS_RESOURCE_NAME_VALUE = from_bytes(b"L1_GAS")
L2_GAS_RESOURCE_NAME_VALUE = from_bytes(b"L2_GAS")
L1_DATA_GAS_RESOURCE_NAME_VALUE = from_bytes(b"L1_DATA")

# Flooring factor for block number in validate mode.
VALIDATE_BLOCK_NUMBER_ROUNDING = 100
# Flooring factor for timestamp in validate mode.
VALIDATE_TIMESTAMP_ROUNDING = 3600

DUMMY_SIERRA_VERSION_FOR_CAIRO0_CLASS_INFO = (0, 0, 0)


class ResourceCost:
    def __init__(self, numer: int, denom: int):
        assert numer >= 0 and denom > 0
        self.numer = numer
        self.denom = denom

    def __mul__(self, other: Union[int, "ResourceCost"]) -> "ResourceCost":
        if isinstance(other, int):
            return ResourceCost(numer=self.numer * other, denom=self.denom)
        return ResourceCost(numer=self.numer * other.numer, denom=self.denom * other.denom)

    def __rmul__(self, other: Union[int, "ResourceCost"]) -> "ResourceCost":
        return self * other

    def __add__(self, other: Union[int, "ResourceCost"]) -> "ResourceCost":
        if isinstance(other, int):
            return self + ResourceCost(numer=other, denom=1)
        return ResourceCost(
            numer=self.numer * other.denom + self.denom * other.numer,
            denom=self.denom * other.denom,
        )

    def __radd__(self, other: Union[int, "ResourceCost"]) -> "ResourceCost":
        return self + other

    def __lt__(self, other: "ResourceCost") -> bool:
        return self.numer * other.denom < self.denom * other.numer

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ResourceCost):
            return NotImplemented
        return self.numer * other.denom == self.denom * other.numer

    def __gt__(self, other: "ResourceCost") -> bool:
        return not (self == other or self < other)

    def floor(self) -> int:
        return self.numer // self.denom

    def ceil(self) -> int:
        return -(-self.numer // self.denom)


class OsOutputConstant(Enum):
    MERKLE_UPDATE_OFFSET = 0
    PREV_BLOCK_NUMBER_OFFSET = 2
    NEW_BLOCK_NUMBER_OFFSET = 3
    PREV_BLOCK_HASH_OFFSET = 4
    NEW_BLOCK_HASH_OFFSET = 5
    OS_PROGRAM_HASH_OFFSET = 6
    CONFIG_HASH_OFFSET = 7
    USE_KZG_DA_OFFSET = 8
    FULL_OUTPUT_OFFSET = 9
    HEADER_SIZE = 10

    # KZG segment relative offsets.
    KZG_Z_OFFSET = 0
    KZG_N_BLOBS_OFFSET = 1
    KZG_COMMITMENTS_OFFSET = 2


class GasCost(Enum):
    """
    See documentation in core/os/constants.cairo.
    """

    STEP = 100
    RANGE_CHECK = 70
    RANGE_CHECK96 = 56
    KECCAK_BUILTIN = 136189
    PEDERSEN = 4050
    BITWISE_BUILTIN = 583
    ECOP = 4085
    POSEIDON = 491
    ADD_MOD = 230
    MUL_MOD = 604
    ECDSA = 10561
    MEMORY_HOLE = 10
    DEFAULT_INITIAL = (10**8) * STEP

    # Compiler gas costs.
    SYSCALL_BASE = 100 * STEP
    ENTRY_POINT_INITIAL_BUDGET = 100 * STEP

    # Syscall cas costs.
    CALL_CONTRACT = 91560
    DEPLOY = 147120
    DEPLOY_CALLDATA_FACTOR = 4850
    GET_BLOCK_HASH = 10840
    GET_CLASS_HASH_AT = 10000
    GET_EXECUTION_INFO = 12640

    # Secp256k1.
    SECP256K1_ADD = 43230
    SECP256K1_GET_POINT_FROM_X = 41800
    SECP256K1_GET_XY = 21670
    SECP256K1_MUL = 8143850
    SECP256K1_NEW = 48750

    # Secp256r1.
    SECP256R1_ADD = 63490
    SECP256R1_GET_POINT_FROM_X = 54680
    SECP256R1_GET_XY = 21870
    SECP256R1_MUL = 13511870
    SECP256R1_NEW = 61630

    KECCAK = 10000
    KECCAK_ROUND_COST = 171707
    SHA256_PROCESS_BLOCK = 841295
    LIBRARY_CALL = 89160
    REPLACE_CLASS = 10670
    STORAGE_READ = 10000
    STORAGE_WRITE = 10000
    EMIT_EVENT = 10000
    SEND_MESSAGE_TO_L1 = 14470

    META_TX_V0 = 167950
    META_TX_V0_CALLDATA_FACTOR = 4850

    @property
    def int_value(self) -> int:
        assert isinstance(self.value, int)
        return self.value


def get_versioned_constants_json():
    """
    Returns the versioned constants as a JSON dict.
    """
    return json.load(VERSIONED_CONSTANTS_PATH.open())


@dataclasses.dataclass(frozen=True)
class ThinVersionedConstants:
    # General config.
    invoke_tx_max_n_steps: int
    validate_max_n_steps: int
    max_n_events: int

    # State manager config.
    max_recursion_depth: int

    # Gateway config.
    max_calldata_length: int
    max_contract_bytecode_size: int

    cairo_resource_fee_weights: Dict[str, ResourceCost]

    archival_data_gas_costs: Dict[str, "ResourceCost"]

    # Os kzg commitment info.
    kzg_commitment_n_steps: int
    kzg_commitment_builtin_instance_counter: Dict[str, int]

    # L2 gas per Cairo step.
    l2_gas_per_cairo_step: int

    @classmethod
    def create(cls):
        versioned_constants_json = get_versioned_constants_json()
        vm_resource_costs = versioned_constants_json["vm_resource_fee_cost"]

        return ThinVersionedConstants(
            invoke_tx_max_n_steps=versioned_constants_json["invoke_tx_max_n_steps"],
            validate_max_n_steps=versioned_constants_json["validate_max_n_steps"],
            max_n_events=versioned_constants_json["tx_event_limits"]["max_n_emitted_events"],
            max_recursion_depth=versioned_constants_json["max_recursion_depth"],
            max_calldata_length=versioned_constants_json["gateway"]["max_calldata_length"],
            max_contract_bytecode_size=versioned_constants_json["gateway"][
                "max_contract_bytecode_size"
            ],
            cairo_resource_fee_weights=dict(
                n_steps=ResourceCost(
                    numer=vm_resource_costs["n_steps"][0], denom=vm_resource_costs["n_steps"][1]
                ),
                **{
                    key: ResourceCost(numer=val[0], denom=val[1])
                    for key, val in vm_resource_costs["builtins"].items()
                },
            ),
            archival_data_gas_costs={
                key: ResourceCost(numer=val[0], denom=val[1])
                for key, val in versioned_constants_json["archival_data_gas_costs"].items()
            },
            kzg_commitment_n_steps=versioned_constants_json["os_resources"][
                "compute_os_kzg_commitment_info"
            ]["n_steps"],
            kzg_commitment_builtin_instance_counter=versioned_constants_json["os_resources"][
                "compute_os_kzg_commitment_info"
            ]["builtin_instance_counter"],
            l2_gas_per_cairo_step=versioned_constants_json["os_constants"]["step_gas_cost"],
        )

    def l1_to_l2_gas_price_conversion(self, l1_gas_price: int) -> int:
        return (l1_gas_price * self.l1_to_l2_gas_price_ratio()).ceil()

    def l1_to_l2_gas_price_ratio(self) -> ResourceCost:
        step_cost = self.cairo_resource_fee_weights["n_steps"]
        return ResourceCost(
            numer=step_cost.numer, denom=step_cost.denom * self.l2_gas_per_cairo_step
        )


VERSIONED_CONSTANTS = ThinVersionedConstants.create()

BUILTIN_INSTANCE_SIZES = {
    "pedersen": 3,
    "range_check": 1,
    "ecdsa": 2,
    "bitwise": 5,
    "ec_op": 7,
    "poseidon": 6,
    "segment_arena": 3,
    "range_check96": 1,
    "add_mod": 7,
    "mul_mod": 7,
    "keccak": 16,
}
