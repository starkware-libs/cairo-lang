import copy
import dataclasses
import logging
import typing
from collections import ChainMap, defaultdict
from dataclasses import field
from typing import Dict, MutableMapping, Optional, Set, Tuple

import marshmallow_dataclass

from services.everest.business_logic.state import (
    CarriedStateBase,
    SharedStateBase,
    StateSelectorBase,
)
from starkware.cairo.lang.vm.cairo_pie import ExecutionResources
from starkware.python.utils import gather_in_chunks, safe_zip
from starkware.starknet.business_logic.state.objects import ContractCarriedState, ContractState
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.definitions.general_config import DEFAULT_GAS_PRICE, StarknetGeneralConfig
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.storage.starknet_storage import StorageLeaf
from starkware.starkware_utils.commitment_tree.binary_fact_tree import BinaryFactDict
from starkware.starkware_utils.commitment_tree.patricia_tree.patricia_tree import PatriciaTree
from starkware.starkware_utils.config_base import Config
from starkware.starkware_utils.error_handling import stark_assert_eq, stark_assert_le
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass
from starkware.storage.storage import FactFetchingContext

logger = logging.getLogger(__name__)
state_objects_logger = logging.getLogger(f"{__name__}:state_objects_logger")

ContractCarriedStateMapping = MutableMapping[int, ContractCarriedState]
ContractCarriedStateChainMapping = typing.ChainMap[int, ContractCarriedState]


@marshmallow_dataclass.dataclass(frozen=True)
class BlockInfo(ValidatedMarshmallowDataclass):
    # The sequence number of the last block created.
    block_number: int = field(metadata=fields.block_number_metadata)

    # Timestamp of the beginning of the last block creation attempt.
    block_timestamp: int = field(metadata=fields.timestamp_metadata)

    # L1 gas price (in Wei) measured at the beginning of the last block creation attempt.
    gas_price: int = field(metadata=fields.gas_price_metadata)

    @classmethod
    def empty(cls) -> "BlockInfo":
        """
        Returns an empty BlockInfo object; i.e., the one before the first in the chain.
        """
        return cls(block_number=-1, block_timestamp=0, gas_price=0)

    @classmethod
    def create_for_testing(cls, block_number: int, block_timestamp: int) -> "BlockInfo":
        """
        Returns a BlockInfo object with default gas_price.
        """
        return cls(
            block_number=block_number,
            block_timestamp=block_timestamp,
            gas_price=DEFAULT_GAS_PRICE,
        )

    def validate_legal_progress(self, next_block_info: "BlockInfo"):
        """
        Validates that next_block_info is a legal progress of self.
        """
        # Check that the block number increases by 1.
        stark_assert_eq(
            next_block_info.block_number,
            self.block_number + 1,
            code=StarknetErrorCode.INVALID_BLOCK_NUMBER,
            message="Block number must increase by 1.",
        )

        # Check that block timestamp in not decreasing.
        stark_assert_le(
            self.block_timestamp,
            next_block_info.block_timestamp,
            code=StarknetErrorCode.INVALID_BLOCK_TIMESTAMP,
            message="Block timestamp must not decrease.",
        )


@dataclasses.dataclass(frozen=True)
class StateSelector(StateSelectorBase):
    """
    A class that contains a set of Cairo contract addresses (sub-commitment tree root IDs)
    affected by one/many transaction(s).
    Used for fetching those sub-trees from storage before transaction(s) processing.
    """

    contract_addresses: Set[int]

    @classmethod
    def empty(cls) -> "StateSelector":
        return cls(contract_addresses=set())

    def __and__(self, other: "StateSelector") -> "StateSelector":
        return StateSelector(self.contract_addresses & other.contract_addresses)

    def __or__(self, other: "StateSelector") -> "StateSelector":
        return StateSelector(self.contract_addresses | other.contract_addresses)

    def __sub__(self, other: "StateSelector") -> "StateSelector":
        return StateSelector(self.contract_addresses - other.contract_addresses)

    def __le__(self, other: "StateSelector") -> bool:
        return self.contract_addresses <= other.contract_addresses


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
        shared_state: "SharedState",
        ffc: FactFetchingContext,
        contract_definitions: typing.ChainMap[bytes, ContractDefinition],
        contract_states: ContractCarriedStateChainMapping,
        cairo_usage: ExecutionResources,
        modified_contracts: typing.ChainMap[int, None],
        block_info: BlockInfo,
        syscall_counter: typing.ChainMap[str, int],
    ):
        """
        Private constructor.
        Should only be called by _create_from_parent_state and create_unfilled class methods.
        """
        super().__init__(parent_state=parent_state)

        # The last committed state; the one this carried state was created from.
        # Used for dynamic retrieval of facts during transaction execution.
        self.shared_state = shared_state

        # A mapping from contract definition hash to contract definition.
        self.contract_definitions = contract_definitions

        # A mapping from contract address to its carried state.
        self.contract_states = contract_states

        # The accumulated Cairo usage.
        self.cairo_usage = cairo_usage

        # Carried state fetches commitment tree leaves from storage during transaction processing.
        self.ffc = ffc

        # Addresses of contracts whose storage has changed.
        self.modified_contracts = modified_contracts

        self.block_info = block_info

        # A mapping from system call to the cumulative times it was invoked.
        self.syscall_counter = syscall_counter

    @classmethod
    def _create_from_parent_state(cls, parent_state: "CarriedState") -> "CarriedState":
        """
        Instantiates a CarriedState object that acts as proxy to given parent_state.
        """
        carried_state = cls(
            parent_state=parent_state,
            shared_state=parent_state.shared_state,
            ffc=parent_state.ffc,
            contract_definitions=parent_state.contract_definitions.new_child(),
            contract_states=parent_state.contract_states.new_child(),
            cairo_usage=parent_state.cairo_usage,
            modified_contracts=(parent_state.modified_contracts.new_child()),
            block_info=parent_state.block_info,
            syscall_counter=parent_state.syscall_counter.new_child(),
        )

        return carried_state

    @classmethod
    def create_unfilled(
        cls, shared_state: "SharedState", ffc: FactFetchingContext
    ) -> "CarriedState":
        """
        Creates a carried state based on the given shared state, where the fields related to the
        commitment leaves (e.g., contract states) are kept unfilled.
        """
        return cls(
            parent_state=None,
            ffc=ffc,
            shared_state=shared_state,
            contract_definitions=ChainMap(),
            contract_states=ChainMap(),
            cairo_usage=ExecutionResources.empty(),
            modified_contracts=ChainMap(),
            block_info=shared_state.block_info,
            syscall_counter=ChainMap(),
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
        empty_contract_state = await ContractState.empty(
            storage_commitment_tree_height=general_config.contract_storage_commitment_tree_height,
            ffc=ffc,
        )

        if shared_state is None:
            shared_state = await SharedState.empty(ffc=ffc, general_config=general_config)

        return cls.from_contracts(
            ffc=ffc,
            contract_definitions={},
            shared_state=shared_state,
            contract_states=defaultdict(
                lambda: ContractCarriedState(
                    state=copy.deepcopy(empty_contract_state), storage_updates={}
                )
            ),
        )

    @classmethod
    def from_contracts(
        cls,
        shared_state: "SharedState",
        ffc: FactFetchingContext,
        contract_definitions: MutableMapping[bytes, ContractDefinition],
        contract_states: ContractCarriedStateMapping,
    ) -> "CarriedState":
        """
        Returns a carried state object, containing the given contracts.
        Other members are initialized with the empty object values.
        This is a utility function and should not be used in the regular flow.
        """
        return cls(
            parent_state=None,
            ffc=ffc,
            shared_state=shared_state,
            contract_definitions=ChainMap(contract_definitions),
            contract_states=ChainMap(contract_states),
            cairo_usage=ExecutionResources.empty(),
            modified_contracts=ChainMap(),
            block_info=shared_state.block_info,
            syscall_counter=ChainMap(),
        )

    @property
    def state_selector(self) -> StateSelector:
        """
        Returns the state selector of this CarriedState containing the contract addresses that
        serve as the commitment tree leaf IDs of the full StarkNet state commitment tree.
        """
        return StateSelector(contract_addresses=set(self.contract_states.keys()))

    def select(self, state_selector: StateSelectorBase) -> "CarriedState":
        raise NotImplementedError("select() is not implemented on StarkNet CarriedState.")

    def _fill_missing(self, other: "CarriedState"):
        """
        Enriches state with the missing information from another CarriedState instance.
        This is a private method, only to be called from public fill_missing method.
        """
        self.contract_states.update(other.contract_states)
        self.contract_definitions.update(other.contract_definitions)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CarriedState):
            return NotImplemented

        return self.contract_states == other.contract_states and self.block_info == other.block_info

    def update_contract_storage(self, contract_address: int, modifications: Dict[int, StorageLeaf]):
        """
        Applies the given storage modifications to the given contract storage.
        """
        contract_carried_state = self.contract_states[contract_address]
        self.contract_states[contract_address] = dataclasses.replace(
            contract_carried_state,
            storage_updates={
                **contract_carried_state.storage_updates,
                **modifications,
            },
        )

    def subtract_merkle_facts(self, previous_state: "CarriedState") -> "CarriedState":
        """
        Subtraction of contract states from current carried state to previous one is unnecessary,
        since it is very unlikely contract state will not change throughout a block.
        """
        raise NotImplementedError

    @property
    def chain_maps(self) -> Tuple[typing.ChainMap, ...]:
        return (
            self.contract_states,
            self.contract_definitions,
            self.modified_contracts,
            self.syscall_counter,
        )

    def _validate_references_of_chain_maps(self):
        assert self.parent_state is not None
        for child_chain_map, parent_chain_map in zip(self.chain_maps, self.parent_state.chain_maps):
            # Verify that the child's parent maps are all references to its (expected) parent maps.
            assert all(
                child_map is parent_map
                # safe_zip also verifies that the lists are of the same length.
                for child_map, parent_map in safe_zip(
                    child_chain_map.parents.maps, parent_chain_map.maps
                )
            ), "Child ChainMap does not hold a reference to its parent."

    def _apply(self):
        """
        Applies state updates to self.parent_state.
        This method should not be directly used; use copy_and_apply instead.
        """
        assert self.parent_state is not None
        self._validate_references_of_chain_maps()

        # Apply state updates.
        self.parent_state.cairo_usage = self.cairo_usage
        for child_chain_map, parent_chain_map in zip(self.chain_maps, self.parent_state.chain_maps):
            parent_chain_map.update(child_chain_map.maps[0])

        # Update additional entire block-related information.
        self.parent_state.block_info = self.block_info


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
            block_info=BlockInfo.empty(),
        )

    def to_carried_state(self, ffc: FactFetchingContext) -> CarriedState:
        """
        Returns an unfilled CarriedState. Its contract states should be filled using
        get_filled_carried_state() method.
        """
        return CarriedState.create_unfilled(ffc=ffc, shared_state=self)

    async def get_filled_carried_state(
        self, ffc: FactFetchingContext, state_selector: StateSelectorBase
    ) -> CarriedState:
        # Downcast arguments to application-specific types.
        assert isinstance(state_selector, StateSelector)

        # Fetch required data from DB, according to the state selector.
        contract_states = await self.contract_states.get_leaves(
            ffc=ffc, indices=state_selector.contract_addresses, fact_cls=ContractState
        )
        contract_definitions = await ContractState.fetch_contract_definitions(
            contract_states=contract_states.values(), ffc=ffc
        )

        # Fill carried_state with fetched data.
        contract_carried_states = {
            contract_address: ContractCarriedState(state=contract_state, storage_updates={})
            for contract_address, contract_state in contract_states.items()
        }

        return CarriedState.from_contracts(
            ffc=ffc,
            shared_state=self,
            contract_definitions=contract_definitions,
            contract_states=contract_carried_states,
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

        # Verify the carried states originated from this shared state.
        assert previous_carried_state.shared_state is self
        assert current_carried_state.shared_state is self

        state_objects_logger.debug(
            f"Updating state from previous carried state: {previous_carried_state} "
            f"to current carried state: {current_carried_state}"
        )

        # Update contract storage roots with cached changes.
        updated_contract_states = await gather_in_chunks(
            awaitables=(
                contract_state.update(ffc=ffc)
                for contract_state in current_carried_state.contract_states.values()
            )
        )
        contract_states: typing.ChainMap[int, ContractCarriedState] = ChainMap(
            dict(safe_zip(current_carried_state.contract_states.keys(), updated_contract_states))
        )

        # Apply changes.
        contract_state_modifications = {
            contract_address: contract_carried_state.state
            for contract_address, contract_carried_state in (contract_states.items())
        }
        updated_global_contract_root = await self.contract_states.update(
            ffc=ffc, modifications=list(contract_state_modifications.items())
        )

        return SharedState(
            contract_states=updated_global_contract_root,
            block_info=current_carried_state.block_info,
        )
