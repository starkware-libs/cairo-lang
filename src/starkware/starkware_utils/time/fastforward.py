import asyncio
from selectors import DefaultSelector


class FFSelector(DefaultSelector):
    def __init__(self, start_time, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_time = start_time

    def select(self, timeout):
        # There are tasks to be scheduled. Continue simulating.
        if timeout is None:
            # If timeout is infinity, just wait without increasing _current_time.
            return DefaultSelector.select(self, timeout)
        self._current_time += timeout
        return DefaultSelector.select(self, 0)


class FFEventLoop(asyncio.SelectorEventLoop):  # type: ignore
    def __init__(self, start_time: int = 0):
        super().__init__(selector=FFSelector(start_time=start_time))

    def time(self):
        return self._selector._current_time
