from typing import Any, Dict, Optional

import marshmallow
import marshmallow_dataclass

from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass


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
