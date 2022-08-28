import asyncio
import contextlib
from collections import ChainMap
from typing import Dict, Iterator, List, Mapping, Set, Tuple

from starkware.python.utils import execute_coroutine_threadsafe
from starkware.starknet.business_logic.state.state_api import (
    State,
    StateReader,
    SyncState,
    SyncStateReader,
)
from starkware.starknet.business_logic.state.state_api_objects import BlockInfo
from starkware.starknet.definitions import constants
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starkware_utils.error_handling import stark_assert

StorageEntry = Tuple[int, int]  # (contract_address, key).


class StateSyncifier(SyncState):
    """
    Acts as a synchronous variant of a given (asynchronous) State object.
    Should be used only from within the given loop.
    """

    def __init__(self, async_state: State, loop: asyncio.AbstractEventLoop):
        # State to sychronize.
        self.async_state = async_state

        # Current running event loop; used for running async tasks in a synchronous context.
        self.loop = loop

    @property
    def block_info(self) -> BlockInfo:
        return self.async_state.block_info

    def update_block_info(self, block_info: BlockInfo):
        self.async_state.block_info = block_info

    def get_contract_class(self, class_hash: bytes) -> ContractClass:
        return execute_coroutine_threadsafe(
            coroutine=self.async_state.get_contract_class(class_hash=class_hash), loop=self.loop
        )

    def get_class_hash_at(self, contract_address: int) -> bytes:
        return execute_coroutine_threadsafe(
            coroutine=self.async_state.get_class_hash_at(contract_address=contract_address),
            loop=self.loop,
        )

    def get_nonce_at(self, contract_address: int) -> int:
        return execute_coroutine_threadsafe(
            coroutine=self.async_state.get_nonce_at(contract_address=contract_address),
            loop=self.loop,
        )

    def get_storage_at(self, contract_address: int, key: int) -> int:
        return execute_coroutine_threadsafe(
            coroutine=self.async_state.get_storage_at(contract_address=contract_address, key=key),
            loop=self.loop,
        )

    def set_contract_class(self, class_hash: bytes, contract_class: ContractClass):
        return execute_coroutine_threadsafe(
            coroutine=self.async_state.set_contract_class(
                class_hash=class_hash, contract_class=contract_class
            ),
            loop=self.loop,
        )

    def deploy_contract(self, contract_address: int, class_hash: bytes):
        return execute_coroutine_threadsafe(
            coroutine=self.async_state.deploy_contract(
                class_hash=class_hash, contract_address=contract_address
            ),
            loop=self.loop,
        )

    def increment_nonce(self, contract_address: int):
        return execute_coroutine_threadsafe(
            coroutine=self.async_state.increment_nonce(contract_address=contract_address),
            loop=self.loop,
        )

    def set_storage_at(self, contract_address: int, key: int, value: int):
        return execute_coroutine_threadsafe(
            coroutine=self.async_state.set_storage_at(
                contract_address=contract_address, key=key, value=value
            ),
            loop=self.loop,
        )


class StateCache:
    """
    Holds read and write requests.
    """

    def __init__(self):
        self.contract_classes: Dict[bytes, ContractClass] = {}

        # Reader's cached information.
        self._class_hash_reads: Dict[int, bytes] = {}
        self._nonce_reads: Dict[int, int] = {}
        self._storage_reads: Dict[StorageEntry, int] = {}

        # Writer's cached information.
        self._class_hash_writes: Dict[int, bytes] = {}
        self._nonce_writes: Dict[int, int] = {}
        self._storage_writes: Dict[StorageEntry, int] = {}

        # State view.

        # Mappings from contract address to different attributes.
        self.address_to_class_hash: Mapping[int, bytes] = ChainMap(
            self._class_hash_writes, self._class_hash_reads
        )
        self.address_to_nonce: Mapping[int, int] = ChainMap(self._nonce_writes, self._nonce_reads)
        # Mapping from (contract_address, key) to a value in the contract's storage.
        self.storage_view: Mapping[StorageEntry, int] = ChainMap(
            self._storage_writes, self._storage_reads
        )

    def update_writes_from_other(self, other: "StateCache"):
        self.contract_classes.update(other.contract_classes)
        self._class_hash_writes.update(other._class_hash_writes)
        self._nonce_writes.update(other._nonce_writes)
        self._storage_writes.update(other._storage_writes)

    def update_writes(
        self,
        contract_classes: Mapping[bytes, ContractClass],
        address_to_class_hash: Mapping[int, bytes],
        address_to_nonce: Mapping[int, int],
        storage_updates: Mapping[Tuple[int, int], int],
    ):
        self.contract_classes.update(contract_classes)
        self._class_hash_writes.update(address_to_class_hash)
        self._nonce_writes.update(address_to_nonce)
        self._storage_writes.update(storage_updates)

    def get_accessed_contract_addresses(self) -> Set[int]:
        return {
            *self.address_to_class_hash.keys(),
            *self.address_to_nonce.keys(),
            *[address for address, _key in self.storage_view.keys()],
        }

    def get_accessed_class_hashes(self) -> Set[bytes]:
        return set(self.contract_classes.keys())


class CachedState(State):
    """
    A cached implementation of the State API. See State's documentation.
    """

    def __init__(self, block_info: BlockInfo, state_reader: StateReader):
        self.block_info = block_info
        self.state_reader = state_reader
        self.cache = StateCache()

    def update_block_info(self, block_info: BlockInfo):
        self.block_info = block_info

    async def get_contract_class(self, class_hash: bytes) -> ContractClass:
        if class_hash not in self.cache.contract_classes:
            self.cache.contract_classes[class_hash] = await self.state_reader.get_contract_class(
                class_hash=class_hash
            )

        return self.cache.contract_classes[class_hash]

    async def get_class_hash_at(self, contract_address: int) -> bytes:
        if contract_address not in self.cache.address_to_class_hash:
            class_hash = await self.state_reader.get_class_hash_at(
                contract_address=contract_address
            )
            self.cache._class_hash_reads[contract_address] = class_hash

        return self.cache.address_to_class_hash[contract_address]

    async def get_nonce_at(self, contract_address: int) -> int:
        if contract_address not in self.cache.address_to_nonce:
            self.cache._nonce_reads[contract_address] = await self.state_reader.get_nonce_at(
                contract_address=contract_address
            )

        return self.cache.address_to_nonce[contract_address]

    async def get_storage_at(self, contract_address: int, key: int) -> int:
        address_key_pair = (contract_address, key)
        if address_key_pair not in self.cache.storage_view:
            self.cache._storage_reads[address_key_pair] = await self.state_reader.get_storage_at(
                contract_address=contract_address, key=key
            )

        return self.cache.storage_view[address_key_pair]

    async def set_contract_class(self, class_hash: bytes, contract_class: ContractClass):
        self.cache.contract_classes[class_hash] = contract_class

    async def deploy_contract(self, contract_address: int, class_hash: bytes):
        stark_assert(
            contract_address != 0,
            code=StarknetErrorCode.OUT_OF_RANGE_ADDRESS,
            message=f"Cannot deploy contract at address 0.",
        )

        current_class_hash = await self.get_class_hash_at(contract_address=contract_address)
        stark_assert(
            current_class_hash == constants.UNINITIALIZED_CLASS_HASH,
            code=StarknetErrorCode.CONTRACT_ADDRESS_UNAVAILABLE,
            message=f"Requested contract address {contract_address} is unavailable for deployment.",
        )

        self.cache._class_hash_writes[contract_address] = class_hash

    async def increment_nonce(self, contract_address: int):
        current_nonce = await self.get_nonce_at(contract_address=contract_address)
        self.cache._nonce_writes[contract_address] = current_nonce + 1

    async def set_storage_at(self, contract_address: int, key: int, value: int):
        self.cache._storage_writes[(contract_address, key)] = value

    def _copy(self) -> "CachedState":
        # Note that the reader's cache may be updated by this copy's read requests.
        return CachedState(block_info=self.block_info, state_reader=self)

    def _apply(self, parent: "CachedState"):
        """
        Apply updates to parent state.
        """
        assert self.state_reader is parent, "Current reader expected to be the parent state."

        parent.block_info = self.block_info
        parent.cache.update_writes_from_other(other=self.cache)

    @contextlib.contextmanager
    def copy_and_apply(self: "CachedState") -> Iterator["CachedState"]:
        copied_state = self._copy()
        # The exit logic will not be called in case an exception is raised inside the context.
        yield copied_state
        copied_state._apply(parent=self)  # Apply to self.


class CachedSyncState(SyncState):
    """
    A cached implementation of the SyncState API. See CachedState's documentation.
    """

    def __init__(self, block_info: BlockInfo, state_reader: SyncStateReader):
        self._block_info = block_info
        self.state_reader = state_reader
        self.cache = StateCache()

    @property
    def block_info(self) -> BlockInfo:
        return self._block_info

    def update_block_info(self, block_info: BlockInfo):
        self._block_info = block_info

    def get_contract_class(self, class_hash: bytes) -> ContractClass:
        if class_hash not in self.cache.contract_classes:
            self.cache.contract_classes[class_hash] = self.state_reader.get_contract_class(
                class_hash=class_hash
            )

        return self.cache.contract_classes[class_hash]

    def get_class_hash_at(self, contract_address: int) -> bytes:
        if contract_address not in self.cache.address_to_class_hash:
            self.cache._class_hash_reads[contract_address] = self.state_reader.get_class_hash_at(
                contract_address=contract_address
            )

        return self.cache.address_to_class_hash[contract_address]

    def get_nonce_at(self, contract_address: int) -> int:
        if contract_address not in self.cache.address_to_nonce:
            self.cache._nonce_reads[contract_address] = self.state_reader.get_nonce_at(
                contract_address=contract_address
            )

        return self.cache.address_to_nonce[contract_address]

    def get_storage_at(self, contract_address: int, key: int) -> int:
        address_key_pair = (contract_address, key)
        if address_key_pair not in self.cache.storage_view:
            self.cache._storage_reads[address_key_pair] = self.state_reader.get_storage_at(
                contract_address=contract_address, key=key
            )

        return self.cache.storage_view[address_key_pair]

    def set_contract_class(self, class_hash: bytes, contract_class: ContractClass):
        self.cache.contract_classes[class_hash] = contract_class

    def deploy_contract(self, contract_address: int, class_hash: bytes):
        stark_assert(
            class_hash != constants.UNINITIALIZED_CLASS_HASH,
            code=StarknetErrorCode.OUT_OF_RANGE_ADDRESS,
            message=f"Cannot deploy contract address 0.",
        )

        current_class_hash = self.get_class_hash_at(contract_address=contract_address)
        stark_assert(
            current_class_hash == constants.UNINITIALIZED_CLASS_HASH,
            code=StarknetErrorCode.CONTRACT_ADDRESS_UNAVAILABLE,
            message=f"Requested contract address {contract_address} is unavailable for deployment.",
        )

        self.cache._class_hash_writes[contract_address] = class_hash

    def increment_nonce(self, contract_address: int):
        current_nonce = self.get_nonce_at(contract_address=contract_address)
        self.cache._nonce_writes[contract_address] = current_nonce + 1

    def set_storage_at(self, contract_address: int, key: int, value: int):
        self.cache._storage_writes[(contract_address, key)] = value


class ContractStorageState:
    """
    Defines the API for accessing StarkNet single contract storage state.
    """

    def __init__(self, state: SyncState, contract_address: int):
        self.state = state
        self.contract_address = contract_address

        # Maintain all read request values in chronological order.
        self.read_values: List[int] = []
        self.accessed_keys: Set[int] = set()

    def read(self, address: int) -> int:
        self.accessed_keys.add(address)
        value = self.state.get_storage_at(contract_address=self.contract_address, key=address)
        self.read_values.append(value)

        return value

    def write(self, address: int, value: int):
        self.accessed_keys.add(address)
        self.state.set_storage_at(contract_address=self.contract_address, key=address, value=value)
