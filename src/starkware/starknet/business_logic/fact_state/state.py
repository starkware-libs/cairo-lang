import logging
from dataclasses import field
from typing import Dict, Mapping, MutableMapping, Optional

import marshmallow_dataclass

from services.everest.business_logic.state import (
    CarriedStateBase,
    EverestStateDiff,
    SharedStateBase,
    StateSelectorBase,
)
from starkware.cairo.lang.vm.cairo_pie import ExecutionResources
from starkware.python.utils import gather_in_chunks, safe_zip, subtract_mappings
from starkware.starknet.business_logic.fact_state.contract_state_objects import (
    ContractCarriedState,
    ContractState,
)
from starkware.starknet.business_logic.fact_state.patricia_state import PatriciaStateReader
from starkware.starknet.business_logic.fact_state.utils import (
    to_cached_state_storage_mapping,
    to_state_diff_storage_mapping,
)
from starkware.starknet.business_logic.state.state import CachedState
from starkware.starknet.business_logic.state.state_api import StateReader
from starkware.starknet.business_logic.state.state_api_objects import BlockInfo
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starkware_utils.commitment_tree.binary_fact_tree import BinaryFactDict
from starkware.starkware_utils.commitment_tree.patricia_tree.patricia_tree import PatriciaTree
from starkware.starkware_utils.config_base import Config
from starkware.storage.storage import DBObject, FactFetchingContext

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
        Should only be called by _create_from_parent_state and empty_for_testing class methods.
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

        state = CachedState(
            block_info=shared_state.block_info,
            state_reader=PatriciaStateReader(
                global_state_root=shared_state.contract_states,
                ffc=ffc,
                contract_class_storage=ffc.storage,
            ),
            contract_class_cache={},
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
        state = CachedState(
            block_info=self.block_info,
            state_reader=PatriciaStateReader(
                global_state_root=self.contract_states,
                ffc=ffc,
                contract_class_storage=ffc.storage,
            ),
        )
        return CarriedState(parent_state=None, state=state)

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
            storage_updates=to_state_diff_storage_mapping(
                storage_writes=state_cache._storage_writes
            ),
            block_info=current_carried_state.state.block_info,
        )

    async def apply_updates(
        self,
        ffc: FactFetchingContext,
        address_to_class_hash: Mapping[int, bytes],
        address_to_nonce: Mapping[int, int],
        storage_updates: Mapping[int, Mapping[int, int]],
        block_info: BlockInfo,
    ) -> "SharedState":
        accessed_addresses = (
            address_to_class_hash.keys() | address_to_nonce.keys() | storage_updates.keys()
        )
        current_contract_states = await self.contract_states.get_leaves(
            ffc=ffc, indices=accessed_addresses, fact_cls=ContractState
        )

        # Update contract storage roots with cached changes.
        updated_contract_states = await gather_in_chunks(
            awaitables=(
                current_contract_states[address].update(
                    ffc=ffc,
                    updates=storage_updates.get(address, {}),
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
class StateDiff(EverestStateDiff, DBObject):
    """
    Holds uncommitted changes induced on StarkNet contracts.
    """

    address_to_class_hash: Mapping[int, bytes] = field(
        metadata=fields.address_to_class_hash_metadata
    )
    address_to_nonce: Mapping[int, int] = field(metadata=fields.address_to_nonce_metadata)
    storage_updates: Mapping[int, Mapping[int, int]] = field(
        metadata=fields.storage_updates_metadata
    )
    block_info: BlockInfo

    @classmethod
    def empty(cls, block_info: BlockInfo):
        """
        Returns an empty state diff object relative to the given block info.
        """
        return cls(
            address_to_class_hash={},
            address_to_nonce={},
            storage_updates={},
            block_info=block_info,
        )

    @classmethod
    def from_cached_state(cls, cached_state: CachedState) -> "StateDiff":
        state_cache = cached_state.cache
        storage_updates = to_state_diff_storage_mapping(
            storage_writes=subtract_mappings(
                state_cache._storage_writes, state_cache._storage_initial_values
            )
        )
        address_to_nonce = subtract_mappings(
            state_cache._nonce_writes, state_cache._nonce_initial_values
        )
        address_to_class_hash = subtract_mappings(
            state_cache._class_hash_writes, state_cache._class_hash_initial_values
        )
        return cls(
            address_to_class_hash=address_to_class_hash,
            address_to_nonce=address_to_nonce,
            storage_updates=storage_updates,
            block_info=cached_state.block_info,
        )

    def to_cached_state(self, state_reader: StateReader) -> CachedState:
        cached_state = CachedState(block_info=self.block_info, state_reader=state_reader)
        cached_state.cache.set_initial_values(
            address_to_class_hash=self.address_to_class_hash,
            address_to_nonce=self.address_to_nonce,
            storage_updates=to_cached_state_storage_mapping(storage_updates=self.storage_updates),
        )

        return cached_state

    def squash(self, other: "StateDiff") -> "StateDiff":
        address_to_class_hash = {**self.address_to_class_hash, **other.address_to_class_hash}
        address_to_nonce = {**self.address_to_nonce, **other.address_to_nonce}
        storage_updates: Dict[int, Dict[int, int]] = {}
        for address in self.storage_updates.keys() | other.storage_updates.keys():
            storage_updates[address] = {
                **self.storage_updates.get(address, {}),
                **other.storage_updates.get(address, {}),
            }
        self.block_info.validate_legal_progress(next_block_info=other.block_info)

        return StateDiff(
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
