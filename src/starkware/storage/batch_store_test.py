import asyncio
import logging

import pytest

from starkware.storage.batch_store import BatchStore
from starkware.storage.test_utils import DelayedStorage

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_batch_store():
    inner_store = DelayedStorage(0.01, 0.01)
    storage = BatchStore(storage=inner_store, n_workers_set=2, n_workers_get=2)

    async def set_value(val_id):
        await storage.set_value(f"key{val_id}".encode("ascii"), f"value{val_id}".encode("ascii"))

    async def get_value(val_id):
        assert await storage.get_value_or_fail(
            key=f"key{val_id}".encode("ascii")
        ) == f"value{val_id}".encode("ascii")

    tasks = [asyncio.create_task(set_value(i)) for i in range(4)]
    await asyncio.sleep(0.02)
    tasks += [asyncio.create_task(get_value(i)) for i in range(4)]
    await asyncio.sleep(0.02)
    await storage.close()
    for task in tasks:
        await task
