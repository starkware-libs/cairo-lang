import asyncio

import pytest

from starkware.storage import Storage
from starkware.storage.dict_storage import DictStorage
from starkware.storage.test_utils import DummyLockManager


@pytest.mark.asyncio
async def test_dummy_lock():
    lock_manager = DummyLockManager()

    locked = [False]

    async def try_lock1():
        async with await lock_manager.lock('lock1') as _:
            locked[0] = True

    async with await lock_manager.lock('lock0') as lock:
        await lock.extend()
        async with await lock_manager.lock('lock1') as lock:
            # Try to lock.
            t = asyncio.create_task(try_lock1())
            await asyncio.sleep(0.01)
            assert locked[0] is False
        await asyncio.sleep(0.01)
        assert locked[0] is True
        await t


@pytest.mark.asyncio
async def test_from_config():
    config = {'class': 'starkware.storage.dict_storage.DictStorage', 'config': {}}

    storage = await Storage.from_config(config)
    assert type(storage) is DictStorage

    config['config']['bad_param'] = None
    with pytest.raises(TypeError, match='got an unexpected keyword argument'):
        await Storage.from_config(config)
