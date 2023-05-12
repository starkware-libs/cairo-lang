import json
from typing import ClassVar

from services.external_api.client import BaseRestClient


class EverestFeederGatewayClient(BaseRestClient):
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

    async def get_previous_batch_id(self, batch_id: int) -> int:
        raw_response = await self._send_request(
            send_method="GET", uri=f"/get_prev_batch_id?batch_id={batch_id}"
        )
        return json.loads(raw_response)
