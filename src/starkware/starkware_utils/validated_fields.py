import dataclasses
import random
from abc import ABC, abstractmethod
from typing import Any, Callable, ClassVar, Dict, Generic, List, Optional, Type, TypeVar

import marshmallow.fields as mfields

from starkware.python.utils import initialize_random
from starkware.starkware_utils.error_handling import ErrorCode, stark_assert
from starkware.starkware_utils.field_validators import validate_in_range
from starkware.starkware_utils.marshmallow_dataclass_fields import (
    BytesAsBase64Str, BytesAsHex, IntAsHex, IntAsStr)

T = TypeVar('T')


class Field(ABC, Generic[T]):
    """
    A class representing data types for fields in ValidatedMarshmallowDataclass.
    A dataclass field using this should have the following in its metadata:
    1.  Data needed for @dataclasses.dataclass fields: 'description', 'default',
        'default_factory', etc. ,
    2.  Data needed for marshmallow: in 'marshmallow_field' ,
    3.  An object implementing this Field class: in 'validated_field' ,
    4.  A name for messages: in 'name_in_messages'.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The default name that appears in messages.
        """

    @abstractmethod
    def format(self, value) -> str:
        """
        The formatted value that appears in messages.
        """

    # Randomization.

    @abstractmethod
    def get_random_value(self, random_object: Optional[random.Random] = None) -> T:
        """
        Returns a random valid value for this field.
        """

    # Validation.

    @abstractmethod
    def is_valid(self, value: T) -> bool:
        """
        Checks and returns if the given value is valid.
        """

    def validate(self, value: T, name: Optional[str] = None):
        error_message = self.format_invalid_value_error_message(value=value, name=name)
        stark_assert(self.is_valid(value=value), code=self.error_code, message=error_message)

    @property
    @abstractmethod
    def error_code(self) -> ErrorCode:
        """
        The error codes that is returned if the value is not valid.
        """

    @abstractmethod
    def get_invalid_values(self) -> List[T]:
        """
        Returns a list of invalid values for this field.
        """

    @abstractmethod
    def format_invalid_value_error_message(self, value: T, name: Optional[str] = None) -> str:
        """
        Constructs the error message for invalid values.
        """

    # Serialization.
    @abstractmethod
    def get_marshmallow_field(self) -> mfields.Field:
        """
        Returns a marshmallow field that serializes and deserializes values of this field.
        """

    # Metadata.

    def metadata(self, field_name: Optional[str] = None):
        """
        Creates the metadata associated with this field. If provided, then use the given field_name
        for messages, and otherwise (if it is None) use the default name.
        """
        return dict(
            marshmallow_field=self.get_marshmallow_field(),
            validated_field=self,
            name_in_messages=self.name if field_name is None else field_name)


@dataclasses.dataclass(frozen=True)
class RangeValidatedField(Field[int]):
    """
    Represents a range-validated integer field.
    """

    lower_bound: int  # Inclusive.
    upper_bound: int  # Non-inclusive.
    name_in_error_message: str
    out_of_range_error_code: ErrorCode
    formatter: Optional[Callable[[int], str]] = None
    out_of_range_message: ClassVar[str] = '{field_name} {field_value} is out of range'

    @property
    def name(self):
        return self.name_in_error_message

    def format(self, value: int) -> str:
        return self._format_value(value=value)

    def get_random_value(self, random_object: Optional[random.Random] = None) -> int:
        r = initialize_random(random_object)
        return r.randrange(self.lower_bound, self.upper_bound)

    def is_valid(self, value: int) -> bool:
        return self.lower_bound <= value < self.upper_bound

    def format_invalid_value_error_message(self, value: int, name: Optional[str] = None) -> str:
        return self.out_of_range_message.format(
            field_name=self.name if name is None else name,
            field_value=self._format_value(value))

    @property
    def error_code(self) -> ErrorCode:
        return self.out_of_range_error_code

    def get_invalid_values(self) -> List[int]:
        return [self.lower_bound - 1, self.upper_bound]

    def _format_value(self, value: int) -> str:
        if self.formatter is None:
            return str(value)
        return self.formatter(value)

    def get_marshmallow_field(self) -> mfields.Field:
        if self.formatter == hex:
            return IntAsHex(required=True)
        if self.formatter == str:
            return IntAsStr(required=True)
        if self.formatter is None:
            return mfields.Integer(required=True)
        raise NotImplementedError(
            f'{self.name}: The given formatter {self.formatter.__name__} '
            'does not have a suitable metadata.')


# Field metadata utilities.

def _generate_metadata(
        marshmallow_field_cls: Type[mfields.Field], validated_field: Optional[Field],
        required: Optional[bool] = None) -> Dict[str, Any]:
    if required is None:
        required = True

    metadata: Dict[str, Any] = dict(marshmallow_field=marshmallow_field_cls(required=required))
    if validated_field is not None:
        metadata.update(validated_field=validated_field)

    return metadata


def int_metadata(
        validated_field: Optional[Field], required: Optional[bool] = None) -> Dict[str, Any]:
    return _generate_metadata(
        marshmallow_field_cls=mfields.Integer, validated_field=validated_field, required=required)


def int_as_hex_metadata(
        validated_field: Optional[Field], required: Optional[bool] = None) -> Dict[str, Any]:
    return _generate_metadata(
        marshmallow_field_cls=IntAsHex, validated_field=validated_field, required=required)


def int_as_str_metadata(
        validated_field: Optional[Field], required: Optional[bool] = None) -> Dict[str, Any]:
    return _generate_metadata(
        marshmallow_field_cls=IntAsStr, validated_field=validated_field, required=required)


def bytes_as_hex_metadata(
        validated_field: Optional[Field], required: Optional[bool] = None) -> Dict[str, Any]:
    return _generate_metadata(
        marshmallow_field_cls=BytesAsHex, validated_field=validated_field, required=required)


def bytes_as_base64_str_metadata(
        validated_field: Optional[Field], required: Optional[bool] = None) -> Dict[str, Any]:
    return _generate_metadata(
        marshmallow_field_cls=BytesAsBase64Str, validated_field=validated_field, required=required)


def sequential_id_metadata(
        field_name: str, required: bool = True,
        allow_previous_id: bool = False) -> Dict[str, Any]:
    validator = validate_in_range(field_name=field_name, min_value=-1 if allow_previous_id else 0)
    return dict(
        marshmallow_field=mfields.Integer(strict=True, required=required, validate=validator))
