import dataclasses
from dataclasses import field
from typing import Dict, List

import marshmallow_dataclass

from starkware.starknet.business_logic.fact_state.contract_state_objects import ContractState
from starkware.starknet.business_logic.transaction.objects import InternalTransaction
from starkware.starknet.core.os.syscall_utils import OsSysCallHandler
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.storage.starknet_storage import OsGlobalStarknetStorage
from starkware.starkware_utils.commitment_tree.patricia_tree.patricia_tree import PatriciaTree
from starkware.starkware_utils.validated_dataclass import (
    ValidatedDataclass,
    ValidatedMarshmallowDataclass,
)


@marshmallow_dataclass.dataclass(frozen=True)
class StarknetOsInput(ValidatedMarshmallowDataclass):
    global_state_commitment_tree: PatriciaTree
    contract_definitions: Dict[bytes, ContractClass] = field(
        metadata=fields.bytes_as_hex_dict_keys_metadata(values_schema=ContractClass.Schema)
    )
    contracts: Dict[int, ContractState]
    general_config: StarknetGeneralConfig
    transactions: List[InternalTransaction]


@dataclasses.dataclass(frozen=True)
class OsHints(ValidatedDataclass):
    os_input: StarknetOsInput
    global_state_storage: OsGlobalStarknetStorage
    syscall_handler: OsSysCallHandler
