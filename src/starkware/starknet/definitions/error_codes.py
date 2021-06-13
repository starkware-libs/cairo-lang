from enum import auto

from starkware.starkware_utils.error_handling import ErrorCode


class StarknetErrorCode(ErrorCode):
    BLOCK_NOT_FOUND = 0
    CONTRACT_ADDRESS_UNAVAILABLE = auto()
    ENTRY_POINT_NOT_FOUND_IN_CONTRACT = auto()
    INVALID_CONTRACT_DEFINITION = auto()
    INVALID_RETURN_DATA = auto()
    INVALID_TRANSACTION_ID = auto()
    MULTIPLE_ENTRY_POINTS_MATCH_SELECTOR = auto()
    OUT_OF_RANGE_BLOCK_ID = auto()
    OUT_OF_RANGE_CALL_DATA_ELEMENT = auto()
    OUT_OF_RANGE_CONTRACT_ADDRESS = auto()
    OUT_OF_RANGE_CONTRACT_STORAGE_KEY = auto()
    OUT_OF_RANGE_ENTRY_POINT_OFFSET = auto()
    OUT_OF_RANGE_ENTRY_POINT_SELECTOR = auto()
    SECURITY_ERROR = auto()
    TRANSACTION_FAILED = auto()
    UNEXPECTED_FAILURE = auto()
    UNINITIALIZED_CONTRACT = auto()
