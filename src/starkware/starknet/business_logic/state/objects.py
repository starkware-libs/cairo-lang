import dataclasses
from dataclasses import field
from typing import ClassVar, Dict, Iterable, List, cast

import marshmallow_dataclass

from starkware.python.utils import gather_in_chunks, safe_zip, to_bytes
from starkware.starknet.core.os.contract_hash import compute_contract_hash
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.storage.starknet_storage import StorageLeaf
from starkware.starkware_utils.commitment_tree.leaf_fact import LeafFact
from starkware.starkware_utils.commitment_tree.patricia_tree.nodes import EmptyNodeFact
from starkware.starkware_utils.commitment_tree.patricia_tree.patricia_tree import PatriciaTree
from starkware.starkware_utils.error_handling import stark_assert
from starkware.starkware_utils.validated_dataclass import (
    ValidatedDataclass,
    ValidatedMarshmallowDataclass,
)
from starkware.storage.storage import HASH_BYTES, Fact, FactFetchingContext, HashFunctionType


@marshmallow_dataclass.dataclass(frozen=True)
class ContractDefinitionFact(ValidatedMarshmallowDataclass, Fact):
    """
    Represents a single contract definition which is stored in the full StarkNet state commitment
    tree.
    """

    contract_definition: ContractDefinition

    def _hash(self, hash_func: HashFunctionType) -> bytes:
        return to_bytes(compute_contract_hash(contract_definition=self.contract_definition))


@marshmallow_dataclass.dataclass(frozen=True)
class ContractState(ValidatedMarshmallowDataclass, LeafFact):
    """
    Represents the state of a single contract (sub-commitment tree) in the full StarkNet state
    commitment tree.
    The contract state containts the contract object (None if the contract was not yet deployed)
    and the commitment tree root of the contract storage.
    """

    contract_hash: bytes = field(metadata=fields.contract_hash_metadata)
    storage_commitment_tree: PatriciaTree

    UNINITIALIZED_CONTRACT_HASH: ClassVar[bytes] = b"\x00" * HASH_BYTES

    @classmethod
    async def create(
        cls, contract_hash: bytes, storage_commitment_tree: PatriciaTree
    ) -> "ContractState":
        return cls(storage_commitment_tree=storage_commitment_tree, contract_hash=contract_hash)

    @classmethod
    async def empty(
        cls, storage_commitment_tree_height: int, ffc: FactFetchingContext
    ) -> "ContractState":
        empty_tree = await PatriciaTree.empty_tree(
            ffc=ffc, height=storage_commitment_tree_height, leaf_fact=StorageLeaf.empty()
        )

        return cls(
            storage_commitment_tree=empty_tree, contract_hash=cls.UNINITIALIZED_CONTRACT_HASH
        )

    @property
    def is_empty(self) -> bool:
        return not self.initialized

    def _hash(self, hash_func: HashFunctionType) -> bytes:
        """
        Computes the hash of the node containing the contract's information, including the contract
        definition and storage.
        """
        if self.is_empty:
            return EmptyNodeFact.EMPTY_NODE_HASH

        CONTRACT_STATE_HASH_VERSION = 0
        RESERVED = 0

        # Set hash_value = H(H(contract_hash, storage_root), RESERVED).
        hash_value = hash_func(self.contract_hash, self.storage_commitment_tree.root)
        hash_value = hash_func(hash_value, to_bytes(RESERVED))

        # Return H(hash_value, CONTRACT_STATE_HASH_VERSION). CONTRACT_STATE_HASH_VERSION must be in
        # the outermost hash to guarantee unique "decoding".
        return hash_func(hash_value, to_bytes(CONTRACT_STATE_HASH_VERSION))

    @staticmethod
    async def fetch_contract_definitions(
        contract_states: Iterable["ContractState"], ffc: FactFetchingContext
    ) -> Dict[bytes, ContractDefinition]:
        # Gather all distinct hashes.
        contract_hashes = set(contract.contract_hash for contract in contract_states)
        # Discard empty hash for not yet deployed contracts.
        contract_hashes -= {ContractState.UNINITIALIZED_CONTRACT_HASH}

        # Fetch corresponding contract definitions from storage.
        contract_definition_facts = await gather_in_chunks(
            awaitables=(
                ContractDefinitionFact.get_or_fail(storage=ffc.storage, suffix=contract_hash)
                for contract_hash in contract_hashes
            )
        )
        contract_definitions = [
            fact.contract_definition
            for fact in cast(List[ContractDefinitionFact], contract_definition_facts)
        ]

        return dict(safe_zip(contract_hashes, contract_definitions))

    @property
    def initialized(self) -> bool:
        uninitialized = self.contract_hash == self.UNINITIALIZED_CONTRACT_HASH
        if uninitialized:
            assert (
                self.storage_commitment_tree.root == EmptyNodeFact.EMPTY_NODE_HASH
            ), "Contract storage commitment root must be empty if contract hash is uninitialized."

        return not uninitialized

    def assert_initialized(self, contract_address: int):
        """
        Asserts that the current ContractState is initialized.

        Takes contract_address as input to improve the error message.
        """
        address_formatter = fields.L2AddressField.format
        stark_assert(
            self.initialized,
            code=StarknetErrorCode.UNINITIALIZED_CONTRACT,
            message=f"Contract with address {address_formatter(contract_address)} is not deployed.",
        )

    async def update(
        self, ffc: FactFetchingContext, updates: Dict[int, StorageLeaf]
    ) -> "ContractState":
        """
        Returns a new ContractState object with the same contract object and a newly calculated
        root, according to the given updates of its leaves.
        """
        updated_storage_commitment_tree = await self.storage_commitment_tree.update(
            ffc=ffc, modifications=updates.items()
        )

        return ContractState(
            contract_hash=self.contract_hash,
            storage_commitment_tree=updated_storage_commitment_tree,
        )


@dataclasses.dataclass
class ContractCarriedState(ValidatedDataclass):
    """
    Represents the state of a single contract in the full StarkNet state commitment tree,
    as well as the modifications made to the contract storage, accumulated between transactions.
    """

    state: ContractState
    storage_updates: Dict[int, StorageLeaf]

    @property
    def has_pending_updates(self) -> bool:
        """
        Returns whether there are cached storage changes that are not yet applied to the storage
        commitment tree root.
        """
        return len(self.storage_updates) > 0

    @classmethod
    async def empty(
        cls, storage_commitment_tree_height: int, ffc: FactFetchingContext
    ) -> "ContractCarriedState":
        empty_state = await ContractState.empty(
            storage_commitment_tree_height=storage_commitment_tree_height, ffc=ffc
        )

        return cls(state=empty_state, storage_updates={})

    async def update(self, ffc: FactFetchingContext) -> "ContractCarriedState":
        updated_state = await self.state.update(ffc=ffc, updates=self.storage_updates)

        return ContractCarriedState(state=updated_state, storage_updates={})
