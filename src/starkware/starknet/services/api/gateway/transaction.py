import dataclasses
from abc import abstractmethod
from dataclasses import field
from typing import Any, ClassVar, Dict, List, Optional, Type

import marshmallow
import marshmallow.decorators
import marshmallow_dataclass
from marshmallow_oneofschema import OneOfSchema

from services.everest.api.gateway.transaction import EverestTransaction
from starkware.starknet.core.os.contract_address.contract_address import (
    calculate_contract_address,
    calculate_contract_address_from_hash,
)
from starkware.starknet.core.os.transaction_hash.transaction_hash import (
    TransactionHashPrefix,
    calculate_declare_transaction_hash,
    calculate_deploy_account_transaction_hash,
    calculate_deploy_transaction_hash,
    calculate_transaction_hash_common,
)
from starkware.starknet.definitions import constants, fields
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.services.api.gateway.transaction_utils import (
    compress_program,
    compress_program_post_dump,
    decompress_program,
)

# The sender address used by default in declare transactions of version 0.
DEFAULT_DECLARE_SENDER_ADDRESS = 1


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@dataclasses.dataclass(frozen=True)  # type: ignore[misc]
class Transaction(EverestTransaction):
    """
    StarkNet transaction base class.
    """

    # The version of the transaction. It is fixed (currently, 1) in the OS, and should be
    # signed by the account contract.
    # This field allows invalidating old transactions, whenever the meaning of the other
    # transaction fields is changed (in the OS).
    version: int = field(metadata=fields.non_required_tx_version_metadata)

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


# Mypy has a problem with dataclasses that contain unimplemented abstract methods.
# See https://github.com/python/mypy/issues/5374 for details on this problem.
@dataclasses.dataclass(frozen=True)  # type: ignore[misc]
class AccountTransaction(Transaction):
    """
    Represents a transaction in the StarkNet network that is originated from an action of an
    account.
    """

    # The maximal fee to be paid in Wei for executing the transaction.
    max_fee: int = field(metadata=fields.fee_metadata)
    # The signature of the transaction.
    # The exact way this field is handled is defined by the called contract's function,
    # similar to calldata.
    signature: List[int] = field(metadata=fields.signature_metadata)
    # The nonce of the transaction.
    # A sequential number attached to the account contract, that prevents transaction replay
    # and guarantees the order of execution and uniqueness of the transaction hash.
    nonce: Optional[int] = field(metadata=fields.optional_nonce_metadata)


@marshmallow_dataclass.dataclass(frozen=True)
class Declare(AccountTransaction):
    """
    Represents a transaction in the StarkNet network that is a declaration of a StarkNet contract
    class.
    """

    contract_class: ContractClass
    # The address of the account contract sending the declaration transaction.
    sender_address: int = field(metadata=fields.contract_address_metadata)
    # Repeat `nonce` to narrow its type to non-optional int.
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
            nonce=self.nonce,
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
        """
        Deprecated.
        Use starkware.starknet.services.api.gateway.transaction_utils.compress_program instead.
        """
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
class DeployAccount(AccountTransaction):
    """
    Represents a transaction in the StarkNet network that is a deployment of a StarkNet account
    contract.
    """

    class_hash: int = field(metadata=fields.ClassHashIntField.metadata())
    contract_address_salt: int = field(metadata=fields.contract_address_salt_metadata)
    constructor_calldata: List[int] = field(metadata=fields.call_data_metadata)
    version: int = field(metadata=fields.tx_version_metadata)
    # Repeat `nonce` to narrow its type to non-optional int.
    nonce: int = field(metadata=fields.nonce_metadata)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.DEPLOY_ACCOUNT

    def calculate_hash(self, general_config: StarknetGeneralConfig) -> int:
        """
        Calculates the transaction hash in the StarkNet network.
        """
        contract_address = calculate_contract_address_from_hash(
            salt=self.contract_address_salt,
            class_hash=self.class_hash,
            constructor_calldata=self.constructor_calldata,
            deployer_address=0,
        )
        return calculate_deploy_account_transaction_hash(
            version=self.version,
            contract_address=contract_address,
            class_hash=self.class_hash,
            constructor_calldata=self.constructor_calldata,
            max_fee=self.max_fee,
            nonce=self.nonce,
            salt=self.contract_address_salt,
            chain_id=general_config.chain_id.value,
        )


@marshmallow_dataclass.dataclass(frozen=True)
class InvokeFunction(AccountTransaction):
    """
    Represents a transaction in the StarkNet network that is an invocation of a Cairo contract
    function.
    """

    contract_address: int = field(metadata=fields.contract_address_metadata)
    calldata: List[int] = field(metadata=fields.call_data_metadata)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.INVOKE_FUNCTION

    # A field element that encodes the signature of the invoked function.
    # The entry_point_selector is deprecated for version 1 and above (transactions
    # should go through the '__execute__' entry point).
    entry_point_selector: Optional[int] = field(
        default=None, metadata=fields.optional_entry_point_selector_metadata
    )

    @marshmallow.decorators.post_dump
    def remove_entry_point_selector(
        self, data: Dict[str, Any], many: bool, **kwargs
    ) -> Dict[str, Any]:
        version = fields.TransactionVersionField.load_value(data["version"])
        if version in (0, constants.QUERY_VERSION_BASE):
            return data

        assert (
            data["entry_point_selector"] is None
        ), f"entry_point_selector should be None in version {version}."
        del data["entry_point_selector"]

        return data

    def calculate_hash(self, general_config: StarknetGeneralConfig) -> int:
        """
        Calculates the transaction hash in the StarkNet network.
        """
        if self.version in [0, constants.QUERY_VERSION_BASE]:
            assert (
                self.nonce is None
            ), f"nonce is not None ({self.nonce}) for version={self.version}."
            additional_data = []
            assert (
                self.entry_point_selector is not None
            ), f"entry_point_selector is None for version={self.version}."
            entry_point_selector_field = self.entry_point_selector
        else:
            assert self.nonce is not None, f"nonce is None for version={self.version}."
            additional_data = [self.nonce]
            assert (
                self.entry_point_selector is None
            ), f"entry_point_selector is deprecated in version={self.version}."
            entry_point_selector_field = 0

        return calculate_transaction_hash_common(
            tx_hash_prefix=TransactionHashPrefix.INVOKE,
            version=self.version,
            contract_address=self.contract_address,
            entry_point_selector=entry_point_selector_field,
            calldata=self.calldata,
            max_fee=self.max_fee,
            chain_id=general_config.chain_id.value,
            additional_data=additional_data,
        )


class AccountTransactionSchema(OneOfSchema):
    """
    Schema for account transaction.
    OneOfSchema adds a "type" field.
    """

    type_schemas: Dict[str, Type[marshmallow.Schema]] = {
        TransactionType.DECLARE.name: Declare.Schema,
        TransactionType.DEPLOY_ACCOUNT.name: DeployAccount.Schema,
        TransactionType.INVOKE_FUNCTION.name: InvokeFunction.Schema,
    }

    def get_obj_type(self, obj: AccountTransaction) -> str:
        return obj.tx_type.name


AccountTransaction.Schema = AccountTransactionSchema


class TransactionSchema(OneOfSchema):
    """
    Schema for transaction.
    OneOfSchema adds a "type" field.

    Allows the use of load/dump of different transaction type data directly via the
    Transaction class (e.g., Transaction.load(invoke_function_dict), where
    {"type": "INVOKE_FUNCTION"} is in invoke_function_dict, will produce an InvokeFunction object).
    """

    type_schemas: Dict[str, Type[marshmallow.Schema]] = {
        **AccountTransactionSchema.type_schemas,
        TransactionType.DEPLOY.name: Deploy.Schema,
    }

    def get_obj_type(self, obj: Transaction) -> str:
        return obj.tx_type.name


Transaction.Schema = TransactionSchema
