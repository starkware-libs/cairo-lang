from enum import auto

from services.everest.api.gateway.transaction_type import TransactionTypeBase


class TransactionType(TransactionTypeBase):
    DECLARE = 0
    DEPLOY = auto()
    DEPLOY_ACCOUNT = auto()
    INITIALIZE_BLOCK_INFO = auto()
    INVOKE_FUNCTION = auto()
    L1_HANDLER = auto()
