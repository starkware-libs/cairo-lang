import dataclasses
import json
from enum import Enum
from pathlib import Path
from typing import Dict, Union

from starkware.crypto.signature.signature import FIELD_PRIME
from starkware.python.utils import from_bytes
from starkware.storage.storage import HASH_BYTES

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
SIERRA_VERSION = [1, 6, 0]
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

# OS reserved contract addresses.
ORIGIN_ADDRESS = 0
BLOCK_HASH_CONTRACT_ADDRESS = 1
OS_RESERVED_CONTRACT_ADDRESSES = [ORIGIN_ADDRESS, BLOCK_HASH_CONTRACT_ADDRESS]

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

# Flooring factor for block number in validate mode.
VALIDATE_BLOCK_NUMBER_ROUNDING = 100
# Flooring factor for timestamp in validate mode.
VALIDATE_TIMESTAMP_ROUNDING = 3600


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
    BITWISE_BUILTIN = 594
    MEMORY_HOLE = 10
    INITIAL = (10**8) * STEP

    # Compiler gas costs.
    SYSCALL_BASE = 100 * STEP
    ENTRY_POINT_INITIAL_BUDGET = 100 * STEP

    # OS gas costs.
    ENTRY_POINT = ENTRY_POINT_INITIAL_BUDGET + 500 * STEP
    FEE_TRANSFER = ENTRY_POINT + 100 * STEP
    TRANSACTION = (2 * ENTRY_POINT) + FEE_TRANSFER + (100 * STEP)
    # Syscall cas costs.
    CALL_CONTRACT = SYSCALL_BASE + 10 * STEP + ENTRY_POINT
    DEPLOY = SYSCALL_BASE + 200 * STEP + ENTRY_POINT
    GET_BLOCK_HASH = SYSCALL_BASE + 50 * STEP
    GET_EXECUTION_INFO = SYSCALL_BASE + 10 * STEP

    # Secp256k1.
    SECP256K1_ADD = 406 * STEP + 29 * RANGE_CHECK
    SECP256K1_GET_POINT_FROM_X = 391 * STEP + 30 * RANGE_CHECK + 20 * MEMORY_HOLE
    SECP256K1_GET_XY = 239 * STEP + 11 * RANGE_CHECK + 40 * MEMORY_HOLE
    SECP256K1_MUL = 76501 * STEP + 7045 * RANGE_CHECK + 2 * MEMORY_HOLE
    SECP256K1_NEW = 475 * STEP + 35 * RANGE_CHECK + 40 * MEMORY_HOLE

    # Secp256r1.
    SECP256R1_ADD = 589 * STEP + 57 * RANGE_CHECK
    SECP256R1_GET_POINT_FROM_X = 510 * STEP + 44 * RANGE_CHECK + 20 * MEMORY_HOLE
    SECP256R1_GET_XY = 241 * STEP + 11 * RANGE_CHECK + 40 * MEMORY_HOLE
    SECP256R1_MUL = 125340 * STEP + 13961 * RANGE_CHECK + 2 * MEMORY_HOLE
    SECP256R1_NEW = 594 * STEP + 49 * RANGE_CHECK + 40 * MEMORY_HOLE

    KECCAK = SYSCALL_BASE
    KECCAK_ROUND_COST = 180000
    SHA256_PROCESS_BLOCK = (
        1115 * BITWISE_BUILTIN + 65 * RANGE_CHECK + 1852 * STEP + 1 * SYSCALL_BASE
    )
    LIBRARY_CALL = CALL_CONTRACT
    REPLACE_CLASS = SYSCALL_BASE + 50 * STEP
    STORAGE_READ = SYSCALL_BASE + 50 * STEP
    STORAGE_WRITE = SYSCALL_BASE + 50 * STEP
    EMIT_EVENT = SYSCALL_BASE + 10 * STEP
    SEND_MESSAGE_TO_L1 = SYSCALL_BASE + 50 * STEP

    @property
    def int_value(self) -> int:
        assert isinstance(self.value, int)
        return self.value


@dataclasses.dataclass(frozen=True)
class ThinVersionedConstants:
    VERSIONED_CONSTANTS_FILE_NAME = "versioned_constants.json"
    VERSIONED_CONSTANTS_PATH = Path(__file__).parent / VERSIONED_CONSTANTS_FILE_NAME

    # General config.
    invoke_tx_max_n_steps: int
    validate_max_n_steps: int

    # State manager config.
    max_recursion_depth: int

    # Gateway config.
    max_calldata_length: int
    max_contract_bytecode_size: int

    cairo_resource_fee_weights: Dict[str, ResourceCost]

    l2_resource_gas_costs: Dict[str, "ResourceCost"]

    # Os kzg commitment info.
    kzg_commitment_n_steps: int
    kzg_commitment_builtin_instance_counter: Dict[str, int]

    @classmethod
    def create(cls):
        versioned_constants_json = json.load(cls.VERSIONED_CONSTANTS_PATH.open())

        return ThinVersionedConstants(
            invoke_tx_max_n_steps=versioned_constants_json["invoke_tx_max_n_steps"],
            validate_max_n_steps=versioned_constants_json["validate_max_n_steps"],
            max_recursion_depth=versioned_constants_json["max_recursion_depth"],
            max_calldata_length=versioned_constants_json["gateway"]["max_calldata_length"],
            max_contract_bytecode_size=versioned_constants_json["gateway"][
                "max_contract_bytecode_size"
            ],
            cairo_resource_fee_weights={
                key: ResourceCost(numer=val[0], denom=val[1])
                for key, val in versioned_constants_json["vm_resource_fee_cost"].items()
            },
            l2_resource_gas_costs={
                key: ResourceCost(numer=val[0], denom=val[1])
                for key, val in versioned_constants_json["l2_resource_gas_costs"].items()
            },
            kzg_commitment_n_steps=versioned_constants_json["os_resources"][
                "compute_os_kzg_commitment_info"
            ]["n_steps"],
            kzg_commitment_builtin_instance_counter=versioned_constants_json["os_resources"][
                "compute_os_kzg_commitment_info"
            ]["builtin_instance_counter"],
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
