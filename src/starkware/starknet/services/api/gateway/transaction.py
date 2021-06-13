import base64
import dataclasses
import gzip
import json
from abc import abstractmethod
from dataclasses import field
from typing import Any, ClassVar, Dict, List, Type

import marshmallow
import marshmallow.decorators
import marshmallow_dataclass
from marshmallow_oneofschema import OneOfSchema

from services.everest.api.gateway.transaction import (
    EverestAddTransactionRequest, EverestTransaction)
from services.everest.definitions import fields as everest_fields
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.transaction_type import TransactionType
from starkware.starknet.services.api.contract_definition import ContractDefinition


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


@marshmallow_dataclass.dataclass(frozen=True)
class Deploy(Transaction):
    """
    Represents a transaction in the StarkNet network that is a deployment of a StarkNet contract.
    """

    contract_address: int = field(metadata=fields.contract_address_metadata)
    contract_definition: ContractDefinition

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.DEPLOY

    @marshmallow.decorators.post_dump
    def compress_program(self, data: Dict[str, Any], many: bool, **kwargs) -> Dict[str, Any]:
        full_program = json.dumps(data['contract_definition']['program'])
        compressed_program = gzip.compress(data=full_program.encode('ascii'))
        compressed_program = base64.b64encode(compressed_program)
        data['contract_definition']['program'] = compressed_program.decode('ascii')
        return data

    @marshmallow.decorators.pre_load
    def decompress_program(self, data: Dict[str, Any], many: bool, **kwargs) -> Dict[str, Any]:
        compressed_program: str = data['contract_definition']['program']
        compressed_program_bytes = base64.b64decode(compressed_program.encode('ascii'))
        decompressed_program = gzip.decompress(data=compressed_program_bytes)
        data['contract_definition']['program'] = json.loads(decompressed_program.decode('ascii'))
        return data

    def _remove_debug_info(self) -> 'Deploy':
        """
        Sets debug_info in the Cairo contract program to None.
        Returns an altered Deploy instance.
        """
        altered_program = dataclasses.replace(self.contract_definition.program, debug_info=None)
        altered_contract_definition = dataclasses.replace(
            self.contract_definition, program=altered_program)
        return dataclasses.replace(self, contract_definition=altered_contract_definition)


@marshmallow_dataclass.dataclass(frozen=True)
class InvokeFunction(Transaction):
    """
    Represents a transaction in the StarkNet network that is an invocation of a Cairo contract
    function.
    """

    contract_address: int = field(metadata=fields.contract_address_metadata)
    # A field element that encodes the signature of the called function.
    entry_point_selector: int = field(metadata=fields.entry_point_selector_metadata)
    calldata: List[int] = field(metadata=fields.call_data_metadata)

    # Class variables.
    tx_type: ClassVar[TransactionType] = TransactionType.INVOKE_FUNCTION


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


@marshmallow_dataclass.dataclass(frozen=True)
class AddTransactionRequest(EverestAddTransactionRequest):
    tx: Transaction
    tx_id: int = field(metadata=everest_fields.tx_id_field_metadata)
