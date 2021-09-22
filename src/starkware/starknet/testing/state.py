import copy
from collections import defaultdict
from typing import List, Optional, Union

from starkware.cairo.lang.vm.crypto import async_pedersen_hash_func
from starkware.starknet.business_logic.internal_transaction import (
    InternalDeploy,
    InternalInvokeFunction,
)
from starkware.starknet.business_logic.internal_transaction_interface import (
    TransactionExecutionInfo,
)
from starkware.starknet.business_logic.state import CarriedState, SharedState
from starkware.starknet.business_logic.state_objects import ContractCarriedState, ContractState
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.services.api.contract_definition import ContractDefinition, EntryPointType
from starkware.storage.dict_storage import DictStorage
from starkware.storage.storage import FactFetchingContext


class StarknetState:
    """
    StarkNet testing object. Represents a state of a StarkNet network.

    Example usage:
      starknet = await StarknetState.empty()
      contract_definition = compile_starknet_files([CONTRACT_FILE], debug_info=True)
      contract_address = await starknet.deploy(contract_definition=contract_definition)
      res = await starknet.invoke_raw(
          contract_address=contract_address, selector="func", calldata=[1, 2])
    """

    def __init__(self, state: CarriedState, general_config: StarknetGeneralConfig):
        """
        Constructor. Should not be used directly. Use empty() instead.
        """
        self.state = state
        self.general_config = general_config

    def copy(self) -> "StarknetState":
        """
        Creates a new StarknetState instance with the same state. And modifications to one instance
        would not affect the other.
        """
        return copy.deepcopy(self)

    @classmethod
    async def empty(cls, general_config: Optional[StarknetGeneralConfig] = None) -> "StarknetState":
        """
        Creates a new StarknetState instance.
        """
        if general_config is None:
            general_config = StarknetGeneralConfig()
        ffc = FactFetchingContext(storage=DictStorage(), hash_func=async_pedersen_hash_func)
        empty_contract_state = await ContractState.empty(
            storage_commitment_tree_height=general_config.contract_storage_commitment_tree_height,
            ffc=ffc,
        )
        empty_contract_carried_state = ContractCarriedState(
            state=empty_contract_state, storage_updates={}
        )
        shared_state = await SharedState.empty(ffc=ffc, general_config=general_config)
        state = CarriedState.empty(shared_state=shared_state, ffc=ffc)
        state.contract_states = defaultdict(lambda: copy.deepcopy(empty_contract_carried_state))
        return cls(state=state, general_config=general_config)

    async def deploy(
        self,
        contract_definition: ContractDefinition,
        contract_address: Optional[Union[int, str]] = None,
    ) -> int:
        """
        Deploys a contract. Returns the contract address.

        Args:
        contract_definition - a compiled StarkNet contract returned by compile_starknet_files().
        contract_address - If supplied, a hexadecimal string or an integer representing the contract
          address to use for deploying. Otherwise, the contract address is randomized.
        """
        if contract_address is None:
            contract_address = fields.ContractAddressField.get_random_value()
        if isinstance(contract_address, str):
            contract_address = int(contract_address, 16)
        assert isinstance(contract_address, int)

        tx = InternalDeploy(
            contract_address=contract_address, contract_definition=contract_definition
        )

        with self.state.copy_and_apply() as state_copy:
            await tx.apply_state_updates(state=state_copy, general_config=self.general_config)
        return contract_address

    async def invoke_raw(
        self,
        contract_address: Union[int, str],
        selector: Union[int, str],
        calldata: List[int],
        entry_point_type: EntryPointType = EntryPointType.EXTERNAL,
    ) -> TransactionExecutionInfo:
        """
        Invokes a contract function. Returns the execution info.

        Args:
        contract_address - a hexadecimal string or an integer representing the contract address.
        selector - either a function name or an integer selector for the entrypoint to invoke.
        calldata - a list of integers to pass as calldata to the invoked function.
        """

        if isinstance(contract_address, str):
            contract_address = int(contract_address, 16)
        assert isinstance(contract_address, int)

        if isinstance(selector, str):
            selector = get_selector_from_name(selector)
        assert isinstance(selector, int)

        tx = InternalInvokeFunction(
            contract_address=contract_address,
            entry_point_selector=selector,
            entry_point_type=entry_point_type,
            calldata=calldata,
        )

        with self.state.copy_and_apply() as state_copy:
            return await tx.apply_state_updates(
                state=state_copy, general_config=self.general_config
            )
