from enum import Enum

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
MAX_MESSAGE_TO_L1_LENGTH = 100
NONCE_LOWER_BOUND = 0
NONCE_UPPER_BOUND = 2**NONCE_BITS
SIERRA_ARRAY_LEN_BOUND = 2**32
SYSCALL_SELECTOR_UPPER_BOUND = FIELD_SIZE
TRANSACTION_COMMITMENT_TREE_HEIGHT = 64
TRANSACTION_HASH_LOWER_BOUND = 0
TRANSACTION_HASH_UPPER_BOUND = FIELD_SIZE
TRANSACTION_VERSION_LOWER_BOUND = 0
TRANSACTION_VERSION_UPPER_BOUND = FIELD_SIZE
ADDRESS_LOWER_BOUND = 0
ADDRESS_UPPER_BOUND = 2**ADDRESS_BITS
UNINITIALIZED_CLASS_HASH = bytes(HASH_BYTES)


# In order to identify transactions from unsupported versions.
TRANSACTION_VERSION = 1
# The version is considered 0 for L1-Handler transaction hash calculation purposes.
L1_HANDLER_VERSION = 0
# Indentation for transactions meant to query and not addressed to the OS.
DECLARE_VERSION = 2
QUERY_VERSION_BASE = 2**128
QUERY_VERSION = QUERY_VERSION_BASE + TRANSACTION_VERSION
QUERY_DECLARE_VERSION = QUERY_VERSION_BASE + DECLARE_VERSION
DEPRECATED_DECLARE_VERSIONS = (
    0,
    1,
    QUERY_VERSION_BASE,
    QUERY_VERSION_BASE + 1,
)

# Sierra -> Casm compilation version.
SIERRA_VERSION = [1, 0, 0]

# The version of contract class leaf.
CONTRACT_CLASS_LEAF_VERSION: bytes = b"CONTRACT_CLASS_LEAF_V0"

# The version of the Starknet global state.
GLOBAL_STATE_VERSION = from_bytes(b"STARKNET_STATE_V0")

# The version of a compiled class.
COMPILED_CLASS_VERSION = from_bytes(b"COMPILED_CLASS_V1")

# OS-related constants.
L1_TO_L2_MSG_HEADER_SIZE = 5
L2_TO_L1_MSG_HEADER_SIZE = 3
CLASS_UPDATE_SIZE = 1

# StarkNet solidity contract-related constants.
N_DEFAULT_TOPICS = 1  # Events have one default topic.
# Excluding the default topic.
LOG_MSG_TO_L1_N_TOPICS = 2
CONSUMED_MSG_TO_L2_N_TOPICS = 3
# The headers include the payload size, so we need to add +1 since arrays are encoded with two
# additional parameters (offset and length) in solidity.
LOG_MSG_TO_L1_ENCODED_DATA_SIZE = (L2_TO_L1_MSG_HEADER_SIZE + 1) - LOG_MSG_TO_L1_N_TOPICS
CONSUMED_MSG_TO_L2_ENCODED_DATA_SIZE = (L1_TO_L2_MSG_HEADER_SIZE + 1) - CONSUMED_MSG_TO_L2_N_TOPICS

# The (empirical) L1 gas cost of each Cairo step.
N_STEPS_FEE_WEIGHT = 0.01

# Expected return values of a 'validate' entry point.
VALIDATE_RETDATA = [from_bytes(b"VALID")]


class OsOutputConstant(Enum):
    MERKLE_UPDATE_OFFSET = 0
    BLOCK_NUMBER_OFFSET = 2
    BLOCK_HASH_OFFSET = 3
    CONFIG_HASH_OFFSET = 4
    HEADER_SIZE = 5


class GasCost(Enum):
    """
    See documentation in core/os/constants.cairo.
    """

    STEP = 100
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
    GET_EXECUTION_INFO = SYSCALL_BASE + 10 * STEP
    KECCAK = SYSCALL_BASE
    KECCAK_ROUND_COST = 180000
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
