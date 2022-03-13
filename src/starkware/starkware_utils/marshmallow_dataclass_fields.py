import base64
import functools
import re
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict

import marshmallow.fields as mfields
from frozendict import frozendict
from marshmallow import ValidationError
from marshmallow.base import FieldABC
from mypy_extensions import KwArg, VarArg

from starkware.starkware_utils.custom_raising_dict import CustomRaisingDict, CustomRaisingFrozenDict

OptionalFloat: Callable[[VarArg(), KwArg()], mfields.Float] = functools.partial(
    mfields.Float, allow_none=True
)
RequiredBoolean: Callable[[VarArg(), KwArg()], mfields.Boolean] = functools.partial(
    mfields.Boolean, truthy={True}, falsy={False}, required=True
)
RequiredFloat: Callable[[VarArg(), KwArg()], mfields.Float] = functools.partial(
    mfields.Float, required=True
)
StrictRequiredInteger: Callable[[VarArg(), KwArg()], mfields.Integer] = functools.partial(
    mfields.Integer, strict=True, required=True
)
StrictOptionalInteger: Callable[[VarArg(), KwArg()], mfields.Integer] = functools.partial(
    mfields.Integer, strict=True, allow_none=True
)


# Class definitions.


class IntAsStr(mfields.Field):
    """
    A field that behaves like an integer, but serializes to a string. Some amount fields are
    serialized to strings in the JSONs, so that JavaSscript can handle them (JavaScript cannot
    handle uint64 numbers).
    """

    default_error_messages = {"invalid": 'Expected int string, got: "{input}".'}

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        return str(value)

    def _deserialize(self, value, attr, data, **kwargs):
        if re.match("^-?[0-9]+$", value) is None:
            self.fail("invalid", input=value)

        return int(value)


class EnumField(mfields.Field):
    """
    A field that behaves like an enum, but serializes to a string.
    """

    def __init__(self, enum_cls, required: bool = False, allow_none: bool = False, **kwargs):
        self.enum_cls = enum_cls
        super().__init__(required=required, allow_none=allow_none, **kwargs)

    def _serialize(self, value, attr, obj, **kwargs):
        if value is not None:
            return value.name

        if self.allow_none:
            # value is None and None is allowed.
            return None

        raise ValidationError(
            message=f"Field of type {type(self).__name__} is None, but allow_none=False"
        )

    def _deserialize(self, value, attr, data, **kwargs):
        # No need to handle the case in which value is None, since public deserialize() method
        # takes care of that.
        return self.enum_cls[value]


class IntAsHex(mfields.Field):
    """
    A field that behaves like an integer, but serializes to a hex string. Usually, this applies to
    field elements.
    """

    default_error_messages = {"invalid": 'Expected hex string, got: "{input}".'}

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        assert isinstance(value, int)
        assert value >= 0, "IntAsHex does not support negative values."
        return hex(value)

    def _deserialize(self, value, attr, data, **kwargs):
        if re.match("^0x[0-9a-f]+$", value) is None:
            self.fail("invalid", input=value)

        return int(value, 16)


class BytesAsHex(mfields.Field):
    """
    A field that behaves like bytes, but serializes to a hex string.
    """

    default_error_messages = {"invalid": 'Expected hex string, got: "{input}".'}

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        assert isinstance(value, bytes)
        return value.hex()

    def _deserialize(self, value, attr, data, **kwargs):
        if re.match("^[0-9a-f]*$", value) is None:
            self.fail("invalid", input=value)

        return bytes.fromhex(value)


class BytesAsBase64Str(mfields.Field):
    """
    A field that behaves like bytes, but serializes to base64.
    """

    default_error_messages = {"invalid": 'Expected Base64 bytes, got: "{input}".'}

    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        assert isinstance(value, bytes)
        return base64.b64encode(value).decode("ascii")

    def _deserialize(self, value, attr, data, **kwargs):
        return base64.b64decode(value.encode("ascii"))


class CustomField(ABC):
    """
    A class representing a field deserialized into a variable of a specific type.
    """

    @property
    @classmethod
    @abstractmethod
    def _type(cls) -> type:
        pass

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)  # type: ignore[call-arg]

        assert issubclass(
            cls, FieldABC
        ), "CustomField must be used along with inheritance from a marshmallow field."

    def _deserialize(self, *args, **kwargs):
        return self._type(super()._deserialize(*args, **kwargs))  # type: ignore


class SetField(CustomField, mfields.List):
    _type = set


class VariadicLengthTupleField(CustomField, mfields.List):
    _type = tuple


class FrozenDictField(CustomField, mfields.Mapping):
    _type = frozendict


class CustomRaisingDictField(CustomField, mfields.Mapping):
    _type = CustomRaisingDict


class CustomRaisingFrozenDictField(CustomField, mfields.Mapping):
    _type = CustomRaisingFrozenDict


# Field metadata for general use in marshmallow dataclasses.


def enum_field_metadata(
    *, enum_class: type, require: bool = True, allow_none: bool = False
) -> dict:
    return dict(
        marshmallow_field=EnumField(enum_cls=enum_class, required=require, allow_none=allow_none)
    )


boolean_field_metadata: Dict[str, Any] = dict(marshmallow_field=RequiredBoolean())
optional_field_metadata: Dict[str, Any] = dict(allow_none=True, load_default=None)


# Utilities.


def load_int_value(field_metadata: Dict[str, Any], value: str) -> int:
    return field_metadata["marshmallow_field"]._deserialize(value=value, attr=None, data=None)
