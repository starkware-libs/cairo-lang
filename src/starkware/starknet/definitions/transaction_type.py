from enum import Enum, auto


class TransactionType(Enum):
    DEPLOY = 0
    INITIALIZE_BLOCK_INFO = auto()
    INVOKE_FUNCTION = auto()
