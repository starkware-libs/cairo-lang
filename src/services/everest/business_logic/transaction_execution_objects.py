from typing import Any, Dict, Optional

import marshmallow
import marshmallow_dataclass

from starkware.starkware_utils.error_handling import StarkException
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass


class EverestTransactionExecutionInfo(ValidatedMarshmallowDataclass):
    """
    Base class of classes containing information generated from an execution of a transaction on
    the state. Each Everest application may implement it specifically.
    Note that this object will only be relevant if the transaction executed successfully.
    """


@marshmallow_dataclass.dataclass(frozen=True)
class TransactionExecutionInfo(EverestTransactionExecutionInfo):
    """
    A non-abstract derived class for completeness of AggregatedScope. Used by StarkEx and Perpetual.
    """


@marshmallow_dataclass.dataclass(frozen=True)
class TransactionFailureReason(ValidatedMarshmallowDataclass):
    """
    Contains the failure reason (error code and error message) of an invalid
    transaction.
    """

    code: str
    error_message: Optional[str]

    @marshmallow.decorators.pre_load
    def remove_tx_id(self, data: Dict[str, Any], many: bool, **kwargs) -> Dict[str, Any]:
        data.pop("tx_id", None)
        return data

    @marshmallow.decorators.post_dump
    def truncate_error_message(self, data: Dict[str, Any], many: bool, **kwargs) -> Dict[str, Any]:
        error_message = data["error_message"]
        if error_message is None:
            # Do nothing.
            return data

        data["error_message"] = error_message[:5000]
        return data

    @classmethod
    def from_exception(cls, exception: StarkException) -> "TransactionFailureReason":
        return cls(code=exception.code.name, error_message=exception.message)
