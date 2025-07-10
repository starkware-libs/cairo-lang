import asyncio
import codecs
import contextlib
import dataclasses
import logging
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    cast,
)

from starkware.python.object_utils import generic_object_repr
from starkware.python.utils import from_bytes, get_exception_repr, to_bytes
from starkware.starkware_utils.config_base import get_object_by_path
from starkware.starkware_utils.serializable import Serializable
from starkware.starkware_utils.validated_dataclass import ValidatedDataclass
from starkware.storage.storage_conflict import StorageConflictError, StorageConflictStatus

logger = logging.getLogger(__name__)

HASH_BYTES = 32
MAX_OBJECT_SIZE_FOR_LOADING_IN_MAIN_THREAD = 2**20  # 1MB.
HashFunctionType = Callable[[bytes, bytes], bytes]

TDBObject = TypeVar("TDBObject", bound="DBObject")
TSingletonDBObject = TypeVar("TSingletonDBObject", bound="SingletonDBObject")
TIndexedDBObject = TypeVar("TIndexedDBObject", bound="IndexedDBObject")
TKey = TypeVar("TKey")
TIntMapping = TypeVar("TIntMapping", bound="IntMapping[Any]")


class Storage(ABC):
    """
    This is a base storage class, all storage classes should inherit from it.
    """

    @staticmethod
    async def create_instance_from_config(config: Dict[str, Any], logger=None) -> "Storage":
        """
        Creates a Storage instance from a config dictionary.
        """
        storage_class = get_object_by_path(path=config["class"])
        if hasattr(storage_class, "create_from_config"):
            storage_instance = await storage_class.create_from_config(**config["config"])
        else:
            storage_instance = storage_class(**config.get("config", {}))
        assert isinstance(storage_instance, Storage)
        if logger is not None:
            logger.info(f"Instance of {type(storage_instance)} was created.")
        return storage_instance

    @abstractmethod
    async def set_value(self, key: bytes, value: bytes):
        pass

    @abstractmethod
    async def get_value(self, key: bytes) -> Optional[bytes]:
        pass

    async def has_key(self, key: bytes) -> bool:
        return await self.get_value(key=key) is not None

    @abstractmethod
    async def del_value(self, key: bytes):
        pass

    async def mset(self, updates: Dict[bytes, bytes]):
        """
        Writes the given updates to storage.
        Raises an exception when one or more of the operations failed;
        in this case, the write might not be atomic.
        """
        raise NotImplementedError

    async def mget(self, keys: Sequence[bytes]) -> Tuple[Optional[bytes], ...]:
        """
        Reads and returns the values of the given keys.
        Returns None for each nonexistent key.
        """
        raise NotImplementedError

    async def mget_or_fail(self, keys: Sequence[bytes]) -> Tuple[bytes, ...]:
        """
        Same as mget, but raises an exception if one or more of the keys don't exist.
        """
        result = await self.mget(keys=keys)
        for i, value in enumerate(result):
            assert value is not None, f"Key {keys[i]!r} does not exist in storage."

        return cast(Tuple[bytes, ...], result)

    async def get_value_or_fail(self, key: bytes) -> bytes:
        assert isinstance(key, bytes)
        result = await self.get_value(key=key)
        assert result is not None, f"Key {key!r} unexpectedly does not appear in storage."
        return result

    async def set_int(self, key: bytes, value: int):
        assert isinstance(key, bytes)
        assert isinstance(value, int)
        value_bytes = str(value).encode("ascii")
        await self.set_value(key=key, value=value_bytes)

    async def setnx_int(self, key: bytes, value: int) -> bool:
        assert isinstance(key, bytes)
        assert isinstance(value, int)
        value_bytes = str(value).encode("ascii")
        return await self.setnx_value(key=key, value=value_bytes)

    async def get_int(self, key: bytes) -> Optional[int]:
        assert isinstance(key, bytes)
        result = await self.get_value(key=key)
        return None if result is None else int(result)

    async def get_int_or_default(self, key: bytes, default: int) -> int:
        assert isinstance(key, bytes)
        result = await self.get_value(key=key)
        return default if result is None else int(result)

    async def get_int_or_fail(self, key: bytes) -> int:
        assert isinstance(key, bytes)
        result = await self.get_value_or_fail(key=key)
        return int(result)

    async def set_float(self, key: bytes, value: float):
        assert isinstance(key, bytes)
        assert isinstance(value, float)
        value_bytes = str(value).encode("ascii")
        await self.set_value(key=key, value=value_bytes)

    async def setnx_float(self, key: bytes, value: float) -> bool:
        assert isinstance(key, bytes)
        assert isinstance(value, float)
        value_bytes = str(value).encode("ascii")
        return await self.setnx_value(key=key, value=value_bytes)

    async def get_float(self, key: bytes, default=None) -> Optional[float]:
        assert isinstance(key, bytes)
        result = await self.get_value(key=key)
        return default if result is None else float(result)

    async def set_str(self, key: bytes, value: str):
        assert isinstance(key, bytes)
        assert isinstance(value, str)
        value_bytes = value.encode("ascii")
        await self.set_value(key=key, value=value_bytes)

    async def setnx_str(self, key: bytes, value: str) -> bool:
        assert isinstance(key, bytes)
        assert isinstance(value, str)
        value_bytes = value.encode("ascii")
        return await self.setnx_value(key=key, value=value_bytes)

    async def get_str(self, key: bytes, default=None) -> Optional[str]:
        assert isinstance(key, bytes)
        result = await self.get_value(key=key)
        return default if result is None else result.decode("ascii")

    async def setnx_value(self, key: bytes, value: bytes) -> bool:
        raise NotImplementedError(f"{self.__class__.__name__} does not implement setnx_value")

    async def setnx_time(self, key: bytes, time: float):
        assert isinstance(key, bytes)
        assert isinstance(time, float)
        await self.setnx_float(key=key, value=time)

    async def get_time(self, key: bytes) -> Optional[float]:
        assert isinstance(key, bytes)
        return await self.get_float(key=key)


class LargeStorage(Storage, ABC):
    def __init__(self, bucket_name: str, prefix: str) -> None:
        self.bucket = bucket_name
        self.prefix = f"files/{prefix}"

    @abstractmethod
    async def set_file(
        self, file: str, key: bytes, bucket_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload file to large storage.
        """

    @abstractmethod
    async def set_large_file(
        self, file: str, key: bytes, bucket_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload large file to large storage.
        """

    def escape(self, key: bytes) -> str:
        return codecs.escape_encode(key)[0].decode("ascii")  # type: ignore

    def _get_bucket_and_key(self, key: bytes) -> Tuple[str, str]:
        """
        Returns a pair of bucket name and full key name (full key includes the prefix).
        """
        return self.bucket, f"{self.prefix}/{self.escape(key=key)}"


class DBObject(Serializable):
    @classmethod
    def db_key(cls, suffix: bytes) -> bytes:
        return cls.prefix() + b":" + suffix

    @classmethod
    async def get(cls: Type[TDBObject], storage: Storage, suffix: bytes) -> Optional[TDBObject]:
        """
        Returns the value under key cls.db_key(suffix) in the storage.
        If key does not exist, returns None.
        """
        result = await storage.get_value(key=cls.db_key(suffix=suffix))

        if result is None:
            return None

        if len(result) > MAX_OBJECT_SIZE_FOR_LOADING_IN_MAIN_THREAD:
            return await asyncio.get_event_loop().run_in_executor(None, cls.deserialize, result)
        else:
            return cls.deserialize(data=result)

    @classmethod
    async def has_key(cls: Type[TDBObject], storage: Storage, suffix: bytes) -> bool:
        return await storage.has_key(key=cls.db_key(suffix=suffix))

    @classmethod
    async def get_or_fail(cls: Type[TDBObject], storage: Storage, suffix: bytes) -> TDBObject:
        """
        Returns the value under key cls.db_key(suffix) in the storage.
        If key does not exist, raises an exception.
        """
        db_key = cls.db_key(suffix=suffix)
        result = await storage.get_value_or_fail(key=db_key)

        if len(result) > MAX_OBJECT_SIZE_FOR_LOADING_IN_MAIN_THREAD:
            return await asyncio.get_event_loop().run_in_executor(None, cls.deserialize, result)
        else:
            return cls.deserialize(data=result)

    async def set(self, storage: Storage, suffix: bytes):
        serialized = await asyncio.get_event_loop().run_in_executor(None, self.serialize)
        await storage.set_value(self.db_key(suffix), serialized)

    async def setnx(self, storage: Storage, suffix: bytes) -> bool:
        serialized = await asyncio.get_event_loop().run_in_executor(None, self.serialize)
        return await storage.setnx_value(self.db_key(suffix=suffix), value=serialized)

    def get_update_for_mset(self, suffix: bytes) -> Tuple[bytes, bytes]:
        """
        Returns a (key, value) pair that can be converted to a dict for mset.

        Usage:
            storage.mset(updates=dict(
                *[obj.get_indexed_update_for_mset(suffix) for key, obj in obj_updates.items()],
            ))
        """
        return (self.db_key(suffix=suffix), self.serialize())


class SingletonDBObject(DBObject):
    """
    A utility class for DBObjects expected to have at most one instance in storage.
    """

    @classmethod
    def suffix(cls) -> bytes:
        return b""

    @classmethod
    async def get_obj(
        cls: Type[TSingletonDBObject], storage: Storage
    ) -> Optional[TSingletonDBObject]:
        return await cls.get(storage=storage, suffix=cls.suffix())

    @classmethod
    async def get_obj_or_fail(
        cls: Type[TSingletonDBObject], storage: Storage
    ) -> TSingletonDBObject:
        return await cls.get_or_fail(storage=storage, suffix=cls.suffix())

    async def set_obj(self, storage: Storage):
        await self.set(storage=storage, suffix=self.suffix())

    async def setnx_obj(self, storage: Storage) -> bool:
        return await self.setnx(storage=storage, suffix=self.suffix())

    def get_obj_update_for_mset(self) -> Tuple[bytes, bytes]:
        return self.get_update_for_mset(suffix=self.suffix())


class IndexedDBObject(DBObject):
    """
    A db object with integer key.
    """

    @classmethod
    def key(cls, index: int) -> bytes:
        return cls.db_key(suffix=str(index).encode("ascii"))

    @classmethod
    async def get_obj(
        cls: Type[TIndexedDBObject], storage: Storage, index: int
    ) -> Optional[TIndexedDBObject]:
        return await cls.get(storage=storage, suffix=str(index).encode("ascii"))

    @classmethod
    async def get_obj_or_fail(
        cls: Type[TIndexedDBObject], storage: Storage, index: int
    ) -> TIndexedDBObject:
        db_object_or_aborted = await cls.get_obj(storage=storage, index=index)
        assert (
            db_object_or_aborted is not None
        ), f"{cls.__name__} at index {index} does not exist in storage."

        return db_object_or_aborted

    async def set_obj(self, storage: Storage, index: int):
        """
        Stores object in storage with given index.
        """
        await self.set(storage=storage, suffix=str(index).encode("ascii"))

    async def setnx_obj(self, storage: Storage, index: int) -> bool:
        return await self.setnx(storage=storage, suffix=str(index).encode("ascii"))

    async def setnx_or_same_obj(
        self, storage: Storage, index: int, fields_to_ignore: Optional[List[str]] = None
    ) -> Tuple[StorageConflictStatus, Optional["IndexedDBObject"]]:
        """
        Attempts to store the object with the given index if it doesn't exist.
        If it does exist, checks if the existing object is the same as this one,
        ignoring the fields specified by `fields_to_ignore` when comparing.
        Returns the existing object if one exists and differs, None otherwise
        """
        obj_cls = type(self)
        if await self.setnx_obj(storage=storage, index=index) == True:
            return StorageConflictStatus.NO_OBJECT, None

        existing_obj = await obj_cls.get_obj_or_fail(storage=storage, index=index)

        # Make sure objects are of the same type.
        if not isinstance(existing_obj, obj_cls):
            return StorageConflictStatus.DIFFERENT_CLASS, existing_obj

        # Create a deep copy of the current object and replace ignored fields with those
        # of the existing object.
        current_obj_to_compare = self
        if fields_to_ignore is not None and len(fields_to_ignore) > 0:
            field_overrides = {}
            for field in fields_to_ignore:
                if hasattr(current_obj_to_compare, field):
                    try:
                        field_overrides[field] = getattr(existing_obj, field)
                    except AttributeError:
                        continue
            if dataclasses.is_dataclass(current_obj_to_compare):
                current_obj_to_compare = dataclasses.replace(
                    current_obj_to_compare, **field_overrides
                )
            else:
                current_obj_to_compare = deepcopy(current_obj_to_compare)
                for field, value in field_overrides.items():
                    setattr(current_obj_to_compare, field, value)

        if current_obj_to_compare == existing_obj:
            return StorageConflictStatus.SAME_OBJECT, existing_obj

        # A different object was found.
        return StorageConflictStatus.DIFFERENT_OBJECT, existing_obj

    async def handle_setnx_or_same_obj_conflict(
        self,
        index: int,
        existing_obj: Optional["IndexedDBObject"],
        storage_conflict_status: StorageConflictStatus,
    ):
        """
        Handles the conflict when attempting to set an object using `setnx_or_same`, but
        an existing object is already present at the same `index`.

        Raises:
            StorageConflictError: If an object already exists at the intended `index`.
        """
        obj_cls = type(self)
        if storage_conflict_status == StorageConflictStatus.NO_OBJECT:
            logger.debug(f"Successfully set {obj_cls.__name__} at {index=} to {self}")
        elif storage_conflict_status == StorageConflictStatus.SAME_OBJECT:
            logger.warning(f"Found existing {obj_cls.__name__} object in storage at id {index}")
        else:
            # Found a different object in storage at the same id.
            # Should never get here!
            logger.error(
                f"Failed to write {obj_cls.__name__} object to storage at {index=}, due to a"
                " different object already set at the same index. This should never happen!\n"
                f" Failed setting the object {self}\n Found object: {existing_obj}"
            )
            raise StorageConflictError(
                obj_name=existing_obj.__class__.__name__,
                existing_obj=existing_obj,
                expected_obj=self,
            )

    async def setnx_or_fail_obj(
        self, storage: Storage, index: int, fields_to_ignore: Optional[List[str]] = None
    ):
        """
        Attempts to store the object with the given index if it doesn't exist.
        If finds a diffrent obj in the index raises an exception.
        """
        storage_conflict_status, existing_obj = await self.setnx_or_same_obj(
            storage=storage, index=index, fields_to_ignore=fields_to_ignore
        )
        await self.handle_setnx_or_same_obj_conflict(
            index=index, existing_obj=existing_obj, storage_conflict_status=storage_conflict_status
        )

    def get_indexed_update_for_mset(self, index: int) -> Tuple[bytes, bytes]:
        """
        Returns a (key, value) pair that can be converted to a dict for mset.

        Usage:
            storage.mset(updates=dict(
                *[obj.get_indexed_update_for_mset(index) for key, obj in obj_updates.items()],
            ))
        """
        return (self.key(index), self.serialize())


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@dataclasses.dataclass(frozen=True)  # type: ignore[misc]
class IntMapping(ValidatedDataclass, DBObject, Generic[TKey]):
    """
    Represents a mapping from type `TKey` to an `int` value.
    """

    value: int

    @classmethod
    @abstractmethod
    def encode_db_key(cls, key: TKey) -> bytes:
        """
        Transforms the given key into bytes.
        """

    def serialize(self) -> bytes:
        byte_length = (self.value.bit_length() + 7) // 8  # Floor division.
        return to_bytes(value=self.value, length=byte_length)

    @classmethod
    def deserialize(cls: Type[TIntMapping], data: bytes) -> TIntMapping:
        return cls(value=from_bytes(data))

    async def setnx_int(self, storage: Storage, key: TKey) -> bool:
        return await self.setnx(storage=storage, suffix=self.encode_db_key(key=key))

    @classmethod
    async def create_and_setnx_int(cls, storage: Storage, key: TKey, value: int) -> bool:
        obj = cls(value=value)
        return await obj.setnx_int(storage=storage, key=key)

    @classmethod
    async def set_int(cls, storage: Storage, key: TKey, value: int):
        obj = cls(value=value)
        await obj.set(storage=storage, suffix=cls.encode_db_key(key=key))

    @classmethod
    async def setnx_or_same_int(cls, storage: Storage, key: TKey, value: int) -> Optional[int]:
        """
        Attempts to store the int value with the given key if it doesn't exist.
        If it does exist, checks if the existing value is the same as the provided one.
        Returns existing value if one exists and differs, None otherwise
        """
        if await cls(value=value).setnx_int(storage=storage, key=key) == True:
            logger.debug(f"Successfully mapped {cls.__name__} with {key=} to {value=}.")
            return None
        existing_value = await cls.get_int_or_fail(storage=storage, key=key)
        if existing_value == value:
            logger.warning(f"Mapping of {cls.__name__} with {key=} to {value=} already exists.")
            return None

        logger.error(
            f"Failed to write {cls.__name__} mapping of {key=} to {value=}, due to a different"
            f" value already set at the same key: {existing_value=}. This should never happen!"
        )
        return existing_value

    @classmethod
    async def handle_setnx_or_same_int_conflict(
        cls, existing_mapped_value: Optional[int], expected_mapped_value: int
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
    async def setnx_or_fail_int(cls, storage: Storage, key: TKey, value: int):
        """
        Attempts to store the int value with the given key if it doesn't exist.
        If finds a different mapped value in the key raises an exception.
        """
        existing_mapped_value = await cls.setnx_or_same_int(storage=storage, key=key, value=value)
        await cls.handle_setnx_or_same_int_conflict(
            existing_mapped_value=existing_mapped_value, expected_mapped_value=value
        )

    @classmethod
    async def get_int(cls, storage: Storage, key: TKey) -> Optional[int]:
        obj = await cls.get(storage=storage, suffix=cls.encode_db_key(key))
        if obj is None:
            return None

        return obj.value

    @classmethod
    async def get_int_or_fail(cls, storage: Storage, key: TKey) -> int:
        """
        Reads the value object from storage under the given key, and
        returns its corresponding value. Raises an error, if does not exist in storage.
        """
        value = await cls.get_int(storage=storage, key=key)

        assert value is not None, f"{cls.__name__} value of key {key} does not appear in storage."

        return value


@dataclasses.dataclass(frozen=True)
class IntToIntMapping(IntMapping[int]):
    """
    Represents a mapping from integer key to integer value.
    """

    @classmethod
    def encode_db_key(cls, key: int) -> bytes:
        return str(key).encode("ascii")


@dataclasses.dataclass(frozen=True)
class StringToIntMapping(IntMapping[str]):
    """
    Represents a mapping from a string key to an integer value.
    """

    @classmethod
    def encode_db_key(cls, key: str) -> bytes:
        return key.encode("ascii")


class FactFetchingContext:
    """
    Information needed to fetch and store facts from a storage.
    A user may provide different implementations to the hash function in here.
    """

    def __init__(
        self,
        storage: Storage,
        hash_func: HashFunctionType,
        n_workers: Optional[int] = None,
        n_hash_workers: Optional[int] = None,
    ):
        self.storage = storage
        self.hash_func = hash_func
        self.n_workers = n_workers
        self.n_hash_workers = n_hash_workers

    def __repr__(self) -> str:
        return generic_object_repr(obj=self)


class Fact(DBObject):
    """
    A fact is a DB object with a DB key that is a hash of its value.
    Use set_fact() and get() to read and write facts.
    """

    @abstractmethod
    def _hash(self, hash_func: HashFunctionType) -> bytes:
        pass

    async def set_fact(self, ffc: FactFetchingContext) -> bytes:
        hash_val = self._hash(ffc.hash_func)
        await self.set(storage=ffc.storage, suffix=hash_val)
        return hash_val


class LockError(Exception):
    pass


class LockObject(ABC):
    @abstractmethod
    async def extend(self):
        pass

    @abstractmethod
    async def __aenter__(self) -> "LockObject":
        pass

    @abstractmethod
    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def safe_extend(self, name: str):
        try:
            await self.extend()
        except Exception as exception:
            logger.error(
                f"Exception while trying to extend lock {name}: "
                f"{get_exception_repr(exception=exception)}",
                exc_info=False,
            )
            logger.debug("Exception details", exc_info=True)


class LockManager(ABC):
    @staticmethod
    async def create_instance_from_config(config: Dict[str, Any], logger=None) -> "LockManager":
        """
        Creates a LockManager instance from a config dictionary.
        """
        lock_manager_class = get_object_by_path(path=config["class"])
        lock_manager_instance = lock_manager_class(**config["config"])
        if logger is not None:
            logger.info(f"Created instance of {type(lock_manager_instance)}")
        assert isinstance(lock_manager_instance, LockManager)
        return lock_manager_instance

    @staticmethod
    @contextlib.asynccontextmanager
    async def from_config_context(config, logger=None):
        lock_manager = await LockManager.create_instance_from_config(config=config, logger=logger)
        try:
            yield lock_manager
        finally:
            await lock_manager.destroy()

    @abstractmethod
    async def lock(self, name: str) -> LockObject:
        """
        Creates a lock object.
        """

    @abstractmethod
    async def lock_exists(self, name: str) -> bool:
        """
        Returns True iff lock object is exists.
        """

    @abstractmethod
    async def try_lock(self, name: str, ttl: int = None) -> LockObject:
        """
        Tries to create a lock object.
        """

    async def destroy(self):
        """
        Closes the LockManager.
        """
