from enum import Enum, auto


class TransactionType(Enum):
    DECLARE = 0
    DEPLOY = auto()
    INITIALIZE_BLOCK_INFO = auto()
    INVOKE_FUNCTION = auto()
