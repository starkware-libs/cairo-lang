from typing import Dict

from starkware.starknet.business_logic.fact_state.contract_state_objects import (
    ContractClassFact,
    ContractState,
)
from starkware.starknet.business_logic.state.state_api import (
    StateReader,
    get_stark_exception_on_undeclared_contract,
)
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.storage.starknet_storage import StorageLeaf
from starkware.starkware_utils.commitment_tree.patricia_tree.patricia_tree import PatriciaTree
from starkware.storage.storage import FactFetchingContext


class PatriciaStateReader(StateReader):
    """
    A Patricia implementation of StateReader.
    """

    def __init__(self, global_state_root: PatriciaTree, ffc: FactFetchingContext):
        # Members related to dynamic retrieval of facts during transaction execution.
        self.ffc = ffc
        # The last committed state; the one this state was created from.
        self.global_state_root = global_state_root
        # A mapping from contract address to its cached state.
        self.contract_states: Dict[int, ContractState] = {}

    # StateReader API.

    async def get_contract_class(self, class_hash: bytes) -> ContractClass:
        contract_class_fact = await ContractClassFact.get(
            storage=self.ffc.storage, suffix=class_hash
        )

        if contract_class_fact is None:
            raise get_stark_exception_on_undeclared_contract(class_hash=class_hash)

        contract_class = contract_class_fact.contract_definition
        contract_class.validate()
        return contract_class

    async def get_class_hash_at(self, contract_address: int) -> bytes:
        contract_state = await self._get_contract_state(contract_address=contract_address)
        return contract_state.contract_hash

    async def get_nonce_at(self, contract_address: int) -> int:
        contract_state = await self._get_contract_state(contract_address=contract_address)
        return contract_state.nonce

    async def get_storage_at(self, contract_address: int, key: int) -> int:
        contract_state = await self._get_contract_state(contract_address=contract_address)

        contract_storage_tree_height = contract_state.storage_commitment_tree.height
        assert (
            0 <= key < 2**contract_storage_tree_height
        ), f"The address {key} is out of range: [0, 2**{contract_storage_tree_height})."

        storage_leaf = await self._fetch_storage_leaf(contract_state=contract_state, key=key)

        return storage_leaf.value

    # Internal utilities.

    async def _get_raw_contract_class(self, class_hash: bytes) -> bytes:
        raw_contract_class_fact = await self.ffc.storage.get_value(
            key=ContractClassFact.db_key(suffix=class_hash)
        )

        if raw_contract_class_fact is None:
            raise get_stark_exception_on_undeclared_contract(class_hash=class_hash)

        return raw_contract_class_fact

    async def _get_contract_state(self, contract_address: int) -> ContractState:
        if contract_address not in self.contract_states:
            self.contract_states[contract_address] = await self._fetch_contract_state(
                contract_address=contract_address
            )

        return self.contract_states[contract_address]

    async def _fetch_contract_state(self, contract_address: int) -> ContractState:
        return await self.global_state_root.get_leaf(
            ffc=self.ffc, index=contract_address, fact_cls=ContractState
        )

    async def _fetch_storage_leaf(self, contract_state: ContractState, key: int) -> StorageLeaf:
        return await contract_state.storage_commitment_tree.get_leaf(
            ffc=self.ffc, index=key, fact_cls=StorageLeaf
        )
