import json
from typing import Any, Dict, List, Optional

from services.everest.api.feeder_gateway.feeder_gateway_client import EverestFeederGatewayClient
from starkware.starknet.services.api.gateway.transaction import InvokeFunction


class FeederGatewayClient(EverestFeederGatewayClient):
    """
    A client class for the StarkNet FeederGateway.
    """

    async def call_contract(
            self, invoke_tx: InvokeFunction,
            block_id: Optional[int] = None) -> Dict[str, List[int]]:
        raw_response = await self._send_request(
            send_method='POST',
            uri=f'/call_contract?blockId={json.dumps(block_id)}', data=invoke_tx.dumps())
        return json.loads(raw_response)

    async def get_block(self, block_id: Optional[int] = None) -> Dict[str, Any]:
        raw_response = await self._send_request(
            send_method='GET', uri=f'/get_block?blockId={json.dumps(block_id)}')
        return json.loads(raw_response)

    async def get_code(self, contract_address: int, block_id: Optional[int] = None) -> List[int]:
        uri = f'/get_code?contractAddress={hex(contract_address)}&blockId={json.dumps(block_id)}'
        raw_response = await self._send_request(send_method='GET', uri=uri)
        return json.loads(raw_response)

    async def get_storage_at(
            self, contract_address: int, key: int, block_id: Optional[int] = None) -> int:
        uri = (
            f'/get_storage_at?contractAddress={hex(contract_address)}&key={key}&'
            f'blockId={json.dumps(block_id)}')
        raw_response = await self._send_request(send_method='GET', uri=uri)
        return json.loads(raw_response)

    async def get_transaction_status(self, tx_id: int) -> str:
        raw_response = await self._send_request(
            send_method='GET', uri=f'/get_transaction_status?transactionId={tx_id}')
        return json.loads(raw_response)
