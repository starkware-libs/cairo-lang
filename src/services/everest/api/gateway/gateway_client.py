import json
from typing import ClassVar, Dict

from services.everest.api.gateway.transaction import EverestAddTransactionRequest
from services.external_api.base_client import BaseClient


class EverestGatewayClient(BaseClient):
    """
    Base class to GatewayClient classes.
    """

    prefix: ClassVar[str] = '/gateway'

    async def is_alive(self) -> str:
        return await self._send_request(send_method='GET', uri='/is_alive')

    async def add_transaction_request(
            self, add_tx_request: EverestAddTransactionRequest) -> Dict[str, str]:
        raw_response = await self._send_request(
            send_method='POST', uri='/add_transaction', data=add_tx_request.dumps())
        return json.loads(raw_response)

    async def get_first_unused_tx_id(self) -> int:
        response = await self._send_request(send_method='GET', uri='/get_first_unused_tx_id')
        return json.loads(response)
