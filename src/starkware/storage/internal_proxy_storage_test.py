import asyncio
import logging

import pytest

from starkware.storage.internal_proxy_storage import InternalProxyStorage

logger = logging.getLogger(__name__)


class MockInternalClient:
    async def get_value(self, key):
        return str(key) + '_result'


@pytest.mark.asyncio
async def test_internal_proxy_storage():
    storage = InternalProxyStorage(internal_client=MockInternalClient())

    async def get_value(val_id):
        assert await storage.get_value(f'key{val_id}') == f'key{val_id}_result'

    tasks = [asyncio.create_task(get_value(i)) for i in range(4)]
    await asyncio.sleep(0.02)
    for task in tasks:
        await task

    # Make sure deletions don't work.
    with pytest.raises(NotImplementedError):
        await storage.del_value(1)

    # Make sure value setting doesn't work.
    with pytest.raises(NotImplementedError):
        await storage.set_value(1, 2)
