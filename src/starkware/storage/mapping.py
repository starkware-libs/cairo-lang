import dataclasses
import logging
from abc import abstractmethod
from dataclasses import field
from typing import Any  # noqa
from typing import Generic, Optional, Type, TypeVar

import marshmallow.fields as mfields

from starkware.python.utils import from_bytes, to_bytes
from starkware.starkware_utils.validated_dataclass import ValidatedDataclass
from starkware.storage.storage import DBObject, ObjectId, Storage
from starkware.storage.storage_conflict import StorageConflictError

logger = logging.getLogger(__name__)

TKey = TypeVar("TKey")
TValue = TypeVar("TValue")
TMapping = TypeVar("TMapping", bound="Mapping[Any, Any]")
TObjectId = TypeVar("TObjectId", bound="ObjectId")


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@dataclasses.dataclass(frozen=True)  # type: ignore[misc]
class Mapping(ValidatedDataclass, DBObject, Generic[TKey, TValue]):
    """
    Represents a mapping from type `TKey` to type `TValue`.
    """

    value: TValue = field(metadata={"marshmallow_field": mfields.Raw()})

    @classmethod
    @abstractmethod
    def encode_db_key(cls, key: TKey) -> bytes:
        """
        Transforms the given key into bytes.
        """

    @abstractmethod
    def serialize(self) -> bytes:
        pass

    @classmethod
    def deserialize(cls: Type[TMapping], data: bytes) -> TMapping:
        return cls(value=from_bytes(data))

    async def _setnx_value(self, storage: Storage, key: TKey) -> bool:
        return await self.setnx(storage=storage, suffix=self.encode_db_key(key=key))

    @classmethod
    async def create_and_setnx_value(cls, storage: Storage, key: TKey, value: TValue) -> bool:
        obj = cls(value=value)
        return await obj._setnx_value(storage=storage, key=key)

    @classmethod
    async def set_value(cls, storage: Storage, key: TKey, value: TValue):
        obj = cls(value=value)
        await obj.set(storage=storage, suffix=cls.encode_db_key(key=key))

    @classmethod
    async def setnx_or_same_value(
        cls, storage: Storage, key: TKey, value: TValue
    ) -> Optional[TValue]:
        """
        Attempts to store the value with the given key if it doesn't exist.
        If it does exist, checks if the existing value is the same as the provided one.
        Returns existing value if one exists and differs, None otherwise.
        """
        if await cls(value=value)._setnx_value(storage=storage, key=key) == True:
            logger.debug(f"Successfully mapped {cls.__name__} with {key=} to {value=}.")
            return None
        existing_value = await cls.get_value_or_fail(storage=storage, key=key)
        if existing_value == value:
            logger.warning(f"Mapping of {cls.__name__} with {key=} to {value=} already exists.")
            return None

        logger.error(
            f"Failed to write {cls.__name__} mapping of {key=} to {value=}, due to a different"
            f" value already set at the same key: {existing_value=}. This should never happen!"
        )
        return existing_value

    @classmethod
    async def _handle_setnx_or_same_value_conflict(
        cls, existing_mapped_value: Optional[TValue], expected_mapped_value: TValue
    ):
        """
        Handles the conflict when attempting to set a mapping using `setnx_or_same`, but
        an existing mapping is already present at the same `key`.

        Raises:
            StorageConflictError: If an object already exists at the intended `key`.
        """
        if existing_mapped_value is not None:
            # Found a different mapped value in storage at the same key. Should never get here!
            raise StorageConflictError(
                obj_name=cls.__name__,
                existing_obj=existing_mapped_value,
                expected_obj=expected_mapped_value,
            )

    @classmethod
    async def setnx_or_fail_value(cls, storage: Storage, key: TKey, value: TValue):
        """
        Attempts to store the value with the given key if it doesn't exist.
        If finds a different mapped value in the key raises an exception.
        """
        existing_mapped_value = await cls.setnx_or_same_value(storage=storage, key=key, value=value)
        await cls._handle_setnx_or_same_value_conflict(
            existing_mapped_value=existing_mapped_value, expected_mapped_value=value
        )

    @classmethod
    async def get_value(cls, storage: Storage, key: TKey) -> Optional[TValue]:
        obj = await cls.get(storage=storage, suffix=cls.encode_db_key(key))
        if obj is None:
            return None

        return obj.value

    @classmethod
    async def get_value_or_fail(cls, storage: Storage, key: TKey) -> TValue:
        """
        Reads the value object from storage under the given key, and
        returns its corresponding value. Raises an error, if does not exist in storage.
        """
        value = await cls.get_value(storage=storage, key=key)

        assert value is not None, f"{cls.__name__} value of key {key} does not appear in storage."

        return value


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@dataclasses.dataclass(frozen=True)  # type: ignore[misc]
class ToIntMapping(Mapping[TKey, int]):
    def serialize(self) -> bytes:
        byte_length = (self.value.bit_length() + 7) // 8  # Floor division.
        return to_bytes(value=self.value, length=byte_length)

    @classmethod
    async def create_and_setnx_int(cls, storage: Storage, key: TKey, value: int) -> bool:
        return await super().create_and_setnx_value(storage=storage, key=key, value=value)

    @classmethod
    async def set_int(cls, storage: Storage, key: TKey, value: int):
        await super().set_value(storage=storage, key=key, value=value)

    @classmethod
    async def setnx_or_same_int(cls, storage: Storage, key: TKey, value: int) -> Optional[int]:
        return await super().setnx_or_same_value(storage=storage, key=key, value=value)

    @classmethod
    async def setnx_or_fail_int(cls, storage: Storage, key: TKey, value: int):
        await super().setnx_or_fail_value(storage=storage, key=key, value=value)

    @classmethod
    async def get_int(cls, storage: Storage, key: TKey) -> Optional[int]:
        return await super().get_value(storage=storage, key=key)

    @classmethod
    async def get_int_or_fail(cls, storage: Storage, key: TKey) -> int:
        return await super().get_value_or_fail(storage=storage, key=key)


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@dataclasses.dataclass(frozen=True)  # type: ignore[misc]
class ToObjectIdMapping(Mapping[TKey, TObjectId]):
    def serialize(self) -> bytes:
        byte_length = (self.value.id.bit_length() + 7) // 8  # Floor division.
        return to_bytes(value=self.value.id, length=byte_length)

    @classmethod
    @abstractmethod
    def get_object_id_class(cls) -> Type[TObjectId]:
        """
        Returns the specific ObjectId subclass that this mapping uses as a value.
        Must be implemented by concrete subclasses.
        """

    @classmethod
    def deserialize(
        cls: Type["ToObjectIdMapping[TKey, TObjectId]"], data: bytes
    ) -> "ToObjectIdMapping[TKey, TObjectId]":
        object_id = cls.get_object_id_class()(id=from_bytes(data))
        return cls(value=object_id)

    @classmethod
    async def create_and_setnx_id(cls, storage: Storage, key: TKey, value: TObjectId) -> bool:
        return await super().create_and_setnx_value(storage=storage, key=key, value=value)

    @classmethod
    async def set_id(cls, storage: Storage, key: TKey, value: TObjectId):
        await super().set_value(storage=storage, key=key, value=value)

    @classmethod
    async def setnx_or_same_id(
        cls, storage: Storage, key: TKey, value: TObjectId
    ) -> Optional[TObjectId]:
        return await super().setnx_or_same_value(storage=storage, key=key, value=value)

    @classmethod
    async def setnx_or_fail_id(cls, storage: Storage, key: TKey, value: TObjectId):
        await super().setnx_or_fail_value(storage=storage, key=key, value=value)

    @classmethod
    async def get_id(cls, storage: Storage, key: TKey) -> Optional[TObjectId]:
        return await super().get_value(storage=storage, key=key)

    @classmethod
    async def get_id_or_fail(cls, storage: Storage, key: TKey) -> TObjectId:
        return await super().get_value_or_fail(storage=storage, key=key)


class IntToIntMapping(ToIntMapping[int]):
    """
    Represents a mapping from integer key to integer value.
    """

    @classmethod
    def encode_db_key(cls, key: int) -> bytes:
        return str(key).encode("ascii")


class ObjectIdToIntMapping(ToIntMapping[ObjectId]):
    """
    Represents a mapping from ObjectId key to integer value.
    """

    @classmethod
    def encode_db_key(cls, key: ObjectId) -> bytes:
        return str(key.id).encode("ascii")


class StringToIntMapping(ToIntMapping[str]):
    """
    Represents a mapping from a string key to an integer value.
    """

    @classmethod
    def encode_db_key(cls, key: str) -> bytes:
        return key.encode("ascii")


class StringToObjectIdMapping(ToObjectIdMapping[str, TObjectId], Generic[TObjectId]):
    """
    Represents a mapping from a string key to an ObjectId value.
    """

    @classmethod
    def encode_db_key(cls, key: str) -> bytes:
        return key.encode("ascii")
