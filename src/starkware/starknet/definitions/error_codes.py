from enum import auto
from typing import FrozenSet, List

from starkware.starkware_utils.error_handling import ErrorCode, StarkErrorCode


class StarknetErrorCode(ErrorCode):
    BLOCK_NOT_FOUND = 0
    CONTRACT_ADDRESS_UNAVAILABLE = auto()
    CONTRACT_BYTECODE_SIZE_TOO_LARGE = auto()
    CONTRACT_DEFINITION_OBJECT_SIZE_TOO_LARGE = auto()
    ENTRY_POINT_NOT_FOUND_IN_CONTRACT = auto()
    INVALID_BLOCK_NUMBER = auto()
    INVALID_BLOCK_TIMESTAMP = auto()
    INVALID_CONTRACT_DEFINITION = auto()
    INVALID_PROGRAM = auto()
    INVALID_RETURN_DATA = auto()
    INVALID_STATUS_MODE = auto()
    INVALID_TRANSACTION_ID = auto()
    L1_TO_L2_MESSAGE_ZEROED_COUNTER = auto()
    MULTIPLE_ENTRY_POINTS_MATCH_SELECTOR = auto()
    NON_PERMITTED_CONTRACT = auto()
    OUT_OF_RANGE_ADDRESS = auto()
    OUT_OF_RANGE_BLOCK_HASH = auto()
    OUT_OF_RANGE_BLOCK_ID = auto()
    OUT_OF_RANGE_CALLER_ADDRESS = auto()
    OUT_OF_RANGE_CONTRACT_ADDRESS = auto()
    OUT_OF_RANGE_CONTRACT_HASH = auto()
    OUT_OF_RANGE_CONTRACT_ADDRESS_SALT = auto()
    OUT_OF_RANGE_CONTRACT_STORAGE_KEY = auto()
    OUT_OF_RANGE_ENTRY_POINT_OFFSET = auto()
    OUT_OF_RANGE_ENTRY_POINT_SELECTOR = auto()
    OUT_OF_RANGE_SEQUENCER_ADDRESS = auto()
    OUT_OF_RANGE_TRANSACTION_HASH = auto()
    OUT_OF_RANGE_TRANSACTION_ID = auto()
    OUT_OF_RESOURCES = auto()
    SECURITY_ERROR = auto()
    TRANSACTION_FAILED = auto()
    TRANSACTION_LIMIT_EXCEEDED = auto()
    TRANSACTION_NOT_FOUND = auto()
    UNEXPECTED_FAILURE = auto()
    UNINITIALIZED_CONTRACT = auto()


# Errors that are raised by the gateways and caused by wrong usage of the user.

external_txs_loading_common_error_codes: List[ErrorCode] = [
    # Raw builtin exceptions from pre/post_load/dump are wrapped with StarkExcpetion and this code.
    StarkErrorCode.MALFORMED_REQUEST,
    StarkErrorCode.OUT_OF_RANGE_FIELD_ELEMENT,
    StarkErrorCode.SCHEMA_VALIDATION_ERROR,
    StarknetErrorCode.OUT_OF_RANGE_ENTRY_POINT_OFFSET,
    StarknetErrorCode.OUT_OF_RANGE_ENTRY_POINT_SELECTOR,
]

main_gateway_error_code_whitelist: FrozenSet[ErrorCode] = frozenset(
    [
        *external_txs_loading_common_error_codes,
        # Signature validation errors.
        StarkErrorCode.INVALID_SIGNATURE,
        # External deploy loading errors.
        StarknetErrorCode.CONTRACT_BYTECODE_SIZE_TOO_LARGE,
        StarknetErrorCode.CONTRACT_DEFINITION_OBJECT_SIZE_TOO_LARGE,
        StarknetErrorCode.INVALID_CONTRACT_DEFINITION,
        StarknetErrorCode.INVALID_PROGRAM,
        StarknetErrorCode.MULTIPLE_ENTRY_POINTS_MATCH_SELECTOR,
        StarknetErrorCode.NON_PERMITTED_CONTRACT,
        StarknetErrorCode.OUT_OF_RANGE_CONTRACT_ADDRESS_SALT,
        # Reaching traffic limits.
        StarknetErrorCode.TRANSACTION_LIMIT_EXCEEDED,
    ]
)

feeder_gateway_error_code_whitelist: FrozenSet[ErrorCode] = frozenset(
    [
        *external_txs_loading_common_error_codes,
        # Requests that fail after quering the DB.
        StarknetErrorCode.BLOCK_NOT_FOUND,
        StarknetErrorCode.TRANSACTION_NOT_FOUND,
        StarknetErrorCode.UNINITIALIZED_CONTRACT,
        # Function call errors.
        StarknetErrorCode.ENTRY_POINT_NOT_FOUND_IN_CONTRACT,
        StarknetErrorCode.INVALID_RETURN_DATA,
        StarknetErrorCode.SECURITY_ERROR,
        StarknetErrorCode.TRANSACTION_FAILED,
        # Request parsing errors.
        StarkErrorCode.MALFORMED_REQUEST,
        StarknetErrorCode.INVALID_STATUS_MODE,
        StarknetErrorCode.OUT_OF_RANGE_BLOCK_HASH,
        StarknetErrorCode.OUT_OF_RANGE_BLOCK_ID,
        StarknetErrorCode.OUT_OF_RANGE_CONTRACT_ADDRESS,
        StarknetErrorCode.OUT_OF_RANGE_CONTRACT_STORAGE_KEY,
        StarknetErrorCode.OUT_OF_RANGE_TRANSACTION_HASH,
        StarknetErrorCode.OUT_OF_RANGE_TRANSACTION_ID,
    ]
)
