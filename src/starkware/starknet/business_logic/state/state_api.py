from abc import ABC, abstractmethod

from services.everest.business_logic.state_api import StateProxy
from starkware.python.utils import to_bytes
from starkware.starknet.business_logic.state.state_api_objects import BlockInfo
from starkware.starknet.definitions import constants, fields
from starkware.starknet.definitions.error_codes import StarknetErrorCode
from starkware.starknet.services.api.contract_class.contract_class import (
    CompiledClass,
    CompiledClassBase,
    DeprecatedCompiledClass,
)
from starkware.starkware_utils.error_handling import StarkException, stark_assert


class StateReader(ABC):
    """
    A read-only API for accessing Starknet global state.
    """

    @abstractmethod
    async def get_compiled_class(self, compiled_class_hash: int) -> CompiledClassBase:
        """
        Returns the compiled class of the given compiled class hash.
        Raises an exception if said class was not declared.
        """

    @abstractmethod
    async def get_compiled_class_hash(self, class_hash: int) -> int:
        """
        Returns the compiled class hash of the given class hash.
        """

    @abstractmethod
    async def get_class_hash_at(self, contract_address: int) -> int:
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

    async def get_compiled_class_by_class_hash(self, class_hash: int) -> CompiledClassBase:
        """
        Returns the compiled class of the given class hash. Handles both class versions.
        """
        compiled_class_hash = await self.get_compiled_class_hash(class_hash=class_hash)
        if compiled_class_hash != 0:
            # The class appears in the class commitment tree, it must be of version > 0.
            compiled_class = await self.get_compiled_class(compiled_class_hash=compiled_class_hash)
            assert isinstance(
                compiled_class, CompiledClass
            ), "Class of version 0 cannot be committed."
        else:
            # The class is not committed; treat it as version 0.
            # Note that 'get_compiled_class' should fail if it's not declared.
            compiled_class = await self.get_compiled_class(compiled_class_hash=class_hash)
            assert isinstance(
                compiled_class, DeprecatedCompiledClass
            ), "Class of version > 0 must be committed."

        return compiled_class


class State(StateProxy, StateReader):
    """
    A class defining the API for accessing Starknet global state.

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
    async def set_compiled_class_hash(self, class_hash: int, compiled_class_hash: int):
        """
        Sets the given compiled class hash under the given class hash.
        """

    async def deploy_contract(self, contract_address: int, class_hash: int):
        """
        Allocates the given address to the given class hash.
        Raises an exception if the address is already assigned;
        meaning: this is a write once action.
        """
        current_class_hash = await self.get_class_hash_at(contract_address=contract_address)
        stark_assert(
            to_bytes(current_class_hash) == constants.UNINITIALIZED_CLASS_HASH,
            code=StarknetErrorCode.CONTRACT_ADDRESS_UNAVAILABLE,
            message=(
                f"Requested contract address {fields.L2AddressField.format(contract_address)} "
                "is unavailable for deployment."
            ),
        )

        await self.set_class_hash_at(contract_address=contract_address, class_hash=class_hash)

    @abstractmethod
    async def set_class_hash_at(self, contract_address: int, class_hash: int):
        """
        Allocates the given address to the given class hash.
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
    def get_compiled_class(self, compiled_class_hash: int) -> CompiledClassBase:
        pass

    @abstractmethod
    def get_compiled_class_hash(self, class_hash: int) -> int:
        pass

    @abstractmethod
    def get_class_hash_at(self, contract_address: int) -> int:
        pass

    @abstractmethod
    def get_nonce_at(self, contract_address: int) -> int:
        pass

    @abstractmethod
    def get_storage_at(self, contract_address: int, key: int) -> int:
        pass

    def get_compiled_class_by_class_hash(self, class_hash: int) -> CompiledClassBase:
        compiled_class_hash = self.get_compiled_class_hash(class_hash=class_hash)
        if compiled_class_hash != 0:
            # The class appears in the class commitment tree, it must be of version > 0.
            compiled_class = self.get_compiled_class(compiled_class_hash=compiled_class_hash)
            assert isinstance(
                compiled_class, CompiledClass
            ), "Class of version 0 cannot be committed."
        else:
            # The class is not committed; treat it as version 0.
            # Note that 'get_compiled_class' should fail if it's not declared.
            compiled_class = self.get_compiled_class(compiled_class_hash=class_hash)
            assert isinstance(
                compiled_class, DeprecatedCompiledClass
            ), "Expected class hash; got compiled class hash."

        return compiled_class


class SyncState(SyncStateReader, StateProxy):
    """
    See State's documentation.
    """

    @property
    @abstractmethod
    def block_info(self) -> BlockInfo:
        pass

    @abstractmethod
    def set_compiled_class_hash(self, class_hash: int, compiled_class_hash: int):
        pass

    def deploy_contract(self, contract_address: int, class_hash: int):
        current_class_hash = self.get_class_hash_at(contract_address=contract_address)
        stark_assert(
            to_bytes(current_class_hash) == constants.UNINITIALIZED_CLASS_HASH,
            code=StarknetErrorCode.CONTRACT_ADDRESS_UNAVAILABLE,
            message=(
                f"Requested contract address {fields.L2AddressField.format(contract_address)} "
                "is unavailable for deployment."
            ),
        )

        self.set_class_hash_at(contract_address=contract_address, class_hash=class_hash)

    @abstractmethod
    def set_class_hash_at(self, contract_address: int, class_hash: int):
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


def get_stark_exception_on_undeclared_contract(class_hash: int) -> StarkException:
    formatted_class_hash = fields.ClassHashIntField.format(class_hash)
    return StarkException(
        code=StarknetErrorCode.UNDECLARED_CLASS,
        message=f"Class with hash {formatted_class_hash} is not declared.",
    )
