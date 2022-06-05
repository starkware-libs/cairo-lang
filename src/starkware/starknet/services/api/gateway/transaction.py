from abc import abstractmethod
from dataclasses import field
from typing import Any, ClassVar, Dict, List, Type

import marshmallow
import marshmallow.decorators
import marshmallow_dataclass
from marshmallow_oneofschema import OneOfSchema

from services.everest.api.gateway.transaction import EverestTransaction
from starkware.starknet.core.os.contract_address.contract_address import calculate_contract_address
from starkware.starknet.core.os.transaction_hash.transaction_hash import (
    TransactionHashPrefix,
    calculate_declare_transaction_hash,
    calculate_deploy_transaction_hash,
    calculate_transaction_hash_common,
)
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.services.api.gateway.transaction_utils import (
    compress_program,
    compress_program_post_dump,
    decompress_program,
)

DECLARE_SENDER_ADDRESS = 1


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@marshmallow_dataclass.dataclass(frozen=True)  # type: ignore[misc]
class Transaction(EverestTransaction):
    """
    StarkNet transaction base class.
    """

    # The version of the transaction. It is fixed (currently, 0) in the OS, and should be
    # signed by the account contract.
    # This field allows invalidating old transactions, whenever the meaning of the other
    # transaction fields is changed (in the OS).
    version: int = field(metadata=fields.tx_version_metadata)

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
class Declare(Transaction):
    """
    Represents a transaction in the StarkNet network that is a declaration of a StarkNet contract
    class.
    """

    contract_class: ContractClass
    # The address of the account contract sending the declaration transaction.
    sender_address: int = field(metadata=fields.contract_address_metadata)
    # The maximal fee to be paid in Wei for declaring a contract class.
    max_fee: int = field(metadata=fields.fee_metadata)
    # Additional information given by the caller that represents the signature of the transaction.
    signature: List[int] = field(metadata=fields.signature_metadata)
    # A sequential integer used to distinguish between transactions and order them.
    nonce: int = field(metadata=fields.nonce_metadata)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.DECLARE

    @staticmethod
    def compress_program(program_json: dict):
        return compress_program(program_json=program_json)

    @marshmallow.decorators.post_dump
    def compress_program_post_dump(
        self, data: Dict[str, Any], many: bool, **kwargs
    ) -> Dict[str, Any]:
        return compress_program_post_dump(data=data, many=many)

    @marshmallow.decorators.pre_load
    def decompress_program(self, data: Dict[str, Any], many: bool, **kwargs) -> Dict[str, Any]:
        return decompress_program(data=data, many=many)

    def calculate_hash(self, general_config: StarknetGeneralConfig) -> int:
        """
        Calculates the transaction hash in the StarkNet network.
        """
        return calculate_declare_transaction_hash(
            contract_class=self.contract_class,
            chain_id=general_config.chain_id.value,
            sender_address=self.sender_address,
            max_fee=self.max_fee,
            version=self.version,
        )


@marshmallow_dataclass.dataclass(frozen=True)
class Deploy(Transaction):
    """
    Represents a transaction in the StarkNet network that is a deployment of a StarkNet contract.
    """

    contract_address_salt: int = field(metadata=fields.contract_address_salt_metadata)
    contract_definition: ContractClass
    constructor_calldata: List[int] = field(metadata=fields.call_data_metadata)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.DEPLOY

    @staticmethod
    def compress_program(program_json: dict):
        return compress_program(program_json=program_json)

    @marshmallow.decorators.post_dump
    def compress_program_post_dump(
        self, data: Dict[str, Any], many: bool, **kwargs
    ) -> Dict[str, Any]:
        return compress_program_post_dump(data=data, many=many)

    @marshmallow.decorators.pre_load
    def decompress_program(self, data: Dict[str, Any], many: bool, **kwargs) -> Dict[str, Any]:
        return decompress_program(data=data, many=many)

    def calculate_hash(self, general_config: StarknetGeneralConfig) -> int:
        """
        Calculates the transaction hash in the StarkNet network.
        """
        contract_address = calculate_contract_address(
            salt=self.contract_address_salt,
            contract_class=self.contract_definition,
            constructor_calldata=self.constructor_calldata,
            deployer_address=0,
        )
        return calculate_deploy_transaction_hash(
            contract_address=contract_address,
            constructor_calldata=self.constructor_calldata,
            chain_id=general_config.chain_id.value,
            version=self.version,
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
        TransactionType.DECLARE.name: Declare.Schema,
        TransactionType.DEPLOY.name: Deploy.Schema,
        TransactionType.INVOKE_FUNCTION.name: InvokeFunction.Schema,
    }

    def get_obj_type(self, obj: Transaction) -> str:
        return obj.tx_type.name


Transaction.Schema = TransactionSchema
