from abc import ABC, abstractmethod

from services.everest.business_logic.state_api import StateProxy
from starkware.starknet.business_logic.state.state_api_objects import BlockInfo
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.services.api.contract_class import ContractClass
from starkware.starkware_utils.error_handling import StarkException


class StateReader(ABC):
    """
    A read-only API for accessing StarkNet global state.
    """

    @abstractmethod
    async def get_contract_class(self, class_hash: bytes) -> ContractClass:
        """
        Returns the contract class of the given class hash.
        Raises an exception if said class was not declared.
        """

    @abstractmethod
    async def _get_raw_contract_class(self, class_hash: bytes) -> bytes:
        """
        Returns the raw bytes of the contract class object of the given class hash.
        Raises an exception if said class was not declared.
        """

    @abstractmethod
    async def get_class_hash_at(self, contract_address: int) -> bytes:
        """
        Returns the class hash of the contract class at the given address.
        """

    @abstractmethod
    async def get_nonce_at(self, contract_address: int) -> int:
        """
        Returns the nonce of the given contract instance.
        """

    @abstractmethod
    async def get_storage_at(self, contract_address: int, key: int) -> int:
        """
        Returns the storage value under the given key in the given contract instance.
        """


class State(StateProxy, StateReader):
    """
    A class defining the API for accessing StarkNet global state.

    Reader functionality is injected through dependency, rather than inherited (only the abstract
    API is inherited).
    """

    block_info: BlockInfo
    state_reader: StateReader  # Reader functionality.

    @abstractmethod
    def update_block_info(self, block_info: BlockInfo):
        """
        Updates the block info.
        """

    @abstractmethod
    async def set_contract_class(self, class_hash: bytes, contract_class: ContractClass):
        """
        Sets the given contract class under the given class hash.
        """

    @abstractmethod
    async def deploy_contract(self, contract_address: int, class_hash: bytes):
        """
        Allocates the given address to the given class hash.
        Raises an exception if the address is already assigned;
        meaning: this is a write once action.
        """

    @abstractmethod
    async def increment_nonce(self, contract_address: int):
        """
        Increments the nonce of the given contract instance.
        """

    @abstractmethod
    async def set_storage_at(self, contract_address: int, key: int, value: int):
        """
        Sets the storage value under the given key in the given contract instance.
        """


class SyncStateReader(ABC):
    """
    See StateReader's documentation.
    """

    @abstractmethod
    def get_contract_class(self, class_hash: bytes) -> ContractClass:
        pass

    @abstractmethod
    def _get_raw_contract_class(self, class_hash: bytes) -> bytes:
        pass

    @abstractmethod
    def get_class_hash_at(self, contract_address: int) -> bytes:
        pass

    @abstractmethod
    def get_nonce_at(self, contract_address: int) -> int:
        pass

    @abstractmethod
    def get_storage_at(self, contract_address: int, key: int) -> int:
        pass


class SyncState(SyncStateReader, StateProxy):
    """
    See State's documentation.
    """

    @property
    @abstractmethod
    def block_info(self) -> BlockInfo:
        pass

    @abstractmethod
    def set_contract_class(self, class_hash: bytes, contract_class: ContractClass):
        pass

    @abstractmethod
    def deploy_contract(self, contract_address: int, class_hash: bytes):
        pass

    @abstractmethod
    def increment_nonce(self, contract_address: int):
        pass

    @abstractmethod
    def update_block_info(self, block_info: BlockInfo):
        """
        Updates the block info.
        """

    @abstractmethod
    def set_storage_at(self, contract_address: int, key: int, value: int):
        pass


# Utilities.


def get_stark_exception_on_undeclared_contract(class_hash: bytes) -> StarkException:
    formatted_class_hash = fields.class_hash_from_bytes(class_hash=class_hash)
    return StarkException(
        code=StarknetErrorCode.UNDECLARED_CLASS,
        message=f"Class with hash {formatted_class_hash} is not declared.",
    )
