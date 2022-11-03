import logging
from typing import Dict, Mapping, MutableMapping, Optional

import marshmallow_dataclass

from services.everest.business_logic.state import (
    CarriedStateBase,
    EverestStateDiff,
    SharedStateBase,
    StateSelectorBase,
)
from starkware.cairo.lang.vm.cairo_pie import ExecutionResources
from starkware.python.utils import gather_in_chunks, safe_zip
from starkware.starknet.business_logic.fact_state.contract_state_objects import (
    ContractCarriedState,
    ContractState,
)
from starkware.starknet.business_logic.fact_state.patricia_state import PatriciaStateReader
from starkware.starknet.business_logic.state.state import CachedState, StorageEntry
from starkware.starknet.business_logic.state.state_api_objects import BlockInfo
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starknet.storage.starknet_storage import ContractStorageMapping, StorageLeaf
from starkware.starkware_utils.commitment_tree.binary_fact_tree import BinaryFactDict
from starkware.starkware_utils.commitment_tree.patricia_tree.patricia_tree import PatriciaTree
from starkware.starkware_utils.config_base import Config
from starkware.storage.storage import FactFetchingContext

logger = logging.getLogger(__name__)
state_objects_logger = logging.getLogger(f"{__name__}:state_objects_logger")

ContractCarriedStateMapping = MutableMapping[int, ContractCarriedState]


class ExecutionResourcesManager:
    """
    Aggregates execution resources throughout transaction stream processing.
    """

    def __init__(
        self,
        cairo_usage: ExecutionResources,
        syscall_counter: Dict[str, int],
    ):
        # The accumulated Cairo usage.
        self.cairo_usage = cairo_usage

        # A mapping from system call to the cumulative times it was invoked.
        self.syscall_counter = syscall_counter

    # Alternative constructors.

    @classmethod
    def empty(cls) -> "ExecutionResourcesManager":
        return cls(
            cairo_usage=ExecutionResources.empty(),
            syscall_counter={},
        )


class CarriedState(CarriedStateBase):
    """
    A state containing a mapping from contract addresses to their states and the accumulated
    modifications to the contract storage across transactions.

    This will be a sub-state of the total state (SharedState). It is carried and maintained by
    the Batcher, as each pending transaction is applied to it during the attempt to include it in
    a block. After a block is created the carried state is applied to the shared state.
    """

    def __init__(
        self,
        parent_state: Optional["CarriedState"],
        state: CachedState,
    ):
        """
        Private constructor.
        Should only be called by _create_from_parent_state and create_unfilled class methods.
        """
        super().__init__(parent_state=parent_state)
        self.state = state

    # Alternative constructors.

    @classmethod
    def _create_from_parent_state(cls, parent_state: "CarriedState") -> "CarriedState":
        """
        Instantiates a CarriedState object that acts as proxy to given parent_state.
        """
        assert (
            parent_state.state is not None
        ), "Parent cached state must be concrete when creating a child state."

        return cls(
            # Parent carried state - must not be modified.
            parent_state=parent_state,
            # Cached state.
            state=parent_state.state._copy(),
        )

    @classmethod
    def create_unfilled(
        cls, shared_state: "SharedState", ffc: FactFetchingContext
    ) -> "CarriedState":
        """
        Creates a carried state based on the given shared state, where the fields related to the
        commitment leaves (e.g., contract states) are kept unfilled.
        """
        state = CachedState(
            block_info=shared_state.block_info,
            state_reader=PatriciaStateReader(
                global_state_root=shared_state.contract_states, ffc=ffc
            ),
        )

        return cls(
            parent_state=None,
            state=state,
        )

    @classmethod
    async def empty_for_testing(
        cls,
        shared_state: Optional["SharedState"],
        ffc: FactFetchingContext,
        general_config: StarknetGeneralConfig,
    ) -> "CarriedState":
        """
        Creates an empty carried state allowing accessing all possible contract addresses (by
        using defaultdict). This constructor should only be used in tests.
        """
        if shared_state is None:
            shared_state = await SharedState.empty(ffc=ffc, general_config=general_config)

        return cls.create_unfilled(ffc=ffc, shared_state=shared_state)

    @classmethod
    def from_contracts(
        cls,
        shared_state: "SharedState",
        ffc: FactFetchingContext,
        contract_definitions: MutableMapping[bytes, ContractClass],
        contract_states: ContractCarriedStateMapping,
    ) -> "CarriedState":
        """
        Returns a carried state object, containing the given contracts.
        Other members are initialized with the empty object values.
        This is a utility function and should not be used in the regular flow.
        """
        state_reader = PatriciaStateReader(global_state_root=shared_state.contract_states, ffc=ffc)
        state = CachedState(block_info=shared_state.block_info, state_reader=state_reader)
        state.cache.update_writes(
            contract_classes=contract_definitions,
            address_to_class_hash={
                address: state.state.contract_hash for address, state in contract_states.items()
            },
            address_to_nonce={address: state.nonce for address, state in contract_states.items()},
            storage_updates={
                (address, key): leaf.value
                for address, state in contract_states.items()
                for key, leaf in state.storage_updates.items()
            },
        )
        return cls(
            parent_state=None,
            state=state,
        )

    @property
    def block_info(self) -> BlockInfo:
        return self.state.block_info

    def create_child_state_for_querying(self) -> "CarriedState":
        """
        Creates a lazy copy of self.
        Used for transaction queries, where we want to have a separation from the parent state
        (e.g., using the chain map mechanism to extract the most recent transaction's affect on the
        state) and do not need to apply the changes.
        Must not be used on regular flow.
        """
        return CarriedState._create_from_parent_state(parent_state=self)

    @property
    def state_selector(self) -> StateSelectorBase:
        raise NotImplementedError("state_selector() is not implemented on StarkNet CarriedState.")

    def select(self, state_selector: StateSelectorBase) -> "CarriedState":
        raise NotImplementedError("select() is not implemented on StarkNet CarriedState.")

    def _fill_missing(self, other: "CarriedState"):
        raise NotImplementedError("_fill_missing() is not implemented on StarkNet CarriedState.")

    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    def subtract_merkle_facts(self, previous_state: "CarriedState") -> "CarriedState":
        """
        Subtraction of contract states from current carried state to previous one is unnecessary,
        since it is very unlikely contract state will not change throughout a block.
        """
        raise NotImplementedError(
            "subtract_merkle_facts() is not implemented on StarkNet CarriedState."
        )

    def _apply(self):
        """
        Applies state updates to self.parent_state.
        This method should not be directly used; use copy_and_apply instead.
        """
        # Apply state updates.
        parent_state = self.non_optional_parent_state

        # Update CachedState.
        self.state._apply(parent=parent_state.state)

        # Update additional entire block-related information.
        parent_state.state.block_info = self.state.block_info


@marshmallow_dataclass.dataclass(frozen=True)
class SharedState(SharedStateBase):
    """
    A class representing a combination of the onchain and offchain state.
    """

    contract_states: PatriciaTree
    block_info: BlockInfo

    @classmethod
    async def empty(cls, ffc: FactFetchingContext, general_config: Config) -> "SharedState":
        """
        Returns an empty state. This is called before creating very first block.
        """
        # Downcast arguments to application-specific types.
        assert isinstance(general_config, StarknetGeneralConfig)

        empty_contract_state = await ContractState.empty(
            storage_commitment_tree_height=general_config.contract_storage_commitment_tree_height,
            ffc=ffc,
        )
        empty_contract_states = await PatriciaTree.empty_tree(
            ffc=ffc,
            height=general_config.global_state_commitment_tree_height,
            leaf_fact=empty_contract_state,
        )

        return cls(
            contract_states=empty_contract_states,
            block_info=BlockInfo.empty(sequencer_address=general_config.sequencer_address),
        )

    def to_carried_state(self, ffc: FactFetchingContext) -> CarriedState:
        """
        Returns an unfilled CarriedState.
        """
        return CarriedState.create_unfilled(ffc=ffc, shared_state=self)

    async def get_filled_carried_state(
        self, ffc: FactFetchingContext, state_selector: StateSelectorBase
    ) -> CarriedState:
        raise NotImplementedError(
            "get_filled_carried_state() is not implemented on StarkNet SharedState."
        )

    async def apply_state_updates(
        self,
        ffc: FactFetchingContext,
        previous_carried_state: CarriedStateBase,
        current_carried_state: CarriedStateBase,
        facts: Optional[BinaryFactDict] = None,
    ) -> "SharedState":
        # Note that previous_carried_state is part of the API of
        # SharedStateBase.apply_state_updates().

        # Downcast arguments to application-specific types.
        assert isinstance(previous_carried_state, CarriedState)
        assert isinstance(current_carried_state, CarriedState)

        state_objects_logger.debug(
            f"Updating state from previous carried state: {previous_carried_state} "
            f"to current carried state: {current_carried_state}"
        )

        # Prepare storage updates to apply.
        state_cache = current_carried_state.state.cache
        return await self.apply_updates(
            ffc=ffc,
            address_to_class_hash=state_cache._class_hash_writes,
            address_to_nonce=state_cache._nonce_writes,
            storage_updates=state_cache._storage_writes,
            block_info=current_carried_state.state.block_info,
        )

    async def apply_updates(
        self,
        ffc: FactFetchingContext,
        address_to_class_hash: Mapping[int, bytes],
        address_to_nonce: Mapping[int, int],
        storage_updates: Mapping[StorageEntry, int],
        block_info: BlockInfo,
    ) -> "SharedState":
        address_to_storage_updates: Dict[int, ContractStorageMapping] = {}
        for (address, key), value in storage_updates.items():
            contract_storage_updates = address_to_storage_updates.setdefault(address, {})
            contract_storage_updates[key] = StorageLeaf(value=value)

        accessed_addresses = (
            set(address_to_class_hash.keys())
            | set(address_to_nonce.keys())
            | {address for address, _ in storage_updates.keys()}
        )
        current_contract_states = await self.contract_states.get_leaves(
            ffc=ffc, indices=accessed_addresses, fact_cls=ContractState
        )

        # Update contract storage roots with cached changes.
        updated_contract_states = await gather_in_chunks(
            awaitables=(
                current_contract_states[address].update(
                    ffc=ffc,
                    updates=address_to_storage_updates.get(address, {}),
                    nonce=address_to_nonce.get(address, None),
                    class_hash=address_to_class_hash.get(address, None),
                )
                for address in accessed_addresses
            )
        )

        # Apply contract changes on global root.
        updated_global_contract_root = await self.contract_states.update(
            ffc=ffc, modifications=list(safe_zip(accessed_addresses, updated_contract_states))
        )

        return SharedState(contract_states=updated_global_contract_root, block_info=block_info)


@marshmallow_dataclass.dataclass(frozen=True)
class StateDiff(EverestStateDiff):
    """
    Holds uncommitted changes induced on StarkNet contracts.
    """

    class_hash_to_class: Mapping[bytes, ContractClass]
    address_to_class_hash: Mapping[int, bytes]
    address_to_nonce: Mapping[int, int]
    storage_updates: Mapping[StorageEntry, int]
    block_info: BlockInfo

    @classmethod
    def empty(cls, block_info: BlockInfo):
        """
        Returns an empty state diff object relative to the given block info.
        """
        return cls(
            class_hash_to_class={},
            address_to_class_hash={},
            address_to_nonce={},
            storage_updates={},
            block_info=block_info,
        )

    @classmethod
    def from_cached_state(cls, cached_state: CachedState) -> "StateDiff":
        state_cache = cached_state.cache
        return cls(
            class_hash_to_class=state_cache.contract_classes,
            address_to_class_hash=state_cache._class_hash_writes,
            address_to_nonce=state_cache._nonce_writes,
            storage_updates=state_cache._storage_writes,
            block_info=cached_state.block_info,
        )

    def to_cached_state(self, ffc: FactFetchingContext, state: SharedState) -> CachedState:
        cached_state = CachedState(
            block_info=self.block_info,
            state_reader=PatriciaStateReader(global_state_root=state.contract_states, ffc=ffc),
        )
        cached_state.cache.update_writes(
            contract_classes=self.class_hash_to_class,
            address_to_class_hash=self.address_to_class_hash,
            address_to_nonce=self.address_to_nonce,
            storage_updates=self.storage_updates,
        )

        return cached_state

    def squash(self, other: "StateDiff") -> "StateDiff":
        class_hash_to_class = {**self.class_hash_to_class, **other.class_hash_to_class}
        address_to_class_hash = {**self.address_to_class_hash, **other.address_to_class_hash}
        address_to_nonce = {**self.address_to_nonce, **other.address_to_nonce}
        storage_updates = {**self.storage_updates, **other.storage_updates}
        self.block_info.validate_legal_progress(next_block_info=other.block_info)

        return StateDiff(
            class_hash_to_class=class_hash_to_class,
            address_to_class_hash=address_to_class_hash,
            address_to_nonce=address_to_nonce,
            storage_updates=storage_updates,
            block_info=other.block_info,
        )

    async def commit(
        self, ffc: FactFetchingContext, previous_state: SharedStateBase
    ) -> SharedState:
        # Downcast argument to application-specific type.
        assert isinstance(previous_state, SharedState)

        return await previous_state.apply_updates(
            ffc=ffc,
            address_to_class_hash=self.address_to_class_hash,
            address_to_nonce=self.address_to_nonce,
            storage_updates=self.storage_updates,
            block_info=self.block_info,
        )
