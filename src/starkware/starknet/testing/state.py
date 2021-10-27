import copy
from collections import defaultdict
from typing import Dict, List, Optional, Union, cast

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
from starkware.starknet.services.api.gateway.transaction import Deploy, InvokeFunction
from starkware.starknet.services.api.messages import StarknetMessage
from starkware.storage.dict_storage import DictStorage
from starkware.storage.storage import FactFetchingContext

CastableToAddress = Union[str, int]
CastableToAddressSalt = Union[str, int]


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
        # A mapping from L2-to-L1 message hash to its counter.
        self._l2_to_l1_messages: Dict[str, int] = {}
        # A list of all L2-to-L1 messages sent, in chronological order.
        self.l2_to_l1_messages_log: List[StarknetMessage] = []

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
        constructor_calldata: List[int],
        contract_address_salt: Optional[CastableToAddressSalt] = None,
    ) -> int:
        """
        Deploys a contract. Returns the contract address.

        Args:
        contract_definition - a compiled StarkNet contract returned by compile_starknet_files().
        contract_address_salt - If supplied, a hexadecimal string or an integer representing
        the salt to use for deploying. Otherwise, the salt is randomized.
        """

        if contract_address_salt is None:
            contract_address_salt = fields.ContractAddressSalt.get_random_value()
        if isinstance(contract_address_salt, str):
            contract_address_salt = int(contract_address_salt, 16)
        assert isinstance(contract_address_salt, int)

        external_tx = Deploy(
            contract_address_salt=contract_address_salt,
            contract_definition=contract_definition,
            constructor_calldata=constructor_calldata,
        )
        tx = cast(
            InternalDeploy,
            InternalDeploy.from_external(
                external_tx=external_tx, general_config=self.general_config
            ),
        )

        with self.state.copy_and_apply() as state_copy:
            await tx.apply_state_updates(state=state_copy, general_config=self.general_config)

        return tx.contract_address

    async def invoke_raw(
        self,
        contract_address: CastableToAddress,
        selector: Union[int, str],
        calldata: List[int],
        caller_address: int,
        signature: Optional[List[int]] = None,
        entry_point_type: EntryPointType = EntryPointType.EXTERNAL,
    ) -> TransactionExecutionInfo:
        """
        Invokes a contract function. Returns the execution info.

        Args:
        contract_address - a hexadecimal string or an integer representing the contract address.
        selector - either a function name or an integer selector for the entrypoint to invoke.
        calldata - a list of integers to pass as calldata to the invoked function.
        signature - a list of integers to pass as signature to the invoked function.
        """

        if isinstance(contract_address, str):
            contract_address = int(contract_address, 16)
        assert isinstance(contract_address, int)

        if isinstance(selector, str):
            selector = get_selector_from_name(selector)
        assert isinstance(selector, int)

        if signature is None:
            signature = []

        external_tx = InvokeFunction(
            contract_address=contract_address,
            entry_point_selector=selector,
            calldata=calldata,
            signature=signature,
        )
        tx = InternalInvokeFunction._specific_from_external_by_entry_point_type(
            external_tx=external_tx,
            entry_point_type=entry_point_type,
            general_config=self.general_config,
            caller_address=caller_address,
        )

        with self.state.copy_and_apply() as state_copy:
            tx_execution_info = await tx.apply_state_updates(
                state=state_copy, general_config=self.general_config
            )

        for message in tx_execution_info.l2_to_l1_messages:
            starknet_message = StarknetMessage.create_message_to_l1(
                from_address=message.from_address,
                to_address=message.to_address,
                payload=message.payload,
            )
            self.l2_to_l1_messages_log.append(starknet_message)
            message_hash = starknet_message.get_hash()
            self._l2_to_l1_messages[message_hash] = self._l2_to_l1_messages.get(message_hash, 0) + 1

        return tx_execution_info

    def consume_message_hash(self, message_hash: str):
        """
        Consumes the given message hash.
        """
        assert (
            self._l2_to_l1_messages.get(message_hash, 0) > 0
        ), f"Message of hash {message_hash} is fully consumed."

        self._l2_to_l1_messages[message_hash] -= 1
