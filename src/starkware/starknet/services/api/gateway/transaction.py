import base64
import gzip
import json
from abc import abstractmethod
from dataclasses import field
from typing import Any, ClassVar, Dict, List, Type

import marshmallow
import marshmallow.decorators
import marshmallow_dataclass
from marshmallow_oneofschema import OneOfSchema

from services.everest.api.gateway.transaction import EverestTransaction
from starkware.starknet.core.os.transaction_hash.transaction_hash import (
    TransactionHashPrefix,
    calculate_deploy_transaction_hash,
    calculate_transaction_hash_common,
)
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.services.api.gateway.contract_address import calculate_contract_address
from starkware.starkware_utils.error_handling import wrap_with_stark_exception


class Transaction(EverestTransaction):
    """
    StarkNet transaction base class.
    """

    @property
    @classmethod
    @abstractmethod
    def tx_type(cls) -> TransactionType:
        """
        Returns the corresponding TransactionType enum. Used in TransacactionSchema.
        Subclasses should define it as a class variable.
        """

    @abstractmethod
    def calculate_hash(self, general_config: StarknetGeneralConfig) -> int:
        """
        Calculates the transaction hash in the StarkNet network - a unique identifier of the
        transaction. See calculate_transaction_hash_common() docstring for more details.
        """


@marshmallow_dataclass.dataclass(frozen=True)
class Deploy(Transaction):
    """
    Represents a transaction in the StarkNet network that is a deployment of a StarkNet contract.
    """

    contract_address_salt: int = field(metadata=fields.contract_address_salt_metadata)
    contract_definition: ContractDefinition
    constructor_calldata: List[int] = field(metadata=fields.call_data_metadata)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.DEPLOY

    @staticmethod
    def compress_program(program_json: dict):
        full_program = json.dumps(program_json)
        compressed_program = gzip.compress(data=full_program.encode("ascii"))
        compressed_program = base64.b64encode(compressed_program)
        return compressed_program.decode("ascii")

    @marshmallow.decorators.post_dump
    def compress_program_post_dump(
        self, data: Dict[str, Any], many: bool, **kwargs
    ) -> Dict[str, Any]:
        data["contract_definition"]["program"] = Deploy.compress_program(
            program_json=data["contract_definition"]["program"]
        )
        return data

    @marshmallow.decorators.pre_load
    def decompress_program(self, data: Dict[str, Any], many: bool, **kwargs) -> Dict[str, Any]:
        compressed_program: str = data["contract_definition"]["program"]

        with wrap_with_stark_exception(
            code=StarknetErrorCode.INVALID_PROGRAM,
            message="Invalid compressed program.",
            exception_types=[Exception],
        ):
            compressed_program_bytes = base64.b64decode(compressed_program.encode("ascii"))
            decompressed_program = gzip.decompress(data=compressed_program_bytes)
            data["contract_definition"]["program"] = json.loads(
                decompressed_program.decode("ascii")
            )

        return data

    def calculate_hash(self, general_config: StarknetGeneralConfig) -> int:
        """
        Calculates the transaction hash in the StarkNet network.
        """
        contract_address = calculate_contract_address(
            salt=self.contract_address_salt,
            contract_definition=self.contract_definition,
            constructor_calldata=self.constructor_calldata,
            caller_address=0,
        )
        return calculate_deploy_transaction_hash(
            contract_address=contract_address,
            constructor_calldata=self.constructor_calldata,
            chain_id=general_config.chain_id.value,
        )


@marshmallow_dataclass.dataclass(frozen=True)
class InvokeFunction(Transaction):
    """
    Represents a transaction in the StarkNet network that is an invocation of a Cairo contract
    function.
    """

    contract_address: int = field(metadata=fields.contract_address_metadata)
    # A field element that encodes the signature of the invoked function.
    entry_point_selector: int = field(metadata=fields.entry_point_selector_metadata)
    calldata: List[int] = field(metadata=fields.call_data_metadata)
    # The maximal fee to be paid in Wei for executing invoked function.
    max_fee: int = field(metadata=fields.fee_metadata)
    # The transaction is not valid if its version is lower than current version,
    # defined by the SN OS.
    version: int = field(metadata=fields.tx_version_metadata)
    # Additional information given by the caller that represents the signature of the transaction.
    # The exact way this field is handled is defined by the called contract's function, like
    # calldata.
    signature: List[int] = field(metadata=fields.signature_metadata)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.INVOKE_FUNCTION

    def calculate_hash(self, general_config: StarknetGeneralConfig) -> int:
        """
        Calculates the transaction hash in the StarkNet network.
        """
        return calculate_transaction_hash_common(
            tx_hash_prefix=TransactionHashPrefix.INVOKE,
            version=self.version,
            contract_address=self.contract_address,
            entry_point_selector=self.entry_point_selector,
            calldata=self.calldata,
            max_fee=self.max_fee,
            chain_id=general_config.chain_id.value,
            additional_data=[],
        )


class TransactionSchema(OneOfSchema):
    """
    Schema for transaction.
    OneOfSchema adds a "type" field.

    Allows the use of load/dump of different transaction type data directly via the
    Transaction class (e.g., Transaction.load(invoke_function_dict), where
    {"type": "INVOKE_FUNCTION"} is in invoke_function_dict, will produce an InvokeFunction object).
    """

    type_schemas: Dict[str, Type[marshmallow.Schema]] = {
        TransactionType.DEPLOY.name: Deploy.Schema,
        TransactionType.INVOKE_FUNCTION.name: InvokeFunction.Schema,
    }

    def get_obj_type(self, obj: Transaction) -> str:
        return obj.tx_type.name


Transaction.Schema = TransactionSchema
