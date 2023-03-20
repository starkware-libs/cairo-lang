import dataclasses
from dataclasses import field
from typing import Collection, Dict, Mapping, Set, Tuple, Type

from starkware.python.utils import from_bytes
from starkware.starknet.definitions import fields
from starkware.starkware_utils.commitment_tree.binary_fact_tree import BinaryFactDict
from starkware.starkware_utils.commitment_tree.leaf_fact import LeafFact
from starkware.starkware_utils.commitment_tree.leaf_fact_utils import FeltLeaf
from starkware.starkware_utils.commitment_tree.patricia_tree.patricia_tree import PatriciaTree
from starkware.starkware_utils.validated_dataclass import ValidatedDataclass
from starkware.storage.storage import FactFetchingContext

ContractStorageMapping = Dict[int, "StorageLeaf"]


class StorageLeaf(FeltLeaf):
    """
    Represents a commitment tree leaf in a Starknet contract storage.
    """

    @classmethod
    def prefix(cls) -> bytes:
        return b"starknet_storage_leaf"


@dataclasses.dataclass(frozen=True)
class CommitmentInfo(ValidatedDataclass):
    """
    Contains hints needed for the commitment tree update in the OS.
    """

    previous_root: int
    updated_root: int
    tree_height: int
    commitment_facts: Mapping[int, Tuple[int, ...]] = field(
        metadata=fields.commitment_facts_metadata
    )

    @classmethod
    async def create(
        cls,
        previous_tree: PatriciaTree,
        updated_tree: PatriciaTree,
        accessed_indices: Collection[int],
        leaf_fact_cls: Type[LeafFact],
        ffc: FactFetchingContext,
    ) -> "CommitmentInfo":
        assert previous_tree.height == updated_tree.height, "Inconsistent tree heights."

        # Perform the commitment to collect the facts needed by the OS.
        modifications = await updated_tree.get_leaves(
            ffc=ffc, indices=accessed_indices, fact_cls=leaf_fact_cls
        )
        commitment_facts: BinaryFactDict = {}
        actual_updated_tree = await previous_tree.update(
            ffc=ffc, modifications=modifications.items(), facts=commitment_facts
        )
        assert actual_updated_tree == updated_tree, "Inconsistent commitment tree roots."

        return cls(
            previous_root=from_bytes(previous_tree.root),
            updated_root=from_bytes(updated_tree.root),
            tree_height=updated_tree.height,
            commitment_facts=commitment_facts,
        )


class OsSingleStarknetStorage:
    """
    Represents a single contract storage.
    It is used by the Starknet OS run in the GpsAmbassador.
    """

    def __init__(self, commitment_info: CommitmentInfo, ongoing_storage_changes: Dict[int, int]):
        """
        The constructor is private.
        """
        self.commitment_info = commitment_info
        self.ongoing_storage_changes = ongoing_storage_changes

    @classmethod
    async def create(
        cls,
        previous_tree: PatriciaTree,
        updated_tree: PatriciaTree,
        accessed_addresses: Set[int],
        ffc: FactFetchingContext,
    ) -> "OsSingleStarknetStorage":
        commitment_info = await CommitmentInfo.create(
            previous_tree=previous_tree,
            updated_tree=updated_tree,
            accessed_indices=accessed_addresses,
            leaf_fact_cls=StorageLeaf,
            ffc=ffc,
        )
        # Fetch initial values of keys accessed by this contract.
        initial_leaves = await previous_tree.get_leaves(
            ffc=ffc, indices=accessed_addresses, fact_cls=StorageLeaf
        )
        initial_entries = {key: leaf.value for key, leaf in initial_leaves.items()}

        return cls(
            commitment_info=commitment_info,
            ongoing_storage_changes=initial_entries,
        )

    # Read/write access to ongoing storage changes;
    # used to create a new storage entry (which contains the previous and the new value)
    # when executing the storage_write system call.

    def read(self, key: int) -> int:
        return self.ongoing_storage_changes[key]

    def write(self, key: int, value: int):
        self.ongoing_storage_changes[key] = value
