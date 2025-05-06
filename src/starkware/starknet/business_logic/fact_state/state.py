import logging
from dataclasses import field
from typing import Any, Callable, Dict, Mapping, MutableMapping, Optional, Set, Tuple, Type, TypeVar

import marshmallow
import marshmallow_dataclass

from services.everest.business_logic.state import (
    CarriedStateBase,
    EverestStateDiff,
    SharedStateBase,
    StateSelectorBase,
)
from starkware.cairo.lang.vm.crypto import poseidon_hash_many
from starkware.python.utils import (
    from_bytes,
    gather_in_chunks,
    safe_zip,
    subtract_mappings,
    to_bytes,
)
from starkware.starknet.business_logic.fact_state.contract_class_objects import (
    ContractClassLeaf,
    get_ffc_for_contract_class_facts,
)
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
from starkware.starknet.core.aggregator.output_parser import ContractChanges, OsStateDiff
from starkware.starknet.definitions import constants, fields
from starkware.starknet.definitions.data_availability_mode import DataAvailabilityMode
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starkware_utils.commitment_tree.binary_fact_tree import BinaryFactDict
from starkware.starkware_utils.commitment_tree.patricia_tree.patricia_tree import PatriciaTree
from starkware.starkware_utils.config_base import Config
from starkware.storage.storage import DBObject, FactFetchingContext, IndexedDBObject, Storage

logger = logging.getLogger(__name__)
state_objects_logger = logging.getLogger(f"{__name__}:state_objects_logger")

ContractCarriedStateMapping = MutableMapping[int, ContractCarriedState]

TStateDiff = TypeVar("TStateDiff", bound="StateDiff")


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
                contract_state_root=shared_state.contract_states,
                contract_class_root=shared_state.contract_classes,
                ffc=ffc,
                contract_class_storage=ffc.storage,
            ),
            compiled_class_cache={},
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
        raise NotImplementedError("state_selector() is not implemented on Starknet CarriedState.")

    def select(self, state_selector: StateSelectorBase) -> "CarriedState":
        raise NotImplementedError("select() is not implemented on Starknet CarriedState.")

    def _fill_missing(self, other: "CarriedState"):
        raise NotImplementedError("_fill_missing() is not implemented on Starknet CarriedState.")

    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    def subtract_merkle_facts(self, previous_state: "CarriedState") -> "CarriedState":
        """
        Subtraction of contract states from current carried state to previous one is unnecessary,
        since it is very unlikely contract state will not change throughout a block.
        """
        raise NotImplementedError(
            "subtract_merkle_facts() is not implemented on Starknet CarriedState."
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
    # Leaf addresses are class hashes; leaf values contain compiled class hashes.
    contract_classes: Optional[PatriciaTree]
    block_info: BlockInfo

    @property
    def state_version(self) -> int:
        return constants.GLOBAL_STATE_VERSION

    @classmethod
    async def create_empty_contract_states(cls, ffc: FactFetchingContext) -> PatriciaTree:
        """
        Returns an empty contract state tree.
        """
        empty_contract_state = await ContractState.empty(
            storage_commitment_tree_height=constants.CONTRACT_STATES_COMMITMENT_TREE_HEIGHT,
            ffc=ffc,
        )
        return await PatriciaTree.empty_tree(
            ffc=ffc,
            height=constants.CONTRACT_ADDRESS_BITS,
            leaf_fact=empty_contract_state,
        )

    @classmethod
    async def create_empty_contract_class_tree(cls, ffc: FactFetchingContext) -> PatriciaTree:
        """
        Returns an empty contract class tree.
        """
        return await PatriciaTree.empty_tree(
            ffc=ffc,
            height=constants.COMPILED_CLASS_HASH_COMMITMENT_TREE_HEIGHT,
            leaf_fact=ContractClassLeaf.empty(),
        )

    @classmethod
    async def empty(cls, ffc: FactFetchingContext, general_config: Config) -> "SharedState":
        """
        Returns an empty state. This is called before creating very first block.
        """
        # Downcast arguments to application-specific types.
        assert isinstance(general_config, StarknetGeneralConfig)

        empty_contract_states = await cls.create_empty_contract_states(ffc=ffc)
        empty_contract_classes = await cls.create_empty_contract_class_tree(ffc=ffc)

        return cls(
            contract_states=empty_contract_states,
            contract_classes=empty_contract_classes,
            block_info=BlockInfo.empty(sequencer_address=general_config.sequencer_address),
        )

    async def get_contract_class_tree(self, ffc: FactFetchingContext) -> PatriciaTree:
        """
        Returns the state's contract class Patricia tree if it exists;
        Otherwise returns an empty tree.
        """
        return (
            self.contract_classes
            if self.contract_classes is not None
            else await self.create_empty_contract_class_tree(ffc=ffc)
        )

    def get_global_state_root(self) -> int:
        """
        Returns the global state root.
        If both the contract class and contract state trees are empty, the global root is set to 0.
        If no contract class state exists or if it is empty, the global state root is equal to the
        contract state root (for backward compatibility);
        Otherwise, the global root is obtained by:
            global_root =  H(state_version, contract_state_root, contract_class_root).
        """
        contract_states_root = self.contract_states.root
        contract_classes_root = (
            self.contract_classes.root if self.contract_classes is not None else to_bytes(0)
        )

        if contract_states_root == to_bytes(0) and contract_classes_root == to_bytes(0):
            # The shared state is empty.
            return 0

        # Return H(contract_state_root, contract_class_root, state_version).
        hash_value = poseidon_hash_many(
            [
                self.state_version,
                from_bytes(contract_states_root),
                from_bytes(contract_classes_root),
            ]
        )
        return hash_value

    def to_carried_state(self, ffc: FactFetchingContext) -> CarriedState:
        state = CachedState(
            block_info=self.block_info,
            state_reader=PatriciaStateReader(
                contract_state_root=self.contract_states,
                contract_class_root=self.contract_classes,
                ffc=ffc,
                contract_class_storage=ffc.storage,
            ),
        )
        return CarriedState(parent_state=None, state=state)

    async def get_filled_carried_state(
        self, ffc: FactFetchingContext, state_selector: StateSelectorBase
    ) -> CarriedState:
        raise NotImplementedError(
            "get_filled_carried_state() is not implemented on Starknet SharedState."
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
            class_hash_to_compiled_class_hash=state_cache._compiled_class_hash_writes,
            storage_updates=to_state_diff_storage_mapping(
                storage_writes=state_cache._storage_writes
            ),
            block_info=current_carried_state.state.block_info,
        )

    async def apply_updates(
        self,
        ffc: FactFetchingContext,
        address_to_class_hash: Mapping[int, int],
        address_to_nonce: Mapping[int, int],
        class_hash_to_compiled_class_hash: Mapping[int, int],
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
        logger.info(f"Updating contract state tree with {len(accessed_addresses)} modifications...")
        updated_global_contract_root = await self.contract_states.update_efficiently(
            ffc=ffc, modifications=list(safe_zip(accessed_addresses, updated_contract_states))
        )

        ffc_for_contract_class = get_ffc_for_contract_class_facts(ffc=ffc)
        updated_contract_classes: Optional[PatriciaTree] = None
        if self.contract_classes is not None:
            logger.info(
                f"Updating contract class tree with {len(class_hash_to_compiled_class_hash)} "
                "modifications..."
            )
            updated_contract_classes = await self.contract_classes.update_efficiently(
                ffc=ffc_for_contract_class,
                modifications=[
                    (key, ContractClassLeaf.create(compiled_class_hash=value))
                    for key, value in class_hash_to_compiled_class_hash.items()
                ],
            )
        else:
            assert (
                len(class_hash_to_compiled_class_hash) == 0
            ), "contract_classes must be concrete before update."

        return SharedState(
            contract_states=updated_global_contract_root,
            contract_classes=updated_contract_classes,
            block_info=block_info,
        )

    async def fetch_all_witnesses(
        self,
        cached_ffc: FactFetchingContext,
        state_diff: "StateDiff",
        get_leaves: bool,
    ):
        """
        Fetches the necessary witnesses from storage to update the state with the provided diff.
        """
        address_to_class_hash = state_diff.address_to_class_hash
        address_to_nonce = state_diff.nonces.get(DataAvailabilityMode.L1, {})
        class_hash_to_compiled_class_hash = state_diff.declared_classes
        storage_updates = state_diff.storage_updates.get(DataAvailabilityMode.L1, {})

        accessed_addresses = (
            address_to_class_hash.keys() | address_to_nonce.keys() | storage_updates.keys()
        )

        # Fetch global tree's witnesses.
        contract_states = await self.contract_states.fetch_witnesses(
            ffc=cached_ffc,
            sorted_leaf_indices=sorted(accessed_addresses),
            fact_cls=ContractState,
            empty_leaf=await ContractState.empty(
                storage_commitment_tree_height=constants.CONTRACT_STATES_COMMITMENT_TREE_HEIGHT,
                ffc=cached_ffc,
            ),
        )

        # Fetch classes tree's witnesses.
        classes_tree_awaitable = (
            [
                self.contract_classes.fetch_witnesses(
                    ffc=cached_ffc,
                    sorted_leaf_indices=sorted(class_hash_to_compiled_class_hash.keys()),
                    fact_cls=ContractClassLeaf if get_leaves else None,
                    empty_leaf=ContractClassLeaf.empty(),
                )
            ]
            if self.contract_classes is not None
            else []
        )

        await gather_in_chunks(
            awaitables=[
                contract_states[address].fetch_storage_witnesses(
                    ffc=cached_ffc, updates=updates, get_leaves=get_leaves
                )
                for address, updates in storage_updates.items()
            ]
            + classes_tree_awaitable
        )


@marshmallow_dataclass.dataclass(frozen=True)
class StateDiff(EverestStateDiff, DBObject):
    """
    Holds changes induced on Starknet state.
    """

    address_to_class_hash: Mapping[int, int] = field(metadata=fields.address_to_class_hash_metadata)
    nonces: Mapping[DataAvailabilityMode, Mapping[int, int]] = field(
        metadata=fields.data_availability_mode_to_nonces_metadata
    )
    storage_updates: Mapping[DataAvailabilityMode, Mapping[int, Mapping[int, int]]] = field(
        metadata=fields.data_availability_mode_to_storage_updates_metadata
    )
    declared_classes: Mapping[int, int] = field(
        metadata=fields.state_diff_declared_classes_metadata
    )
    # The block after this StateDiff is applied.
    block_info: BlockInfo

    @marshmallow.pre_load
    def backward_compatibility_before_data_availability_modes(
        self, data: Dict[str, Any], many: bool, **kwargs
    ) -> Dict[str, Any]:
        """
        Backward compatibility for state diffs that were created before the introduction of data
        availability modes.
        """
        if "address_to_nonce" in data.keys():
            data["nonces"] = {DataAvailabilityMode.L1.name: data.pop("address_to_nonce")}
            data["storage_updates"] = {DataAvailabilityMode.L1.name: data.pop("storage_updates")}

            assert "declared_classes" not in data.keys()
            if "class_hash_to_compiled_class_hash" in data.keys():
                data["declared_classes"] = data.pop("class_hash_to_compiled_class_hash")
            else:
                # Older versions of the state diff did not have this field.
                data["declared_classes"] = {}

        return data

    @classmethod
    def empty(cls: Type[TStateDiff], block_info: BlockInfo) -> TStateDiff:
        """
        Returns an empty state diff object relative to the given block info.
        """
        return cls(
            address_to_class_hash={},
            nonces={},
            storage_updates={},
            declared_classes={},
            block_info=block_info,
        )

    async def write(self, storage: Storage, batch_id: int) -> bytes:
        """
        Writes the state diff to the storage under the given batch_id.
        Returns the key suffix (serialized batch_id).
        """
        suffix = str(batch_id).encode("ascii")
        await self.set(storage=storage, suffix=suffix)
        return suffix

    @classmethod
    def create_l1_da_mode(
        cls: Type[TStateDiff],
        address_to_class_hash: Mapping[int, int],
        nonces: Mapping[int, int],
        storage_updates: Mapping[int, Mapping[int, int]],
        declared_classes: Mapping[int, int],
        block_info: BlockInfo,
    ) -> TStateDiff:
        return cls(
            address_to_class_hash=address_to_class_hash,
            nonces={DataAvailabilityMode.L1: nonces},
            storage_updates={DataAvailabilityMode.L1: storage_updates},
            declared_classes=declared_classes,
            block_info=block_info,
        )

    @classmethod
    def from_cached_state(cls: Type[TStateDiff], cached_state: CachedState) -> TStateDiff:
        state_cache = cached_state.cache
        storage_updates = to_state_diff_storage_mapping(
            storage_writes=subtract_mappings(
                state_cache._storage_writes, state_cache._storage_initial_values
            )
        )
        nonces = subtract_mappings(state_cache._nonce_writes, state_cache._nonce_initial_values)
        address_to_class_hash = subtract_mappings(
            state_cache._class_hash_writes, state_cache._class_hash_initial_values
        )
        declared_classes = subtract_mappings(
            state_cache._compiled_class_hash_writes, state_cache._compiled_class_hash_initial_values
        )
        return cls(
            address_to_class_hash=address_to_class_hash,
            nonces={DataAvailabilityMode.L1: nonces} if len(nonces) > 0 else {},
            storage_updates=(
                {DataAvailabilityMode.L1: storage_updates} if len(storage_updates) > 0 else {}
            ),
            declared_classes=declared_classes,
            block_info=cached_state.block_info,
        )

    def to_cached_state(self, state_reader: StateReader) -> CachedState:
        cached_state = CachedState(block_info=self.block_info, state_reader=state_reader)
        cached_state.cache.set_initial_values(
            address_to_class_hash=self.address_to_class_hash,
            address_to_nonce=self.nonces.get(DataAvailabilityMode.L1, {}),
            class_hash_to_compiled_class_hash=self.declared_classes,
            storage_updates=to_cached_state_storage_mapping(
                storage_updates=self.storage_updates.get(DataAvailabilityMode.L1, {})
            ),
        )

        return cached_state

    def squash(self, other: "StateDiff") -> "StateDiff":
        address_to_class_hash = {**self.address_to_class_hash, **other.address_to_class_hash}
        declared_classes = {**self.declared_classes, **other.declared_classes}
        nonces: Dict[DataAvailabilityMode, Dict[int, int]] = {}
        storage_updates: Dict[DataAvailabilityMode, Dict[int, Dict[int, int]]] = {}
        for data_availability_mode in self.nonces.keys() | other.nonces.keys():
            nonces[data_availability_mode] = {
                **self.nonces.get(data_availability_mode, {}),
                **other.nonces.get(data_availability_mode, {}),
            }
        for data_availability_mode in self.storage_updates.keys() | other.storage_updates.keys():
            storage_updates[data_availability_mode] = {}
            self_storage_updates = self.storage_updates.get(data_availability_mode, {})
            other_storage_updates = other.storage_updates.get(data_availability_mode, {})
            for address in self_storage_updates.keys() | other_storage_updates.keys():
                storage_updates[data_availability_mode][address] = {
                    **self_storage_updates.get(address, {}),
                    **other_storage_updates.get(address, {}),
                }
        self.block_info.validate_legal_progress(next_block_info=other.block_info)

        return StateDiff(
            address_to_class_hash=address_to_class_hash,
            nonces=nonces,
            declared_classes=declared_classes,
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
            address_to_nonce=self.nonces.get(DataAvailabilityMode.L1, {}),
            class_hash_to_compiled_class_hash=self.declared_classes,
            storage_updates=self.storage_updates.get(DataAvailabilityMode.L1, {}),
            block_info=self.block_info,
        )

    def get_os_encoded_length(self) -> int:
        """
        Returns the length of the OS encoded representation of the state diff.
        See src/starkware/starknet/core/os/state/output.cairo.
        """
        return len(self.to_os_state_diff().encode())

    def get_marginal_os_encoded_length(
        self: TStateDiff, previous_state_diff: Optional[TStateDiff]
    ) -> int:
        """
        Returns the marginal addition of self to the given state diff's length.

        E.g., the following are equivalent:
          * (a + b).get_os_encoded_length()
          * a.get_os_encoded_length() + b.get_marginal_os_encoded_length(a)
        """
        if previous_state_diff is None:
            return self.get_os_encoded_length()

        pre_squash_size = previous_state_diff.get_os_encoded_length()
        post_squash_size = previous_state_diff.squash(other=self).get_os_encoded_length()
        return post_squash_size - pre_squash_size

    def to_os_state_diff(self, alias_storage: Optional[Dict[int, int]] = None) -> OsStateDiff:
        self.assert_l1_da_mode()

        key_sort_func: Optional[Callable[[int], int]] = None
        item_sort_func: Optional[Callable[[Tuple[int, int]], int]] = None
        if alias_storage is not None:
            alias_to_key = {value: key for key, value in alias_storage.items()}
            key_sort_func = lambda x: (
                x if x < constants.INITIAL_AVAILABLE_ALIAS else alias_to_key[x]
            )
            item_sort_func = lambda item: (
                item[0] if item[0] < constants.INITIAL_AVAILABLE_ALIAS else alias_to_key[item[0]]
            )

        nonces = self.nonces.get(DataAvailabilityMode.L1, {})
        storage_updates = self.storage_updates.get(DataAvailabilityMode.L1, {})
        modified_contracts = sorted(
            self.address_to_class_hash.keys() | nonces.keys() | storage_updates.keys(),
            key=key_sort_func,
        )
        return OsStateDiff(
            contracts=[
                ContractChanges(
                    addr=addr,
                    new_nonce=nonces.get(addr, None),
                    new_class_hash=self.address_to_class_hash.get(addr, None),
                    storage_changes=[
                        (key, (None, value))
                        for key, value in sorted(
                            storage_updates.get(addr, {}).items(),
                            key=(
                                None
                                if addr <= constants.MAX_NON_COMPRESSED_CONTRACT_ADDRESS
                                else item_sort_func
                            ),
                        )
                    ],
                    # Only relevant for `full_output` mode.
                    prev_nonce=None,
                    prev_class_hash=None,
                )
                for addr in modified_contracts
            ],
            classes=[
                (class_hash, (None, compiled_class_hash))
                for class_hash, compiled_class_hash in sorted(self.declared_classes.items())
            ],
        )

    @classmethod
    def from_os_state_diff(
        cls: Type[TStateDiff], os_state_diff: OsStateDiff, block_info: BlockInfo
    ) -> TStateDiff:
        contracts = os_state_diff.contracts
        return cls.create_l1_da_mode(
            address_to_class_hash={
                contract.addr: contract.new_class_hash
                for contract in contracts
                if contract.new_class_hash is not None
            },
            nonces={
                contract.addr: contract.new_nonce
                for contract in contracts
                if contract.new_nonce is not None
            },
            storage_updates={
                contract.addr: {key: value for key, (_prev, value) in contract.storage_changes}
                for contract in contracts
                if len(contract.storage_changes) > 0
            },
            declared_classes={
                class_hash: compiled_class_hash
                for class_hash, (_prev, compiled_class_hash) in os_state_diff.classes
            },
            block_info=block_info,
        )

    def assert_l1_da_mode(self):
        supported_da_modes = {DataAvailabilityMode.L1}
        unsupported_da_modes = (
            set(self.nonces.keys() | self.storage_updates.keys()) - supported_da_modes
        )
        assert len(unsupported_da_modes) == 0, f"Unsupported DA modes: {unsupported_da_modes}."

    def gather_accessed_aliases(self) -> Set[int]:
        """
        Gather the accessed leaves in the aliases contract.
        """
        accessed_alias_contract_keys = set([constants.ALIAS_COUNTER_STORAGE_KEY])
        accessed_alias_contract_keys.update(
            {
                address
                for address in (
                    self.address_to_class_hash.keys()
                    | self.nonces.get(DataAvailabilityMode.L1, {}).keys()
                    | self.storage_updates.get(DataAvailabilityMode.L1, {}).keys()
                )
                if address >= constants.INITIAL_AVAILABLE_ALIAS
            }
        )
        for address, storge_updates in self.storage_updates.get(
            DataAvailabilityMode.L1, {}
        ).items():
            if address > constants.MAX_NON_COMPRESSED_CONTRACT_ADDRESS:
                accessed_alias_contract_keys.update(
                    {
                        storage_key
                        for storage_key in storge_updates.keys()
                        if storage_key >= constants.INITIAL_AVAILABLE_ALIAS
                    }
                )
        return accessed_alias_contract_keys

    @classmethod
    def from_compressed_state_diff(
        cls, compressed_state_diff: "CompressedStateDiff"
    ) -> "StateDiff":
        return StateDiff(
            address_to_class_hash=compressed_state_diff.address_to_class_hash,
            nonces=compressed_state_diff.nonces,
            storage_updates=compressed_state_diff.storage_updates,
            declared_classes=compressed_state_diff.declared_classes,
            block_info=compressed_state_diff.block_info,
        )


@marshmallow_dataclass.dataclass(frozen=True)
class CompressedStateDiff(StateDiff, IndexedDBObject):
    """
    A stateful compressed state diff - the contract addresses and the storage keys are replaced with
    aliases.
    """

    def decompress(self, alias_storage: Mapping[int, int]) -> StateDiff:
        """
        Decompresses a stateful compressed state diff by the alias storage state.
        """
        reversed_alias_storage = {value: key for key, value in alias_storage.items()}

        def restore_from_alias(alias):
            if alias < constants.INITIAL_AVAILABLE_ALIAS:
                return alias
            return reversed_alias_storage[alias]

        address_to_class_hash = {
            restore_from_alias(alias=alias): class_hash
            for alias, class_hash in self.address_to_class_hash.items()
        }

        nonces = {
            data_availability_mode: {
                restore_from_alias(alias=alias): nonce for alias, nonce in nonce_mapping.items()
            }
            for data_availability_mode, nonce_mapping in self.nonces.items()
        }

        storage_updates: MutableMapping[
            DataAvailabilityMode, MutableMapping[int, Mapping[int, int]]
        ] = {}
        for (
            data_availability_mode,
            storage_updates_mapping,
        ) in self.storage_updates.items():
            storage_updates[data_availability_mode] = {}
            for contract_alias, storage_mapping in storage_updates_mapping.items():
                contract_address = restore_from_alias(alias=contract_alias)
                if contract_address <= constants.MAX_NON_COMPRESSED_CONTRACT_ADDRESS:
                    storage_updates[data_availability_mode][contract_address] = storage_mapping
                else:
                    storage_updates[data_availability_mode][contract_address] = {
                        restore_from_alias(alias=storage_alias): value
                        for storage_alias, value in storage_mapping.items()
                    }

        return StateDiff(
            address_to_class_hash=address_to_class_hash,
            nonces=nonces,
            storage_updates=storage_updates,
            declared_classes=self.declared_classes,
            block_info=self.block_info,
        )


@marshmallow_dataclass.dataclass(frozen=True)
class DeprecatedStateDiff(EverestStateDiff, DBObject):
    """
    Holds changes induced on Starknet state.

    BACKWARD-COMPATIBILITY
    ----------------------
    This class is used to support the old state diff format when communicating with the
    blockifier.
    """

    address_to_class_hash: Mapping[int, int] = field(metadata=fields.address_to_class_hash_metadata)
    address_to_nonce: Mapping[int, int] = field(metadata=fields.address_to_nonce_metadata)
    class_hash_to_compiled_class_hash: Mapping[int, int] = field(
        metadata=fields.state_diff_declared_classes_metadata
    )
    storage_updates: Mapping[int, Mapping[int, int]] = field(
        metadata=fields.storage_updates_metadata
    )
    block_info: BlockInfo

    @classmethod
    def from_new_state_diff(cls, state_diff: StateDiff) -> "DeprecatedStateDiff":
        return cls(
            address_to_class_hash=state_diff.address_to_class_hash,
            address_to_nonce=state_diff.nonces.get(DataAvailabilityMode.L1, {}),
            class_hash_to_compiled_class_hash=state_diff.declared_classes,
            storage_updates=state_diff.storage_updates.get(DataAvailabilityMode.L1, {}),
            block_info=state_diff.block_info,
        )

    def squash(self, other: "DeprecatedStateDiff") -> "DeprecatedStateDiff":
        raise NotImplementedError("squash is not implemented for {type(self).__name__}.")

    async def commit(
        self, ffc: FactFetchingContext, previous_state: SharedStateBase
    ) -> SharedState:
        raise NotImplementedError("commit is not implemented for {type(self).__name__}.")
