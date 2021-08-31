from enum import auto
from typing import FrozenSet, List

from starkware.starkware_utils.error_handling import ErrorCode, StarkErrorCode


class StarknetErrorCode(ErrorCode):
    BLOCK_NOT_FOUND = 0
    CONTRACT_ADDRESS_UNAVAILABLE = auto()
    ENTRY_POINT_NOT_FOUND_IN_CONTRACT = auto()
    INVALID_CONTRACT_DEFINITION = auto()
    INVALID_FIELD_ELEMENT = auto()
    INVALID_PROGRAM = auto()
    INVALID_RETURN_DATA = auto()
    INVALID_STATUS_MODE = auto()
    INVALID_TRANSACTION_ID = auto()
    L1_TO_L2_MESSAGE_ZEROED_COUNTER = auto()
    MULTIPLE_ENTRY_POINTS_MATCH_SELECTOR = auto()
    OUT_OF_RANGE_BLOCK_ID = auto()
    OUT_OF_RANGE_CONTRACT_ADDRESS = auto()
    OUT_OF_RANGE_CONTRACT_STORAGE_KEY = auto()
    OUT_OF_RANGE_ENTRY_POINT_OFFSET = auto()
    OUT_OF_RANGE_ENTRY_POINT_SELECTOR = auto()
    OUT_OF_RANGE_TRANSACTION_ID = auto()
    OUT_OF_RESOURCES = auto()
    SECURITY_ERROR = auto()
    TRANSACTION_FAILED = auto()
    UNEXPECTED_FAILURE = auto()
    UNINITIALIZED_CONTRACT = auto()


# Errors that are raised by the gateways and caused by wrong usage of the user.

external_txs_loading_common_error_codes: List[ErrorCode] = [
    StarknetErrorCode.INVALID_FIELD_ELEMENT,
    StarknetErrorCode.OUT_OF_RANGE_ENTRY_POINT_OFFSET,
    StarknetErrorCode.OUT_OF_RANGE_ENTRY_POINT_SELECTOR,
    StarkErrorCode.SCHEMA_VALIDATION_ERROR,
]

main_gateway_error_code_whitelist: FrozenSet[ErrorCode] = frozenset(
    [
        *external_txs_loading_common_error_codes,
        # Signature validation errors.
        StarkErrorCode.INVALID_SIGNATURE,
        # External deploy loading errors.
        StarknetErrorCode.INVALID_CONTRACT_DEFINITION,
        StarknetErrorCode.INVALID_PROGRAM,
        StarknetErrorCode.MULTIPLE_ENTRY_POINTS_MATCH_SELECTOR,
    ]
)

feeder_gateway_error_code_whitelist: FrozenSet[ErrorCode] = frozenset(
    [
        *external_txs_loading_common_error_codes,
        # Requests that fail after quering the DB.
        StarknetErrorCode.UNINITIALIZED_CONTRACT,
        StarknetErrorCode.BLOCK_NOT_FOUND,
        # Function call errors.
        StarknetErrorCode.ENTRY_POINT_NOT_FOUND_IN_CONTRACT,
        StarknetErrorCode.INVALID_RETURN_DATA,
        StarknetErrorCode.SECURITY_ERROR,
        StarknetErrorCode.TRANSACTION_FAILED,
        # Request parsing errors.
        StarknetErrorCode.INVALID_STATUS_MODE,
        StarknetErrorCode.OUT_OF_RANGE_BLOCK_ID,
        StarknetErrorCode.OUT_OF_RANGE_CONTRACT_ADDRESS,
        StarknetErrorCode.OUT_OF_RANGE_CONTRACT_STORAGE_KEY,
        StarknetErrorCode.OUT_OF_RANGE_TRANSACTION_ID,
        StarkErrorCode.MALFORMED_REQUEST,
    ]
)
