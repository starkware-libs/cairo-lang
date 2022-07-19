from typing import Any, Dict

import marshmallow

from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass


class BaseResponseObject:
    """
    Contains common functionality to response objects from the FeederGateway.
    """

    @marshmallow.post_dump
    def remove_none_values(self, data: Dict[Any, Any], many: bool = False) -> Dict[Any, Any]:
        return {key: value for key, value in data.items() if value is not None}


class ValidatedResponseObject(BaseResponseObject, ValidatedMarshmallowDataclass):
    """
    Validated version of BaseResponseObject.
    This class must not contain a marshmallow schema and should not be directly (de)serialized.
    """
