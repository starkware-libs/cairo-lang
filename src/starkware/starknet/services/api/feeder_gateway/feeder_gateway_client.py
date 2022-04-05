import json
from typing import Any, Dict, List, Optional, Union

from typing_extensions import Literal

from services.everest.api.feeder_gateway.feeder_gateway_client import EverestFeederGatewayClient
from starkware.starknet.definitions import fields
from starkware.starknet.services.api.feeder_gateway.response_objects import (
    StarknetBlock,
    TransactionInfo,
    TransactionReceipt,
    TransactionTrace,
)
from starkware.starknet.services.api.gateway.transaction import InvokeFunction
from starkware.starkware_utils.validated_fields import RangeValidatedField

CastableToHash = Union[int, str]
JsonObject = Dict[str, Any]
BlockIdentifier = Union[int, Literal["pending"]]


class FeederGatewayClient(EverestFeederGatewayClient):
    """
    A client class for the StarkNet FeederGateway.
    """

    async def get_contract_addresses(self) -> Dict[str, str]:
        raw_response = await self._send_request(send_method="GET", uri=f"/get_contract_addresses")
        return json.loads(raw_response)

    async def call_contract(
        self,
        invoke_tx: InvokeFunction,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> Dict[str, List[str]]:
        formatted_block_identifier = get_formatted_block_identifier(
            block_hash=block_hash, block_number=block_number
        )
        raw_response = await self._send_request(
            send_method="POST",
            uri=(f"/call_contract?{formatted_block_identifier}"),
            data=invoke_tx.dumps(),
        )
        return json.loads(raw_response)

    async def estimate_fee(
        self,
        invoke_tx: InvokeFunction,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> JsonObject:
        formatted_block_identifier = get_formatted_block_identifier(
            block_hash=block_hash, block_number=block_number
        )
        raw_response = await self._send_request(
            send_method="POST",
            uri=(f"/estimate_fee?{formatted_block_identifier}"),
            data=invoke_tx.dumps(),
        )
        return json.loads(raw_response)

    async def get_block(
        self,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> StarknetBlock:
        formatted_block_identifier = get_formatted_block_identifier(
            block_hash=block_hash, block_number=block_number
        )
        raw_response = await self._send_request(
            send_method="GET",
            uri=f"/get_block?{formatted_block_identifier}",
        )
        return StarknetBlock.loads(data=raw_response)

    async def get_state_update(
        self,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> JsonObject:
        formatted_block_identifier = get_formatted_block_identifier(
            block_hash=block_hash, block_number=block_number
        )
        raw_response = await self._send_request(
            send_method="GET",
            uri=f"/get_state_update?{formatted_block_identifier}",
        )
        return json.loads(raw_response)

    async def get_code(
        self,
        contract_address: int,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> List[str]:
        formatted_block_identifier = get_formatted_block_identifier(
            block_hash=block_hash, block_number=block_number
        )
        raw_response = await self._send_request(
            send_method="GET",
            uri=f"/get_code?contractAddress={hex(contract_address)}&{formatted_block_identifier}",
        )
        return json.loads(raw_response)

    async def get_full_contract(
        self,
        contract_address: int,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> JsonObject:
        """
        Returns the contract definition deployed under the given address.
        A plain JSON is returned, rather than the Python object, to save loading time.
        """
        formatted_block_identifier = get_formatted_block_identifier(
            block_hash=block_hash, block_number=block_number
        )
        uri = (
            f"/get_full_contract?contractAddress={hex(contract_address)}&"
            f"{formatted_block_identifier}"
        )
        raw_response = await self._send_request(send_method="GET", uri=uri)
        return json.loads(raw_response)

    async def get_storage_at(
        self,
        contract_address: int,
        key: int,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> str:
        formatted_block_identifier = get_formatted_block_identifier(
            block_hash=block_hash, block_number=block_number
        )
        uri = (
            f"/get_storage_at?contractAddress={hex(contract_address)}&key={key}&"
            f"{formatted_block_identifier}"
        )
        raw_response = await self._send_request(send_method="GET", uri=uri)
        return json.loads(raw_response)

    async def get_transaction_status(self, tx_hash: CastableToHash) -> JsonObject:
        raw_response = await self._send_request(
            send_method="GET",
            uri=f"/get_transaction_status?{tx_identifier(tx_hash=tx_hash)}",
        )
        return json.loads(raw_response)

    async def get_transaction(self, tx_hash: CastableToHash) -> TransactionInfo:
        raw_response = await self._send_request(
            send_method="GET", uri=f"/get_transaction?{tx_identifier(tx_hash=tx_hash)}"
        )
        return TransactionInfo.loads(data=raw_response)

    async def get_transaction_receipt(self, tx_hash: CastableToHash) -> TransactionReceipt:
        raw_response = await self._send_request(
            send_method="GET",
            uri=f"/get_transaction_receipt?{tx_identifier(tx_hash=tx_hash)}",
        )
        return TransactionReceipt.loads(data=raw_response)

    async def get_transaction_trace(self, tx_hash: CastableToHash) -> TransactionTrace:
        raw_response = await self._send_request(
            send_method="GET",
            uri=f"/get_transaction_trace?{tx_identifier(tx_hash=tx_hash)}",
        )
        return TransactionTrace.loads(data=raw_response)

    async def get_block_hash_by_id(self, block_id: int) -> str:
        raw_response = await self._send_request(
            send_method="GET",
            uri=f"/get_block_hash_by_id?blockId={block_id}",
        )
        return json.loads(raw_response)

    async def get_block_id_by_hash(self, block_hash: CastableToHash) -> int:
        raw_response = await self._send_request(
            send_method="GET",
            uri=(
                "/get_block_id_by_hash?"
                f"blockHash={format_hash(hash_value=block_hash, hash_field=fields.BlockHashField)}"
            ),
        )
        return json.loads(raw_response)

    async def get_transaction_hash_by_id(self, tx_id: int) -> str:
        raw_response = await self._send_request(
            send_method="GET",
            uri=f"/get_transaction_hash_by_id?transactionId={tx_id}",
        )
        return json.loads(raw_response)

    async def get_transaction_id_by_hash(self, tx_hash: CastableToHash) -> int:
        raw_response = await self._send_request(
            send_method="GET",
            uri=(
                "/get_transaction_id_by_hash?transactionHash="
                f"{format_hash(hash_value=tx_hash, hash_field=fields.TransactionHashField)}"
            ),
        )
        return json.loads(raw_response)


def format_hash(hash_value: CastableToHash, hash_field: RangeValidatedField) -> str:
    if isinstance(hash_value, int):
        return hash_field.format(hash_value)

    assert isinstance(hash_value, str)
    return hash_value


def tx_identifier(tx_hash: CastableToHash) -> str:
    hash_str = format_hash(hash_value=tx_hash, hash_field=fields.TransactionHashField)
    return f"transactionHash={hash_str}"


def get_formatted_block_identifier(
    block_hash: Optional[CastableToHash], block_number: Optional[BlockIdentifier]
) -> str:
    if block_hash is None:
        block_number_str = (
            block_number if isinstance(block_number, str) else json.dumps(block_number)
        )
        return f"blockNumber={block_number_str}"
    else:
        return f"blockHash={format_hash(hash_value=block_hash, hash_field=fields.BlockHashField)}"
