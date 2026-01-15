import asyncio
import dataclasses
from typing import Any, Dict

import pytest

from starkware.storage.dict_storage import CachedStorage, DictStorage
from starkware.storage.storage import IndexedDBObject, IntToIntMapping, ObjectId, Storage
from starkware.storage.storage_conflict import StorageConflictError
from starkware.storage.test_utils import DummyLockManager, MockLargeStorage


@pytest.mark.asyncio
async def test_dummy_lock():
    lock_manager = DummyLockManager()

    locked = [False]

    async def try_lock1():
        async with await lock_manager.lock("lock1") as _:
            locked[0] = True

    async with await lock_manager.lock("lock0") as lock:
        await lock.extend()
        async with await lock_manager.lock("lock1") as lock:
            # Try to lock.
            t = asyncio.create_task(try_lock1())

            # Check that lock exists.
            assert await lock_manager.lock_exists("lock0")
            await asyncio.sleep(0.01)
            assert locked[0] is False
        await asyncio.sleep(0.01)
        assert locked[0] is True
        await t


@pytest.mark.asyncio
async def test_from_config():
    config: Dict[str, Any] = {"class": "starkware.storage.dict_storage.DictStorage", "config": {}}

    storage = await Storage.create_instance_from_config(config=config)
    assert type(storage) is DictStorage

    config["config"]["bad_param"] = None
    with pytest.raises(TypeError, match="got an unexpected keyword argument"):
        await Storage.create_instance_from_config(config=config)


def test_int_to_int_mapping_serializability():
    tested_object = IntToIntMapping(value=2021)
    serialized = tested_object.serialize()
    assert tested_object == IntToIntMapping.deserialize(data=serialized)


@pytest.mark.asyncio
async def test_cached_storage():
    storage = DictStorage()
    cached_storage = CachedStorage(storage=storage, max_size=1000)

    # Setup the storage.
    storage.db = {b"1": b"1", b"2": b"2"}

    # Write some values through the cached storage.
    await cached_storage.mset(updates={b"1": b"A", b"3": b"3"})

    # Test mget - change the DB manually to verify that the cached storage does not access it
    # for cached value.
    storage.db[b"3"] = b"C"
    assert await cached_storage.mget(keys=[b"1", b"2", b"4", b"3"]) == (b"A", b"2", None, b"3")

    # Check cache.
    assert cached_storage.cache == {b"1": b"A", b"2": b"2", b"3": b"3"}

    # Test `mget_or_fail`.
    with pytest.raises(AssertionError, match="Key b'4' does not exist in storage."):
        assert await cached_storage.mget_or_fail(keys=[b"1", b"2", b"4", b"3"])

    assert await cached_storage.mget_or_fail(keys=[b"3", b"1", b"2"]) == (b"3", b"A", b"2")


@pytest.mark.asyncio
async def test_get_bucket_and_key():
    test_bucket = "test-bucket"
    test_prefix = "test-prefix"
    test_key = "test-key"
    storage = MockLargeStorage(bucket_name=test_bucket, prefix=test_prefix)
    assert storage._get_bucket_and_key(key=test_key.encode("ascii")) == (
        test_bucket,
        "files/" + test_prefix + "/" + test_key,
    )


class TestStorage(DictStorage):
    async def setnx_value(self, key: bytes, value: bytes) -> bool:
        if key in self.db:
            return False
        self.db[key] = value
        return True


class TestId(ObjectId):
    def __str__(self) -> str:
        return f"test{self.id}"


@dataclasses.dataclass(frozen=True)
class TestIndexedDBObject(IndexedDBObject):
    """
    A simple test implementation of IndexedDBObject with in-memory storage capability.
    """

    value: str = ""

    @classmethod
    def prefix(cls) -> bytes:
        return b"test_obj"

    def serialize(self) -> bytes:
        return self.value.encode("utf-8")

    @classmethod
    def deserialize(cls, data: bytes) -> "TestIndexedDBObject":
        return cls(value=data.decode("utf-8"))


@pytest.mark.asyncio
async def test_union_typing():
    """Test IndexedDBObject methods with Union[int, ObjectId] index parameters."""
    storage = TestStorage()
    int_id = 1
    test_id = TestId(int_id)
    obj = TestIndexedDBObject(value="hello world")

    # Test `set_obj`.
    await obj.set_obj(storage=storage, index=int_id)
    await obj.set_obj(storage=storage, index=test_id)

    # Test `get_obj`.
    optional_obj_int = await TestIndexedDBObject.get_obj(storage=storage, index=int_id)
    optional_obj_test_id = await TestIndexedDBObject.get_obj(storage=storage, index=test_id)
    assert optional_obj_int == obj
    assert optional_obj_test_id == optional_obj_int

    # Test `get_obj_or_fail`.
    obj_int = await TestIndexedDBObject.get_obj_or_fail(storage=storage, index=int_id)
    obj_test_id = await TestIndexedDBObject.get_obj_or_fail(storage=storage, index=test_id)
    assert obj_int == obj
    assert obj_test_id == obj_int

    # Test `key`.
    key_int = TestIndexedDBObject.key(index=int_id)
    key_test_id = TestIndexedDBObject.key(index=test_id)
    assert key_int == b"test_obj:1"
    assert key_test_id == key_int

    # Test `setnx_obj`.
    assert await obj.setnx_obj(storage=storage, index=int_id) is False
    assert await obj.setnx_obj(storage=storage, index=test_id) is False
    assert await obj.setnx_obj(storage=storage, index=2) is True
    assert await obj.setnx_obj(storage=storage, index=TestId(3)) is True

    # Test `setnx_or_fail_obj` success.
    await obj.setnx_or_fail_obj(storage=storage, index=4)
    await obj.setnx_or_fail_obj(storage=storage, index=TestId(5))

    # Test `setnx_or_fail_obj` failure.
    different_obj = TestIndexedDBObject(value="hello universe")
    with pytest.raises(StorageConflictError):
        await different_obj.setnx_or_fail_obj(storage=storage, index=5)
    with pytest.raises(StorageConflictError):
        await different_obj.setnx_or_fail_obj(storage=storage, index=TestId(4))
