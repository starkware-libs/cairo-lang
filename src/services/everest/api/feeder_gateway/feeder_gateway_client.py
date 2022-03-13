import json
from typing import ClassVar

from services.external_api.base_client import BaseClient


class EverestFeederGatewayClient(BaseClient):
    """
    Base class to FeederGatewayClient classes.
    """

    prefix: ClassVar[str] = "/feeder_gateway"

    async def get_last_batch_id(self) -> int:
        raw_response = await self._send_request(send_method="GET", uri="/get_last_batch_id")
        return json.loads(raw_response)

    async def get_l1_blockchain_id(self) -> int:
        raw_response = await self._send_request(send_method="GET", uri="/get_l1_blockchain_id")
        return json.loads(raw_response)
