from enum import Enum, auto
from typing import FrozenSet, List

from starkware.python.utils import from_bytes
from starkware.starkware_utils.error_handling import ErrorCode, StarkErrorCode


class StarknetErrorCode(ErrorCode):
    BLOCK_NOT_FOUND = 0
    SENDER_ADDRESS_IS_BLOCKED = auto()
    CLASS_ALREADY_DECLARED = auto()
    COMPILATION_FAILED = auto()
    CONTRACT_ADDRESS_UNAVAILABLE = auto()
    CONTRACT_BYTECODE_SIZE_TOO_LARGE = auto()
    CONTRACT_CLASS_OBJECT_SIZE_TOO_LARGE = auto()
    DEPRECATED_TRANSACTION = auto()
    ENTRY_POINT_NOT_FOUND_IN_CONTRACT = auto()
    EXTERNAL_TO_INTERNAL_CONVERSION_ERROR = auto()
    FEE_TRANSFER_FAILURE = auto()
    INVALID_BLOCK_NUMBER = auto()
    INVALID_BLOCK_TIMESTAMP = auto()
    INVALID_COMPILED_CLASS = auto()
    INVALID_COMPILED_CLASS_HASH = auto()
    INVALID_CONTRACT_CLASS = auto()
    INVALID_CONTRACT_CLASS_VERSION = auto()
    INVALID_PROGRAM = auto()
    INVALID_RETURN_DATA = auto()
    INVALID_STATUS_MODE = auto()
    INVALID_TRANSACTION_HASH = auto()
    INVALID_TRANSACTION_ID = auto()
    INVALID_TRANSACTION_NONCE = auto()
    INVALID_TRANSACTION_QUERYING_VERSION = auto()
    INVALID_TRANSACTION_VERSION = auto()
    L1_TO_L2_MESSAGE_CANCELLED = auto()
    L1_TO_L2_MESSAGE_INSUFFICIENT_FEE = auto()
    L1_TO_L2_MESSAGE_ZEROED_COUNTER = auto()
    MISSING_ENTRY_POINT_FOR_INVOKE = auto()
    MULTIPLE_ENTRY_POINTS_MATCH_SELECTOR = auto()
    NON_EMPTY_SIGNATURE = auto()
    NON_PERMITTED_CONTRACT = auto()
    NO_TRACE = auto()
    OUT_OF_RANGE_ADDRESS = auto()
    OUT_OF_RANGE_BLOCK_HASH = auto()
    OUT_OF_RANGE_BLOCK_ID = auto()
    OUT_OF_RANGE_CALLER_ADDRESS = auto()
    OUT_OF_RANGE_CLASS_HASH = auto()
    OUT_OF_RANGE_COMPILED_CLASS_HASH = auto()
    OUT_OF_RANGE_CONTRACT_ADDRESS = auto()
    OUT_OF_RANGE_CONTRACT_STORAGE_KEY = auto()
    OUT_OF_RANGE_ENTRY_POINT_FUNCTION_IDX = auto()
    OUT_OF_RANGE_ENTRY_POINT_OFFSET = auto()
    OUT_OF_RANGE_ENTRY_POINT_SELECTOR = auto()
    OUT_OF_RANGE_FEE = auto()
    OUT_OF_RANGE_GAS_PRICE = auto()
    OUT_OF_RANGE_NONCE = auto()
    OUT_OF_RANGE_SEQUENCER_ADDRESS = auto()
    OUT_OF_RANGE_TRANSACTION_HASH = auto()
    OUT_OF_RANGE_TRANSACTION_ID = auto()
    OUT_OF_RANGE_TRANSACTION_VERSION = auto()
    OUT_OF_RESOURCES = auto()
    SECURITY_ERROR = auto()
    TRANSACTION_FAILED = auto()
    TRANSACTION_LIMIT_EXCEEDED = auto()
    TRANSACTION_NOT_FOUND = auto()
    UNAUTHORIZED_ACTION_ON_VALIDATE = auto()
    UNAUTHORIZED_ENTRY_POINT_FOR_INVOKE = auto()
    UNDECLARED_CLASS = auto()
    UNEXPECTED_FAILURE = auto()
    UNINITIALIZED_CONTRACT = auto()
    UNSUPPORTED_TRANSACTION = auto()


# Errors that are raised by the gateways and caused by wrong usage of the user.

common_error_codes: List[ErrorCode] = [
    # Raw builtin exceptions from pre/post_load/dump are wrapped with StarkException and this code.
    StarkErrorCode.MALFORMED_REQUEST,
    StarkErrorCode.OUT_OF_RANGE_FIELD_ELEMENT,
    StarkErrorCode.SCHEMA_VALIDATION_ERROR,
    StarknetErrorCode.INVALID_TRANSACTION_NONCE,
    StarknetErrorCode.NON_EMPTY_SIGNATURE,
    StarknetErrorCode.OUT_OF_RANGE_CONTRACT_ADDRESS,
    StarknetErrorCode.OUT_OF_RANGE_ENTRY_POINT_FUNCTION_IDX,
    StarknetErrorCode.OUT_OF_RANGE_ENTRY_POINT_OFFSET,
    StarknetErrorCode.OUT_OF_RANGE_ENTRY_POINT_SELECTOR,
    StarknetErrorCode.OUT_OF_RANGE_FEE,
    StarknetErrorCode.OUT_OF_RANGE_TRANSACTION_VERSION,
    # External-to-internal conversion errors.
    StarknetErrorCode.EXTERNAL_TO_INTERNAL_CONVERSION_ERROR,
    StarknetErrorCode.INVALID_TRANSACTION_QUERYING_VERSION,
    StarknetErrorCode.INVALID_TRANSACTION_VERSION,
    StarknetErrorCode.MISSING_ENTRY_POINT_FOR_INVOKE,
    StarknetErrorCode.UNAUTHORIZED_ENTRY_POINT_FOR_INVOKE,
    # Contract class validation.
    StarknetErrorCode.COMPILATION_FAILED,
    StarknetErrorCode.INVALID_COMPILED_CLASS_HASH,
    StarknetErrorCode.INVALID_CONTRACT_CLASS,
    StarknetErrorCode.INVALID_CONTRACT_CLASS_VERSION,
    # Validate execution.
    StarknetErrorCode.UNAUTHORIZED_ACTION_ON_VALIDATE,
]

main_gateway_error_code_whitelist: FrozenSet[ErrorCode] = frozenset(
    [
        *common_error_codes,
        StarknetErrorCode.DEPRECATED_TRANSACTION,
        StarknetErrorCode.SENDER_ADDRESS_IS_BLOCKED,
        # Signature validation errors.
        StarkErrorCode.INVALID_SIGNATURE,
        # External deploy loading errors.
        StarknetErrorCode.CONTRACT_BYTECODE_SIZE_TOO_LARGE,
        StarknetErrorCode.CONTRACT_CLASS_OBJECT_SIZE_TOO_LARGE,
        StarknetErrorCode.INVALID_PROGRAM,
        StarknetErrorCode.MULTIPLE_ENTRY_POINTS_MATCH_SELECTOR,
        StarknetErrorCode.NON_PERMITTED_CONTRACT,
        # Reaching traffic limits.
        StarknetErrorCode.TRANSACTION_LIMIT_EXCEEDED,
    ]
)

feeder_gateway_error_code_whitelist: FrozenSet[ErrorCode] = frozenset(
    [
        *common_error_codes,
        # Requests that fail after quering the DB.
        StarknetErrorCode.BLOCK_NOT_FOUND,
        StarknetErrorCode.INVALID_TRANSACTION_HASH,
        StarknetErrorCode.NO_TRACE,
        StarknetErrorCode.TRANSACTION_NOT_FOUND,
        StarknetErrorCode.UNINITIALIZED_CONTRACT,
        # Function call errors.
        StarknetErrorCode.CLASS_ALREADY_DECLARED,
        StarknetErrorCode.CONTRACT_ADDRESS_UNAVAILABLE,
        StarknetErrorCode.ENTRY_POINT_NOT_FOUND_IN_CONTRACT,
        StarknetErrorCode.FEE_TRANSFER_FAILURE,
        StarknetErrorCode.INVALID_COMPILED_CLASS,
        StarknetErrorCode.INVALID_RETURN_DATA,
        StarknetErrorCode.INVALID_TRANSACTION_VERSION,
        StarknetErrorCode.L1_TO_L2_MESSAGE_INSUFFICIENT_FEE,
        StarknetErrorCode.OUT_OF_RESOURCES,
        StarknetErrorCode.SECURITY_ERROR,
        StarknetErrorCode.TRANSACTION_FAILED,
        StarknetErrorCode.UNDECLARED_CLASS,
        StarknetErrorCode.UNEXPECTED_FAILURE,
        # Request parsing errors.
        StarkErrorCode.MALFORMED_REQUEST,
        StarknetErrorCode.INVALID_STATUS_MODE,
        StarknetErrorCode.OUT_OF_RANGE_BLOCK_HASH,
        StarknetErrorCode.OUT_OF_RANGE_BLOCK_ID,
        StarknetErrorCode.OUT_OF_RANGE_CLASS_HASH,
        StarknetErrorCode.OUT_OF_RANGE_COMPILED_CLASS_HASH,
        StarknetErrorCode.OUT_OF_RANGE_CONTRACT_ADDRESS,
        StarknetErrorCode.OUT_OF_RANGE_CONTRACT_STORAGE_KEY,
        StarknetErrorCode.OUT_OF_RANGE_TRANSACTION_HASH,
        StarknetErrorCode.OUT_OF_RANGE_TRANSACTION_ID,
        StarknetErrorCode.UNSUPPORTED_TRANSACTION,
    ]
)

internal_gateway_error_code_whitelist: FrozenSet[ErrorCode] = frozenset(
    [
        *common_error_codes,
        StarkErrorCode.INVALID_REQUEST,
        StarkErrorCode.INVALID_REQUEST_PARAMETERS,
        StarkErrorCode.OUT_OF_RANGE_BATCH_ID,
    ]
)


class CairoErrorCode(Enum):
    """
    Error codes returned by Cairo 1.0 code.
    """

    OUT_OF_GAS = "Out of gas"
    INVALID_INPUT_LEN = "Invalid input length"

    def to_felt(self) -> int:
        return from_bytes(self.value.encode("ascii"))
