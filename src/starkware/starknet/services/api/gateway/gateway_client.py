import json
from typing import Dict

from services.everest.api.gateway.gateway_client import EverestGatewayClient
from starkware.starknet.services.api.gateway.transaction import Transaction


class GatewayClient(EverestGatewayClient):
    """
    A client class for the StarkNet Gateway.
    """
    async def add_transaction(self, tx: Transaction) -> Dict[str, int]:
        raw_response = await self._send_request(
            send_method='POST', uri='/add_transaction', data=Transaction.Schema().dumps(obj=tx))
        return json.loads(raw_response)
