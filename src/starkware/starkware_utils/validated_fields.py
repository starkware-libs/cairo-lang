import copy
import dataclasses
import random
from abc import ABC, abstractmethod
from typing import Any, Callable, ClassVar, Dict, Generic, List, Optional, Type, TypeVar

import marshmallow.fields as mfields

from starkware.python.utils import get_random_bytes, initialize_random
from starkware.starkware_utils.error_handling import ErrorCode, stark_assert
from starkware.starkware_utils.field_validators import validate_in_range
from starkware.starkware_utils.marshmallow_dataclass_fields import (
    BytesAsBase64Str,
    BytesAsHex,
    IntAsHex,
    IntAsStr,
)

T = TypeVar("T")


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@dataclasses.dataclass(frozen=True)  # type: ignore
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

    name: str
    error_code: ErrorCode

    @property
    @classmethod
    @abstractmethod
    def error_message(cls) -> str:
        """
        The default error message that appears when the value is invalid.
        Subclasses should define it as a class variable.
        """

    @abstractmethod
    def format(self, value: T) -> str:
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
            name_in_messages=self.name if field_name is None else field_name,
        )


class OptionalField(Field[Optional[T]]):
    """
    A wrapper class for a field, allowing it to be None.
    Loading a class with an optional field, where the serialized data for that class doesn't contain
    a value for this field, will load the class with a None value in this field.
    """

    # Class variables:
    error_message: ClassVar[str] = "Invalid OptionalField value {value}"

    def __init__(self, field: Field[T], none_probability: float):
        """
        Wraps the given field as an optional field. The probability to get None in
        get_random_value is going to be none_probability. Otherwise, it returns a random value from
        the wrapped field.
        """
        super().__init__(name=field.name, error_code=field.error_code)
        self.field = field
        self.none_probability = max(0, min(1, none_probability))
        self.mfield: mfields.Field = copy.copy(self.field.get_marshmallow_field())  # type: ignore
        self.mfield.allow_none = True
        self.mfield.missing = None
        self.mfield.required = False

    def format(self, value: Optional[T]) -> str:
        if value is None:
            return "None"
        return self.field.format(value=value)

    # Randomization.
    def get_random_value(self, random_object: Optional[random.Random] = None) -> Optional[T]:
        r = initialize_random(random_object=random_object)
        if r.random() < self.none_probability:
            return None
        return self.field.get_random_value(random_object=r)

    # Validation.
    def is_valid(self, value: Optional[T]) -> bool:
        return value is None or self.field.is_valid(value=value)

    def get_invalid_values(self) -> List[Optional[T]]:
        return [value for value in self.field.get_invalid_values() if value is not None]

    def format_invalid_value_error_message(
        self, value: Optional[T], name: Optional[str] = None
    ) -> str:
        if value is None:
            return f"{name} is valid (None)."
        return self.field.format_invalid_value_error_message(value=value, name=name)

    def get_marshmallow_field(self) -> mfields.Field:
        return self.mfield


@dataclasses.dataclass(frozen=True)
class RangeValidatedField(Field[int]):
    """
    Represents a range-validated integer field.
    """

    lower_bound: int  # Inclusive.
    upper_bound: int  # Non-inclusive.
    formatter: Optional[Callable[[int], str]] = None

    # Class variables:
    error_message: ClassVar[str] = "{field_name} {field_value} is out of range"

    def format(self, value: int) -> str:
        return self._format_value(value=value)

    def get_random_value(self, random_object: Optional[random.Random] = None) -> int:
        r = initialize_random(random_object)
        return r.randrange(self.lower_bound, self.upper_bound)

    def is_valid(self, value: int) -> bool:
        return self.lower_bound <= value < self.upper_bound

    def format_invalid_value_error_message(self, value: int, name: Optional[str] = None) -> str:
        return self.error_message.format(
            field_name=self.name if name is None else name,
            field_value=self._format_value(value),
        )

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
            f"{self.name}: The given formatter {self.formatter.__name__} "
            "does not have a suitable metadata."
        )


class BytesLengthField(Field[bytes]):
    """
    Represents a field with value of type bytes, of a given length.
    """

    error_message: ClassVar[str] = "{field_name} {field_value} is out of range"

    def __init__(self, name: str, error_code: ErrorCode, length: int):
        super().__init__(name=name, error_code=error_code)

        assert length > 0, "Bytes length must be at least 1."
        self.length = length

    # Randomization.
    def get_random_value(self, random_object: Optional[random.Random] = None) -> bytes:
        return get_random_bytes(random_object, n=self.length)

    # Validation.
    def is_valid(self, value: bytes) -> bool:
        return len(value) == self.length

    def get_invalid_values(self) -> List[bytes]:
        return [b"\x00" * (self.length - 1), b"\x00" * (self.length + 1)]

    def format_invalid_value_error_message(self, value: bytes, name: Optional[str] = None) -> str:
        name = self.name if name is None else name
        value_repr = self.format(value=value)
        return f"{name} {value_repr} length is not {self.length} bytes, instead it is {len(value)}"

    # Serialization.
    def get_marshmallow_field(self) -> mfields.Field:
        return BytesAsHex(required=True)

    def format(self, value: bytes) -> str:
        return value.hex()


# Field metadata utilities.


def _generate_metadata(
    marshmallow_field_cls: Type[mfields.Field],
    validated_field: Optional[Field],
    required: Optional[bool] = None,
) -> Dict[str, Any]:
    if required is None:
        required = True

    metadata: Dict[str, Any] = dict(marshmallow_field=marshmallow_field_cls(required=required))
    if validated_field is not None:
        metadata.update(validated_field=validated_field)

    return metadata


def int_metadata(
    validated_field: Optional[Field], required: Optional[bool] = None
) -> Dict[str, Any]:
    return _generate_metadata(
        marshmallow_field_cls=mfields.Integer, validated_field=validated_field, required=required
    )


def int_as_hex_metadata(
    validated_field: Optional[Field], required: Optional[bool] = None
) -> Dict[str, Any]:
    return _generate_metadata(
        marshmallow_field_cls=IntAsHex, validated_field=validated_field, required=required
    )


def int_as_str_metadata(
    validated_field: Optional[Field], required: Optional[bool] = None
) -> Dict[str, Any]:
    return _generate_metadata(
        marshmallow_field_cls=IntAsStr, validated_field=validated_field, required=required
    )


def bytes_as_hex_metadata(
    validated_field: Optional[Field], required: Optional[bool] = None
) -> Dict[str, Any]:
    return _generate_metadata(
        marshmallow_field_cls=BytesAsHex, validated_field=validated_field, required=required
    )


def bytes_as_base64_str_metadata(
    validated_field: Optional[Field], required: Optional[bool] = None
) -> Dict[str, Any]:
    return _generate_metadata(
        marshmallow_field_cls=BytesAsBase64Str, validated_field=validated_field, required=required
    )



def sequential_id_metadata(
    field_name: str,
    required: bool = True,
    allow_previous_id: bool = False,
    allow_none: bool = False,
) -> Dict[str, Any]:
    validator = validate_in_range(
        field_name=field_name, min_value=-1 if allow_previous_id else 0, allow_none=allow_none
    )
    return dict(
        marshmallow_field=mfields.Integer(
            strict=True, required=required, allow_none=allow_none, validate=validator
        )
    )
