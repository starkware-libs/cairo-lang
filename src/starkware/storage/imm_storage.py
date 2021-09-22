import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

from starkware.storage.storage import Storage


class _ImmediateStorage(Storage):
    def __init__(self, storage: Storage, avoid_write_through: bool):
        self.storage = storage
        self.write_tasks: List[asyncio.Task] = []
        self.db: Dict[bytes, bytes] = {}
        self.avoid_write_through = avoid_write_through

    async def set_value(self, key: bytes, value: bytes):
        assert isinstance(key, bytes), f"key must be bytes. Got {type(key)}."
        self.db[key] = value

        if not self.avoid_write_through:
            self.write_tasks.append(asyncio.create_task(self.storage.set_value(key, value)))

    async def get_value(self, key: bytes) -> Optional[bytes]:
        assert isinstance(key, bytes), f"key must be bytes. Got {type(key)}."
        if key in self.db:
            return self.db[key]
        res = await self.storage.get_value(key)
        if res is not None:
            self.db[key] = res
        return res

    async def del_value(self, key: bytes):
        assert isinstance(key, bytes), f"key must be bytes. Got {type(key)}."
        if key in self.db:
            del self.db[key]

        if not self.avoid_write_through:
            self.write_tasks.append(asyncio.create_task(self.storage.del_value(key)))

    async def wait_for_all(self):
        for task in self.write_tasks:
            await task


@asynccontextmanager
async def immediate_storage(storage: Storage, avoid_write_through: bool = False):
    try:
        res = _ImmediateStorage(storage=storage, avoid_write_through=avoid_write_through)
        yield res
    finally:
        await res.wait_for_all()
