from typing import ClassVar, Optional, Type, TypeVar

import marshmallow

from starkware.starkware_utils.serializable import StringSerializable

TSerializableDataclass = TypeVar("TSerializableDataclass", bound="SerializableMarshmallowDataclass")


class SerializableMarshmallowDataclass(StringSerializable):
    """
    Base class to classes decorated with marshmallow_dataclass.dataclass, implementing the
    Serializable interface.
    """

    Schema: ClassVar[Type[marshmallow.Schema]]
    _schema_instance: ClassVar[Optional[marshmallow.Schema]] = None

    @classmethod
    def _schema(cls) -> marshmallow.Schema:
        """
        Returns a cached, reusable schema instance for this class.
        """
        schema = cls.__dict__.get("_schema_instance")
        if not schema:
            schema = cls.Schema()
            cls._schema_instance = schema
        return schema

    def dump(self) -> dict:
        return self._schema().dump(obj=self)

    @classmethod
    def load(cls: Type[TSerializableDataclass], data: dict) -> TSerializableDataclass:
        return cls._schema().load(data=data)

    def dumps(self, indent: Optional[int] = None, sort_keys: Optional[bool] = None) -> str:
        sort_keys = False if sort_keys is None else sort_keys
        # An indent level of 0 will only insert newlines; 'None' is the most compact representation.
        return self._schema().dumps(obj=self, indent=indent, sort_keys=sort_keys)

    @classmethod
    def loads(cls: Type[TSerializableDataclass], data: str) -> TSerializableDataclass:
        return cls._schema().loads(json_data=data)
