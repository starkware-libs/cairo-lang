import asyncio
import logging
from asyncio import Queue
from typing import Optional, Tuple

from starkware.storage.storage import Storage

logger = logging.getLogger(__name__)
NoneType = type(None)


class BatchStore(Storage):
    def __init__(self, storage: Storage, n_workers_set: int, n_workers_get: int):
        self.store = storage
        self.set_queue: Queue[Tuple[bytes, bytes, asyncio.Future]] = Queue()
        self.get_queue: Queue[Tuple[bytes, asyncio.Future]] = Queue()
        self.tasks = [asyncio.create_task(self.set_value_thread()) for _ in range(n_workers_set)]
        self.tasks += [asyncio.create_task(self.get_value_thread()) for _ in range(n_workers_get)]

    async def close(self):
        for task in self.tasks:
            task.cancel()
            try:
                await task
            except Exception as ex:
                if not isinstance(ex, asyncio.CancelledError):
                    logger.error(f"Excpetion occurred! Exception: {ex}")
                    logger.debug("Exception details", exc_info=True)

    async def set_value(self, key: bytes, value: bytes):
        # Put value in the set_queue.
        future: asyncio.Future[NoneType] = asyncio.Future()
        await self.set_queue.put((key, value, future))
        await future

    async def get_value(self, key: bytes) -> Optional[bytes]:
        # Put value in the get_queue.
        future: asyncio.Future[Optional[bytes]] = asyncio.Future()
        await self.get_queue.put((key, future))
        return await future

    async def del_value(self, key: bytes):
        await self.store.del_value(key)

    async def get_queue_items(self, queue):
        queue_items = []
        if queue.empty():
            # Empty queue, await next item.
            queue_items.append(await queue.get())
        for _ in range(queue.qsize()):
            # Since no await occurs in this loop, this is safe.
            queue_items.append(queue.get_nowait())
        return queue_items

    async def set_value_thread(self):
        """
        Implements the thread that retrieves set-commands from 'set_queue' and processes them
        in batch (using 'mset').
        """
        while True:
            queue_items = await self.get_queue_items(self.set_queue)
            futures_list = [future for _, _, future in queue_items]
            await self.store.mset({key: val for key, val, _ in queue_items})
            for item in futures_list:
                item.set_result(None)

    async def get_value_thread(self):
        """
        Implements the thread that retrieves get-commands from 'get_queue' and processes them
        in batch (using 'mget').
        """
        while True:
            queue_items = await self.get_queue_items(self.get_queue)
            futures_list = [future for _, future in queue_items]
            res = await self.store.mget([key for key, _ in queue_items])
            for i, item in enumerate(futures_list):
                item.set_result(res[i])
