import asyncio
import concurrent
import concurrent.futures
import dataclasses
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Set, Tuple, Type, TypeVar, Union

from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.python.utils import from_bytes, to_bytes
from starkware.starkware_utils.commitment_tree.binary_fact_tree import BinaryFactDict
from starkware.starkware_utils.commitment_tree.leaf_fact import LeafFact
from starkware.starkware_utils.commitment_tree.patricia_tree.nodes import EmptyNodeFact
from starkware.starkware_utils.commitment_tree.patricia_tree.patricia_tree import PatriciaTree
from starkware.starkware_utils.validated_dataclass import ValidatedDataclass
from starkware.storage.storage import HASH_BYTES, FactFetchingContext, HashFunctionType


TStorageLeaf = TypeVar("TStorageLeaf", bound="StorageLeaf")


@dataclasses.dataclass(frozen=True)
class StorageLeaf(LeafFact, ValidatedDataclass):
    """
    A class representing a commitment tree leaf in a Cairo contract storage.
    The content of the leaf is a single integer.
    """

    value: int

    assert (
        DEFAULT_PRIME.bit_length() < HASH_BYTES * 8
    ), f"Expecting a field element to fit in a {HASH_BYTES} bytes."

    @classmethod
    def prefix(cls) -> bytes:
        return b"starknet_storage_leaf"

    def serialize(self) -> bytes:
        return to_bytes(self.value)

    def _hash(self, hash_func: HashFunctionType) -> bytes:
        """
        Calculates and returns the leaf hash.
        Note that the return value size needs to be HASH_BYTES.
        """
        if self.is_empty:
            return EmptyNodeFact.EMPTY_NODE_HASH

        return self.serialize()

    @classmethod
    def deserialize(cls: Type[TStorageLeaf], data: bytes) -> TStorageLeaf:
        return cls(value=from_bytes(data))

    @classmethod
    def empty(cls) -> "StorageLeaf":
        return cls(value=0)

    @property
    def is_empty(self) -> bool:
        return self.value == 0


class StarknetStorageInterface(ABC):
    """
    StarkNet storage interface.
    """

    @abstractmethod
    def read(self, address: int) -> int:
        """
        Performs a read operation.
        """

    @abstractmethod
    def write(self, address: int, value: int):
        """
        Performs a write operation.
        """

    @abstractmethod
    def commitment_update(self) -> Tuple[PatriciaTree, BinaryFactDict]:
        """
        Updates the facts storage with the written values.
        Returns the resulting commitment tree and the commitment tree facts required for the Cairo
        commitment tree multi-update function.
        """


class StarknetStorage(StarknetStorageInterface):
    """
    StarkNet storage class.

    Used for caching of read and write operations in a StarkNet contract.
    """

    def __init__(
        self,
        commitment_tree: PatriciaTree,
        ffc: FactFetchingContext,
        pending_modifications: Optional[Dict[int, StorageLeaf]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        """
        Creates a StarkNet storage corresponding to the given 'commitment_tree' and
        'pending_modifications'.
        Updates are done with respect to the given ffc.
        """
        self.ffc = ffc
        self.commitment_tree = commitment_tree
        self.modifications: Dict[int, Union[int, concurrent.futures.Future[int]]] = {}

        # A mapping with the initial storage values, used to override values in the commitment tree
        # and validation of the storage segment.
        self.initial_values: Dict[int, int] = {}
        self.pending_modifications = {} if pending_modifications is None else pending_modifications
        # If StarknetStorage is initialized while running inside executor, the loop must
        # be obtained and passed ahead, as get_running_loop() will raise an exception in that case.
        self.loop = asyncio.get_running_loop() if loop is None else loop

    async def _read_from_commitment_tree_async(self, address: int) -> int:
        assert isinstance(address, int)

        assert (
            0 <= address < 2 ** self.commitment_tree.height
        ), f"The address {address} is out of range."
        leaves = await self.commitment_tree.get_leaves(
            ffc=self.ffc, indices=[address], fact_cls=StorageLeaf
        )

        return leaves[address].value

    def _update_init_value(self, address: int, value: int):
        assert address not in self.initial_values, f"Trying to overwrite initial_values[{address}]."
        self.initial_values[address] = value

    def begin_read(self, address: int):
        """
        Creates a read request with the given address.
        """
        assert isinstance(address, int)
        if address not in self.modifications:
            pending_modification = self.pending_modifications.get(address)
            if pending_modification is None:
                self.modifications[address] = asyncio.run_coroutine_threadsafe(
                    coro=self._read_from_commitment_tree_async(address), loop=self.loop
                )
                return

            value = pending_modification.value
            self._update_init_value(address=address, value=value)
            self.modifications[address] = value

    def end_read(self, address: int) -> int:
        """
        Blocks until the value of the storage in the given address is read.
        """
        value = self.modifications.get(address)
        assert value is not None, "end_read was called without a prior begin_read."
        if isinstance(value, concurrent.futures.Future):
            value = value.result()
            self._update_init_value(address=address, value=value)

        self.modifications[address] = value

        return value

    def read(self, address: int) -> int:
        """
        Performs a read operation.
        """
        self.begin_read(address=address)
        return self.end_read(address=address)

    def write(self, address: int, value: int):
        """
        Writes value to cache.
        """
        assert isinstance(address, int)
        assert isinstance(value, int)

        current_value = self.modifications.get(address)
        # Note that current_value == None is allowed.
        assert not isinstance(
            current_value, concurrent.futures.Future
        ), f"Read operation for address {address} was not finalized using end_read."

        self.modifications[address] = value

    def commitment_update(self) -> Tuple[PatriciaTree, BinaryFactDict]:
        """
        Updates the facts storage with the values written to cache.

        Returns the resulting commitment tree and the commitment tree facts required for the Cairo
        commitment tree multi-update function.
        """
        return asyncio.run_coroutine_threadsafe(
            coro=self.commitment_update_async(), loop=self.loop
        ).result()

    def get_modifications(self) -> Dict[int, StorageLeaf]:
        """
        Returns a dict of modifications that need to be applied to self.commitment_tree.
        """
        modifications = {}
        for (address, value) in self.modifications.items():
            assert isinstance(
                value, int
            ), f"Read operation for address {address} was not finalized using end_read."
            modifications[address] = StorageLeaf(value=value)

        return modifications

    async def commitment_update_async(self) -> Tuple[PatriciaTree, BinaryFactDict]:
        """
        An asynchronous version of commitment_update.
        """
        assert (
            len(self.pending_modifications) == 0
        ), "Cannot perform a commitment tree update when there are pending updates."

        commitment_tree_facts: BinaryFactDict = {}
        commitment_tree = await self.commitment_tree.update(
            ffc=self.ffc,
            modifications=self.get_modifications().items(),
            facts=commitment_tree_facts,
        )

        return commitment_tree, commitment_tree_facts

    def reset_state(self, storage_updates: Dict[int, StorageLeaf]):
        self.pending_modifications.update(storage_updates)
        self.modifications.clear()
        self.initial_values.clear()

    def validate_dict_accesses(self, dict_accesses: List[int]):
        current_values: Dict[int, int] = {}

        assert len(dict_accesses) % 3 == 0, "len(dict_accesses) % DictAccess.SIZE must be 0."

        for i in range(0, len(dict_accesses), 3):
            key, prev_value, new_value = dict_accesses[i : i + 3]
            assert (
                0 <= key < 2 ** self.commitment_tree.height
            ), f"The address {key} is out of range."

            curr_val = current_values.get(key)
            if curr_val is None:
                curr_val = self.initial_values.get(key)
                assert (
                    curr_val is not None
                ), f"Bad dict access at address {key}, prev_value was not read from storage."

            assert (
                curr_val == prev_value
            ), f"""\
Bad dict access at address {key}, expected prev_value to be {curr_val}, found {prev_value}."""

            current_values[key] = new_value

        assert (
            current_values == self.modifications
        ), f"""\
dict_accesses_modificitions = {current_values} != actual modificiation = {self.modifications}."""


class BusinessLogicStarknetStorage(StarknetStorage):
    """
    The StarknetStorage implementation that is used in the transaction-batching phase.
    """

    def __init__(
        self,
        commitment_tree: PatriciaTree,
        ffc: FactFetchingContext,
        pending_modifications: Optional[Dict[int, StorageLeaf]] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        super().__init__(
            commitment_tree=commitment_tree,
            ffc=ffc,
            pending_modifications=pending_modifications,
            loop=loop,
        )

        # Maintain all read request values in chronological order.
        self.read_values: List[int] = []
        self.accessed_addresses: Set[int] = set()

    def read(self, address: int) -> int:
        value = super().read(address=address)
        self.read_values.append(value)
        self.accessed_addresses.add(address)
        return value

    def write(self, address: int, value: int):
        super().write(address=address, value=value)
        self.accessed_addresses.add(address)


class OsStarknetStorage(StarknetStorageInterface):
    """
    The StarknetStorage implementation that is used by the StarkNet OS run in the GpsAmbassador.
    """

    def __init__(
        self,
        commitment_tree: PatriciaTree,
        updated_commitment_tree: PatriciaTree,
        commitment_tree_facts: BinaryFactDict,
    ):
        """
        The constructor is private.
        """
        self.commitment_tree = commitment_tree  # This is the previous commitment tree.

        # The return values of commitment_update, computed at the creation of this object (before
        # entering the CairoRunner run) for optimization.
        self.updated_commitment_tree = updated_commitment_tree
        self.commitment_tree_facts = commitment_tree_facts

    def read(self, address: int) -> int:
        raise NotImplementedError("read() is not implemented in OsStarknetStorage.")

    def write(self, address: int, value: int):
        raise NotImplementedError("write() is not implemented in OsStarknetStorage.")

    def commitment_update(self) -> Tuple[PatriciaTree, BinaryFactDict]:
        return self.updated_commitment_tree, self.commitment_tree_facts

    @classmethod
    async def create(
        cls,
        previous_commitment_tree: PatriciaTree,
        updated_commitment_tree: PatriciaTree,
        ffc: FactFetchingContext,
        accessed_addresses: Set[int],
    ) -> "OsStarknetStorage":
        # Compute commitment tree facts.
        # Get modifications from the given updated commitment tree.
        modifications = await updated_commitment_tree.get_leaves(
            ffc=ffc, indices=accessed_addresses, fact_cls=StorageLeaf
        )
        # Apply these modifications to the previous commitment tree and obtain commitment tree
        # facts.
        commitment_tree_facts: BinaryFactDict = {}
        actual_updated_commitment_tree = await previous_commitment_tree.update(
            ffc=ffc, modifications=modifications.items(), facts=commitment_tree_facts
        )

        assert (
            actual_updated_commitment_tree == updated_commitment_tree
        ), "Inconsistent commitment tree roots."

        return cls(
            commitment_tree=previous_commitment_tree,
            updated_commitment_tree=updated_commitment_tree,
            commitment_tree_facts=commitment_tree_facts,
        )
