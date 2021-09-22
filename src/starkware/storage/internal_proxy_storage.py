from starkware.storage.storage import Storage


class InternalProxyStorage(Storage):
    """
    Local storage that communicates with an internal client.
    """

    def __init__(self, internal_client):
        self.internal_client = internal_client

    async def set_value(self, key, value):
        raise NotImplementedError("Cannot set storage values in this version.")

    async def del_value(self, key):
        raise NotImplementedError("Cannot delete storage values in this version.")

    async def get_value(self, key):
        return await self.internal_client.get_value(key)
