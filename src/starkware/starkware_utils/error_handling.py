import operator
from enum import Enum, auto
from typing import Any, Dict, Optional

symbol_to_function = {'!=': operator.ne, '==': operator.eq, '>': operator.gt, '>=': operator.ge}


class ErrorCode(Enum):
    """
    Base class of all error code enums.
    Do not add enum members to this class, only functionality.
    See: https://docs.python.org/3/library/enum.html#restricted-enum-subclassing.
    """


class StarkErrorCode(ErrorCode):
    #: Api function temporarily disabled.
    API_FUNCTION_TEMPORARILY_DISABLED = 0
    #: Batch creation failure; batch currently cannot be created.
    BATCH_CREATION_FAILURE = auto()
    #: Batch is full; there will be no additional attempt to insert any transactions.
    BATCH_FULL = auto()
    #: Batch not ready to be created; does not indicate an error.
    BATCH_NOT_READY = auto()
    #: Order amount exceeds capacity.
    CONFLICTING_ORDER_AMOUNTS = auto()
    #: Fact not registered in fact registry.
    FACT_NOT_REGISTERED = auto()
    #: Not enough onchain balance to complete deposit.
    INSUFFICIENT_ONCHAIN_BALANCE = auto()
    #: Invalid batch ID.
    INVALID_BATCH_ID = auto()
    #: Invalid committee claim hash.
    INVALID_CLAIM_HASH = auto()
    #: Invalid committee member key.
    INVALID_COMMITTEE_MEMBER = auto()
    #: StarkEx contracts information missing or corrupt.
    INVALID_CONTRACT_ADDRESS = auto()
    #: Invalid response from a contract (for example, Infura too many requests).
    INVALID_CONTRACT_RESPONSE = auto()
    #: StarkEx deployment information missing or corrupt.
    INVALID_DEPLOYMENT_INFO = auto()
    #: Invalid eth address.
    INVALID_ETH_ADDRESS = auto()
    #: Fact is not 32 bytes length.
    INVALID_FACT = auto()
    #: Fee taken is too high.
    INVALID_FEE_TAKEN = auto()
    #: Invalid order ID.
    INVALID_ORDER_ID = auto()
    #: Invalid order type.
    INVALID_ORDER_TYPE = auto()
    #: Invalid HTTP request.
    INVALID_REQUEST = auto()
    #: Invalid HTTP request parameters.
    INVALID_REQUEST_PARAMETERS = auto()
    #: Settlement trade amounts mismatch.
    INVALID_SETTLEMENT_INFO = auto()
    #: Settlement trade ratio not satisfied.
    INVALID_SETTLEMENT_RATIO = auto()
    #: Mismatching tokens for orders in settlement.
    INVALID_SETTLEMENT_TOKENS = auto()
    #: Invalid order signature.
    INVALID_SIGNATURE = auto()
    #: Invalid transaction.
    INVALID_TRANSACTION = auto()
    #: Invalid transaction ID.
    INVALID_TRANSACTION_ID = auto()
    #: Invalid vault.
    INVALID_VAULT = auto()
    #: Malformed request.
    MALFORMED_REQUEST = auto()
    #: Pipeline object is missing because it was migrated from an older version object.
    MIGRATED_PIPELINE_OBJECT_MISSING = auto()
    #: One of the fee objects is missing while the other exists.
    MISSING_FEE_OBJECT = auto()
    #: The order is expired.
    ORDER_OVERDUE = auto()
    #: Positive amount value is out of range.
    OUT_OF_RANGE_POSITIVE_AMOUNT = auto()
    #: Amount value is out of range.
    OUT_OF_RANGE_AMOUNT = auto()
    #: Vault balance is out of range.
    OUT_OF_RANGE_BALANCE = auto()
    #: Batch ID value is out of range.
    OUT_OF_RANGE_BATCH_ID = auto()
    #: Expiration timestamp value is out of range.
    OUT_OF_RANGE_EXPIRATION_TIMESTAMP = auto()
    #: Nonce value is out of range.
    OUT_OF_RANGE_NONCE = auto()
    #: Oracle price quorum value is out of range.
    OUT_OF_RANGE_ORACLE_PRICE_QUORUM = auto()
    #: Order ID value is out of range.
    OUT_OF_RANGE_ORDER_ID = auto()
    #: Public key (Stark key) value is out of range.
    OUT_OF_RANGE_PUBLIC_KEY = auto()
    #: Signature subfield is out of range.
    OUT_OF_RANGE_SIGNATURE_SUBFIELD = auto()
    #: Token ID value is out of range.
    OUT_OF_RANGE_TOKEN_ID = auto()
    #: Vault ID value is out of range.
    OUT_OF_RANGE_VAULT_ID = auto()
    #: Alternative transaction requested before for this transaction. Transaction is now valid.
    REPLACED_BEFORE = auto()
    #: Failed response for alternative transaction request.
    REQUEST_FAILED = auto()
    #: Object schema validation failed.
    SCHEMA_VALIDATION_ERROR = auto()
    #: Transaction received successfully by the gateway.
    TRANSACTION_PENDING = auto()
    TRANSACTION_RECEIVED = auto()


class WebFriendlyException(Exception):
    """
    Base class to exception classes that are exposed to the user, usually in a HTTP response body.
    """

    def __init__(self, status_code: int, body: Dict[str, Any]):
        self.status_code = status_code
        self.body = body
        super().__init__(status_code, body)


class StarkException(WebFriendlyException):
    """
    Base class to exceptions classes representing flows under the user's control (for example,
    an invalid transaction).
    """

    def __init__(self, code, message: Optional[str] = None):
        self.code = code
        self.message = message
        super().__init__(status_code=500, body={'code': code, 'message': message})

    def __repr__(self) -> str:
        return f'{type(self).__name__}(code={self.code}, message={self.message})'

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, StarkException):
            raise NotImplementedError

        return self.code == other.code and self.message == other.message


def stark_assert(expr: bool, code, message: Optional[str] = None):
    """
    Verifies that the given expression is True. If not, raises a StarkException with the given
    code and message.
    """
    if not expr:
        raise StarkException(code=code, message=message)


def stark_assert_eq(exp_val, actual_val, code, message: Optional[str] = None):
    """
    Verifies that the expected value is equal to the actual value, raising a StarkException with
    the appropriate code and message, where the expected and actual values are added to the message.
    """
    _stark_assert_not_symbol(exp_val, actual_val, symbol='!=', code=code, message=message)


def stark_assert_ne(exp_val, actual_val, code, message: Optional[str] = None):
    """
    Verifies that the expected value is not equal to the actual value, raising a StarkException
    with the appropriate code and message, where the expected and actual values are added to the
    message.
    """
    _stark_assert_not_symbol(exp_val, actual_val, symbol='==', code=code, message=message)


def stark_assert_le(exp_val, actual_val, code, message: Optional[str] = None):
    """
    Verifies that the expected value is less than or equal to the actual value, raising a
    StarkException with the appropriate code and message, where the expected and actual values are
    added to the message.
    """
    _stark_assert_not_symbol(exp_val, actual_val, symbol='>', code=code, message=message)


def stark_assert_lt(exp_val, actual_val, code, message: Optional[str] = None):
    """
    Verifies that the expected value is strictly less than the actual value, raising a
    StarkException with the appropriate code and message, where the expected and actual values are
    added to the message.
    """
    _stark_assert_not_symbol(exp_val, actual_val, symbol='>=', code=code, message=message)


def _stark_assert_not_symbol(
        exp_val, actual_val, symbol: str, code, message: Optional[str] = None):
    """
    Receives a symbol as a string that compares two values (e.g '==', '>') and verifies that:
    `not exp_val symbol actual_val`.

    Example:
        _stark_assert_not_symbol(3, 2, '==', code) -> Does nothing
        _stark_assert_not_symbol(3, 3, '==', code) -> Raises an exception

    the given symbol must be mapped by the dict `symbol_to_function` to a function that performs the
    symbol on two values.
    """
    MIN_HEX_SIZE = 1 << 128

    format_val = lambda val: hex(val) if isinstance(val, int) and val > MIN_HEX_SIZE else val
    if symbol_to_function[symbol](exp_val, actual_val):
        eq_log = f'{format_val(exp_val)} {symbol} {format_val(actual_val)}'
        message = f'{message}\n{eq_log}' if message else eq_log
        raise StarkException(code=code, message=message)
