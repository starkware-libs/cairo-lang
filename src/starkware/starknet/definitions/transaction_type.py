from enum import Enum, auto


class TransactionType(Enum):
    DEPLOY = 0
    INVOKE_FUNCTION = auto()
