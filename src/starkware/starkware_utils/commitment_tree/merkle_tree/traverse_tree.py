import asyncio
from typing import AsyncIterator, Callable, Optional, TypeVar

NodeType = TypeVar("NodeType")


async def traverse_tree(
    get_children_callback: Callable[[NodeType], AsyncIterator[NodeType]],
    root: NodeType,
    n_workers: Optional[int] = None,
):
    """
    Traverses a tree as follows:
    1. Starts by calling get_children_callback(root). This function should return the children of
    root in the tree that you want to visit.
    2. Call get_children_callback() on each of the children to get more nodes, and repeat.

    The order of execution is not guaranteed, except that it is more similar to DFS than BFS in
    terms of memory consumption.
    """
    if n_workers is None:
        n_workers = 128

    # Keep the visited nodes in a priority queue so that children will be prioritized over their
    # parents. This keeps the behavior similar to DFS rather than BFS (e.g., with one worker this
    # is exactly DFS).
    queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
    await queue.put((0, root))

    async def worker_func():
        while True:
            height, node = await queue.get()
            try:
                async for child in get_children_callback(node):
                    await queue.put((height - 1, child))
            finally:
                queue.task_done()

    # Run several workers to process the nodes.
    workers = asyncio.gather(*(worker_func() for _ in range(n_workers)))

    await queue.join()

    workers.cancel()
    try:
        await workers
    except asyncio.CancelledError:
        pass

    assert queue.empty()
