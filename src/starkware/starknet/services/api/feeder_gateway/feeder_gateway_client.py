import json
from typing import Dict, List, Optional, Union

from services.everest.api.feeder_gateway.feeder_gateway_client import EverestFeederGatewayClient
from services.external_api.client import JsonObject
from starkware.starknet.definitions import fields
from starkware.starknet.services.api.feeder_gateway.request_objects import (
    CallFunction,
    CallL1Handler,
)
from starkware.starknet.services.api.feeder_gateway.response_objects import (
    BlockIdentifier,
    BlockTransactionTraces,
    FeeEstimationInfo,
    StarknetBlock,
    TransactionInfo,
    TransactionReceipt,
    TransactionSimulationInfo,
    TransactionTrace,
)
from starkware.starknet.services.api.gateway.transaction import AccountTransaction
from starkware.starkware_utils.validated_fields import RangeValidatedField

CastableToHash = Union[int, str]


class FeederGatewayClient(EverestFeederGatewayClient):
    """
    A client class for the StarkNet FeederGateway.
    """

    async def get_contract_addresses(self) -> Dict[str, str]:
        raw_response = await self._send_request(send_method="GET", uri=f"/get_contract_addresses")
        return json.loads(raw_response)

    async def call_contract(
        self,
        call_function: CallFunction,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> Dict[str, List[str]]:
        formatted_block_named_argument = get_formatted_block_named_argument(
            block_hash=block_hash, block_number=block_number
        )
        raw_response = await self._send_request(
            send_method="POST",
            uri=f"/call_contract?{formatted_block_named_argument}",
            data=call_function.dumps(),
        )
        return json.loads(raw_response)

    async def estimate_fee(
        self,
        tx: AccountTransaction,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> FeeEstimationInfo:
        formatted_block_named_argument = get_formatted_block_named_argument(
            block_hash=block_hash, block_number=block_number
        )
        raw_response = await self._send_request(
            send_method="POST",
            uri=f"/estimate_fee?{formatted_block_named_argument}",
            data=AccountTransaction.Schema().dumps(obj=tx),
        )
        return FeeEstimationInfo.loads(data=raw_response)

    async def estimate_message_fee(
        self,
        call_l1_handler: CallL1Handler,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> FeeEstimationInfo:
        formatted_block_named_argument = get_formatted_block_named_argument(
            block_hash=block_hash, block_number=block_number
        )
        raw_response = await self._send_request(
            send_method="POST",
            uri=f"/estimate_message_fee?{formatted_block_named_argument}",
            data=call_l1_handler.dumps(),
        )
        return FeeEstimationInfo.loads(data=raw_response)

    async def simulate_transaction(
        self,
        tx: AccountTransaction,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> TransactionSimulationInfo:
        formatted_block_named_argument = get_formatted_block_named_argument(
            block_hash=block_hash, block_number=block_number
        )
        raw_response = await self._send_request(
            send_method="POST",
            uri=f"/simulate_transaction?{formatted_block_named_argument}",
            data=AccountTransaction.Schema().dumps(obj=tx),
        )
        return TransactionSimulationInfo.loads(data=raw_response)

    async def get_block(
        self,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> StarknetBlock:
        formatted_block_named_argument = get_formatted_block_named_argument(
            block_hash=block_hash, block_number=block_number
        )
        raw_response = await self._send_request(
            send_method="GET",
            uri=f"/get_block?{formatted_block_named_argument}",
        )
        return StarknetBlock.loads(data=raw_response)

    async def get_block_traces(
        self,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> BlockTransactionTraces:
        formatted_block_named_argument = get_formatted_block_named_argument(
            block_hash=block_hash, block_number=block_number
        )
        raw_response = await self._send_request(
            send_method="GET",
            uri=f"/get_block_traces?{formatted_block_named_argument}",
        )
        return BlockTransactionTraces.loads(data=raw_response)

    async def get_state_update(
        self,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> JsonObject:
        formatted_block_named_argument = get_formatted_block_named_argument(
            block_hash=block_hash, block_number=block_number
        )
        raw_response = await self._send_request(
            send_method="GET",
            uri=f"/get_state_update?{formatted_block_named_argument}",
        )
        return json.loads(raw_response)

    async def get_code(
        self,
        contract_address: int,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> List[str]:
        formatted_block_named_argument = get_formatted_block_named_argument(
            block_hash=block_hash, block_number=block_number
        )
        contract_address_str = fields.L2AddressField.format(contract_address)
        raw_response = await self._send_request(
            send_method="GET",
            uri=f"/get_code?contractAddress={contract_address_str}&"
            f"{formatted_block_named_argument}",
        )
        return json.loads(raw_response)

    async def get_full_contract(
        self,
        contract_address: int,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> JsonObject:
        """
        Returns the contract class deployed under the given address.
        A plain JSON is returned, rather than the Python object, to save loading time.
        """
        formatted_block_named_argument = get_formatted_block_named_argument(
            block_hash=block_hash, block_number=block_number
        )
        contract_address_str = fields.L2AddressField.format(contract_address)
        uri = (
            f"/get_full_contract?contractAddress={contract_address_str}&"
            f"{formatted_block_named_argument}"
        )
        raw_response = await self._send_request(send_method="GET", uri=uri)
        return json.loads(raw_response)

    async def get_class_hash_at(
        self,
        contract_address: int,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> str:
        """
        Returns the class hash deployed under the given address.
        """
        formatted_block_named_argument = get_formatted_block_named_argument(
            block_hash=block_hash, block_number=block_number
        )
        uri = (
            f"/get_class_hash_at?contractAddress={fields.L2AddressField.format(contract_address)}&"
            f"{formatted_block_named_argument}"
        )
        raw_response = await self._send_request(send_method="GET", uri=uri)
        return json.loads(raw_response)

    async def get_class_by_hash(self, class_hash: str) -> JsonObject:
        """
        Returns the contract class deployed under the given class hash.
        A plain JSON is returned, rather than the Python object, to save loading time.
        """
        uri = f"/get_class_by_hash?classHash={class_hash}"
        raw_response = await self._send_request(send_method="GET", uri=uri)
        return json.loads(raw_response)

    async def get_storage_at(
        self,
        contract_address: int,
        key: int,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> str:
        formatted_block_named_argument = get_formatted_block_named_argument(
            block_hash=block_hash, block_number=block_number
        )
        contract_address_str = fields.L2AddressField.format(contract_address)
        uri = (
            f"/get_storage_at?contractAddress={contract_address_str}&"
            f"key={key}&{formatted_block_named_argument}"
        )
        raw_response = await self._send_request(send_method="GET", uri=uri)
        return json.loads(raw_response)

    async def get_nonce(
        self,
        contract_address: int,
        block_hash: Optional[CastableToHash] = None,
        block_number: Optional[BlockIdentifier] = None,
    ) -> int:
        formatted_block_identifier = get_formatted_block_named_argument(
            block_hash=block_hash, block_number=block_number
        )
        contract_address_str = fields.L2AddressField.format(contract_address)
        uri = f"/get_nonce?contractAddress={contract_address_str}&{formatted_block_identifier}"
        raw_response = await self._send_request(send_method="GET", uri=uri)
        return int(json.loads(raw_response), 16)

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


def get_formatted_block_named_argument(
    block_hash: Optional[CastableToHash], block_number: Optional[BlockIdentifier]
) -> str:
    if block_hash is None:
        block_number_str = (
            block_number if isinstance(block_number, str) else json.dumps(block_number)
        )
        return f"blockNumber={block_number_str}"
    else:
        return f"blockHash={format_hash(hash_value=block_hash, hash_field=fields.BlockHashField)}"
