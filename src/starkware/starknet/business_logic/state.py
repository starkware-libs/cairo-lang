import asyncio
import dataclasses
import logging
from collections import ChainMap, defaultdict
from typing import Dict, MutableMapping, Optional, Set

import marshmallow_dataclass

from services.everest.business_logic.state import (
    CarriedStateBase,
    SharedStateBase,
    StateSelectorBase,
)
from starkware.cairo.lang.vm.cairo_pie import ExecutionResources
from starkware.python.utils import safe_zip
from starkware.starknet.business_logic.state_objects import ContractCarriedState, ContractState
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.storage.starknet_storage import StorageLeaf
from starkware.starkware_utils.commitment_tree.patricia_tree.patricia_tree import PatriciaTree
from starkware.starkware_utils.config_base import Config
from starkware.starkware_utils.validated_dataclass import ValidatedMarshmallowDataclass
from starkware.storage.storage import FactFetchingContext

logger = logging.getLogger(__name__)
state_objects_logger = logging.getLogger(f"{__name__}:state_objects_logger")

ContractCarriedStateMapping = MutableMapping[int, ContractCarriedState]


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


class CarriedState(CarriedStateBase["CarriedState"]):
    """
    A state containing a mapping from contract addresses to their states and the accumulated
    modifications to the contract storage across transactions.

    This will be a sub-state of the total state (SharedState). It is carried and maintained by
    the Batcher, as each pending transaction is applied to it during the attempt to include it in
    a batch. After a batch is created the carried state is applied to the shared state.
    """

    def __init__(
        self,
        parent_state: Optional["CarriedState"],
        shared_state: "SharedState",
        ffc: FactFetchingContext,
        contract_definitions: Dict[bytes, ContractDefinition],
        contract_states: ContractCarriedStateMapping,
        cairo_usage: ExecutionResources,
        output_length: int,
    ):
        """
        Private constructor.
        Should only be called by _create_from_parent_state and create_unfilled class methods.
        """
        super().__init__(parent_state=parent_state)

        # The last committed state; the one this carried state was created from.
        self.shared_state = shared_state

        # A mapping from contract definition hash to contract definition.
        self.contract_definitions: Dict[bytes, ContractDefinition] = contract_definitions

        # A mapping from contract address to its carried state.
        self.contract_states: ContractCarriedStateMapping = contract_states

        # The contract states that will change as a result of transaction application on the state.
        self._updated_contract_states: ContractCarriedStateMapping = {}

        # The accumulated Cairo usage.
        self.cairo_usage: ExecutionResources = cairo_usage

        # Carried state fetches commitment tree leaves from storage during transaction processing.
        self.ffc: FactFetchingContext = ffc

        # Cumulative length of SN OS output (that eventually goes onchain).
        self.output_length = output_length

    @classmethod
    def _create_from_parent_state(cls, parent_state: "CarriedState") -> "CarriedState":
        """
        Instantiates a CarriedState object that acts as proxy to given parent_state.
        """
        carried_state = cls(
            parent_state=parent_state,
            shared_state=parent_state.shared_state,
            ffc=parent_state.ffc,
            contract_definitions=parent_state.contract_definitions,
            contract_states={},
            cairo_usage=parent_state.cairo_usage,
            output_length=parent_state.output_length,
        )
        carried_state.contract_states = ChainMap(
            carried_state._updated_contract_states, parent_state.contract_states
        )

        return carried_state

    @classmethod
    def empty(cls, shared_state: "SharedState", ffc: FactFetchingContext) -> "CarriedState":
        """
        Returns an empty carried state.
        """
        return cls(
            parent_state=None,
            ffc=ffc,
            shared_state=shared_state,
            contract_definitions={},
            contract_states={},
            cairo_usage=ExecutionResources.empty(),
            # Global information that will appear in the output at the end of the OS run:
            # Previous root, new root, L2-to-L1 message segment size, L1-to-L2 message segment size.
            output_length=4,
        )

    @classmethod
    async def create_empty_for_test(
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
                lambda: ContractCarriedState(state=empty_contract_state, storage_updates={})
            ),
        )

    @classmethod
    def from_contracts(
        cls,
        shared_state: "SharedState",
        ffc: FactFetchingContext,
        contract_definitions: Dict[bytes, ContractDefinition],
        contract_states: ContractCarriedStateMapping,
    ) -> "CarriedState":
        """
        Returns a carried state object, containing the given contracts.
        Other members are initialized with the empty object values.
        This is a utility function and should not be used in the regular flow.
        """
        carried_state = cls.empty(ffc=ffc, shared_state=shared_state)
        carried_state.contract_definitions = contract_definitions
        carried_state.contract_states = contract_states

        return carried_state

    @property
    def state_selector(self) -> StateSelector:
        """
        Returns the state selector of this CarriedState containing the contract addresses that
        serve as the commitment tree leaf IDs of the full StarkNet state commitment tree.
        """
        return StateSelector(contract_addresses=set(self.contract_states.keys()))

    def select(self, state_selector: StateSelectorBase) -> "CarriedState":
        """
        Returns a new CarriedState copied from this one after deleting unused commitment tree state
        leaves.
        """
        # Downcast arguments to application-specific types.
        assert isinstance(state_selector, StateSelector)

        selected_contract_states = {
            contract_address: self.contract_states[contract_address]
            for contract_address in state_selector.contract_addresses & self.contract_states.keys()
        }

        return CarriedState(
            parent_state=self.parent_state,
            ffc=self.ffc,
            shared_state=self.shared_state,
            contract_definitions=self.contract_definitions,
            contract_states=selected_contract_states,
            cairo_usage=self.cairo_usage.copy(),
            output_length=self.output_length,
        )

    def _fill_missing(self, other: "CarriedState"):
        """
        Updates this state with the missing entries from another CarriedState instance.
        This is a private method, only to be called from public fill_missing method.
        """
        self.contract_states.update(other.contract_states)
        self.contract_definitions.update(other.contract_definitions)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CarriedState):
            return NotImplemented

        return self.contract_states == other.contract_states

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
        since it is very unlikely contract state will not change throughout a batch.
        """
        raise NotImplementedError

    def _apply(self):
        """
        Applies state updates to self.parent_state.
        This method should not be directly used; use copy_and_apply instead.
        """
        assert self.parent_state is not None

        self.parent_state.contract_states.update(self._updated_contract_states)
        self.parent_state.cairo_usage = self.cairo_usage
        self.parent_state.output_length = self.output_length


@marshmallow_dataclass.dataclass(frozen=True)
class SharedState(SharedStateBase, ValidatedMarshmallowDataclass):
    """
    A class representing a combination of the onchain and offchain state.
    """

    contract_states: PatriciaTree

    @classmethod
    async def empty(cls, ffc: FactFetchingContext, general_config: Config) -> "SharedState":
        """
        Returns an empty state. This is called before creating very first batch.
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

        return cls(contract_states=empty_contract_states)

    def to_carried_state(self, ffc: FactFetchingContext) -> CarriedState:
        """
        Returns an unfilled CarriedState. Its contract states should be filled using
        get_filled_carried_state() method.
        """
        return CarriedState.empty(ffc=ffc, shared_state=self)

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
    ) -> "SharedState":
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
        updated_contract_states = await asyncio.gather(
            *(
                contract_state.update(ffc=ffc)
                for contract_state in current_carried_state.contract_states.values()
            )
        )
        current_carried_state.contract_states = dict(
            safe_zip(current_carried_state.contract_states.keys(), updated_contract_states)
        )

        # Apply changes.
        contract_state_modifications = {
            contract_address: contract_carried_state.state
            for contract_address, contract_carried_state in (
                current_carried_state.contract_states.items()
            )
        }
        updated_global_contract_root = await self.contract_states.update(
            ffc=ffc, modifications=list(contract_state_modifications.items())
        )

        return SharedState(contract_states=updated_global_contract_root)
