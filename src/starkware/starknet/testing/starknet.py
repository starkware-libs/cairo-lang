import copy
from typing import List, Optional, Union

from starkware.starknet.business_logic.execution.objects import TransactionExecutionInfo
from starkware.starknet.business_logic.transaction.objects import (
    InternalDeployAccount,
    InternalL1Handler,
)
from starkware.starknet.core.os.contract_class.deprecated_class_hash import (
    compute_deprecated_class_hash,
)
from starkware.starknet.core.test_contract.test_utils import get_deprecated_compiled_class
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.public.abi import get_selector_from_name
from starkware.starknet.services.api.contract_class.contract_class import DeprecatedCompiledClass
from starkware.starknet.services.api.messages import StarknetMessageToL1
from starkware.starknet.testing.contract import DeclaredClass, StarknetContract
from starkware.starknet.testing.contract_utils import (
    execution_info_to_call_info,
    gather_deprecated_compiled_class,
    get_deprecated_compiled_class_abi,
)
from starkware.starknet.testing.state import CastableToAddress, CastableToAddressSalt, StarknetState
from starkware.starknet.testing.test_utils import create_internal_deploy_tx_for_testing


class Starknet:
    """
    A high level interface to a StarkNet state object.
    Example:
      starknet = await Starknet.empty()
      contract = await starknet.deploy('contract.cairo')
      await contract.foo(a=1, b=[2, 3]).execute()
    """

    def __init__(self, state: StarknetState):
        self.state = state

        # l1_to_l2_nonce starts from 2**128 to avoid nonce collisions with
        # messages that were sent using starkware.starknet.testing.postman.Postman.
        self.l1_to_l2_nonce = 2**128

    @classmethod
    async def empty(cls, general_config: Optional[StarknetGeneralConfig] = None) -> "Starknet":
        return Starknet(state=await StarknetState.empty(general_config=general_config))

    def copy(self) -> "Starknet":
        return copy.deepcopy(self)

    async def declare(
        self,
        source: Optional[str] = None,
        contract_class: Optional[DeprecatedCompiledClass] = None,
        cairo_path: Optional[List[str]] = None,
        disable_hint_validation: bool = False,
    ) -> DeclaredClass:
        """
        Declares a DeprecatedCompiledClass in the StarkNet network.
        Returns the class hash and the ABI of the contract.
        """
        contract_class = gather_deprecated_compiled_class(
            source=source,
            contract_class=contract_class,
            cairo_path=cairo_path,
            disable_hint_validation=disable_hint_validation,
        )
        class_hash, _ = await self.state.declare(contract_class=contract_class)
        assert class_hash is not None
        return DeclaredClass(
            class_hash=class_hash,
            abi=get_deprecated_compiled_class_abi(contract_class=contract_class),
        )

    async def deploy(
        self,
        source: Optional[str] = None,
        contract_class: Optional[DeprecatedCompiledClass] = None,
        contract_address_salt: Optional[CastableToAddressSalt] = None,
        cairo_path: Optional[List[str]] = None,
        constructor_calldata: Optional[List[int]] = None,
        disable_hint_validation: bool = False,
    ) -> StarknetContract:
        contract_class = gather_deprecated_compiled_class(
            source=source,
            contract_class=contract_class,
            cairo_path=cairo_path,
            disable_hint_validation=disable_hint_validation,
        )
        address, execution_info = await self.state.deploy(
            contract_class=contract_class,
            contract_address_salt=contract_address_salt,
            constructor_calldata=[] if constructor_calldata is None else constructor_calldata,
        )

        abi = get_deprecated_compiled_class_abi(contract_class=contract_class)
        deploy_call_info = execution_info_to_call_info(execution_info=execution_info, abi=abi)
        return StarknetContract(
            state=self.state,
            abi=abi,
            contract_address=address,
            deploy_call_info=deploy_call_info,
        )

    def consume_message_from_l2(self, from_address: int, to_address: int, payload: List[int]):
        """
        Mocks the L1 contract function consumeMessageFromL2.
        """
        starknet_message = StarknetMessageToL1(
            from_address=from_address,
            to_address=to_address,
            payload=payload,
        )
        self.state.consume_message_hash(message_hash=starknet_message.get_hash())

    async def send_message_to_l2(
        self,
        from_address: int,
        to_address: CastableToAddress,
        selector: Union[int, str],
        payload: List[int],
        max_fee: int = 0,
        nonce: Optional[int] = None,
        paid_fee_on_l1: Optional[int] = None,
    ) -> TransactionExecutionInfo:
        """
        Mocks the L1 contract function sendMessageToL2.

        Takes an optional nonce paramater to force a specific nonce, this
        should only be used by the Postman class.
        """
        if isinstance(to_address, str):
            to_address = int(to_address, 16)
        assert isinstance(to_address, int)

        if isinstance(selector, str):
            selector = get_selector_from_name(selector)
        assert isinstance(selector, int)

        if nonce is None:
            nonce = self.l1_to_l2_nonce
            self.l1_to_l2_nonce += 1

        tx = InternalL1Handler.create(
            contract_address=to_address,
            entry_point_selector=selector,
            calldata=[from_address, *payload],
            nonce=nonce,
            chain_id=self.state.general_config.chain_id.value,
            paid_fee_on_l1=paid_fee_on_l1,
        )

        return await self.state.execute_tx(tx=tx)

    async def deploy_mock_account(self) -> int:
        """
        Declares and deploys a mock/dummy account contract and returns its address.
        """
        # Declare the dummy_account contract class.
        dummy_account_contract_class = get_deprecated_compiled_class("dummy_account")
        await self.declare(contract_class=dummy_account_contract_class)
        general_config = self.state.general_config
        salt = fields.ContractAddressSalt.get_random_value()
        # Deploy the dummy_account contract.
        deploy_account_tx = InternalDeployAccount.create(
            class_hash=compute_deprecated_class_hash(contract_class=dummy_account_contract_class),
            constructor_calldata=[],
            contract_address_salt=salt,
            nonce=0,
            max_fee=0,
            version=general_config.tx_version,
            chain_id=general_config.chain_id.value,
            signature=[],
        )

        await self.state.execute_tx(tx=deploy_account_tx)
        return deploy_account_tx.sender_address

    async def deploy_contract_from(
        self,
        contract_class: DeprecatedCompiledClass,
        constructor_calldata: List[int],
        deploy_from: int,
        nonce: int,
        signature: Optional[List[int]] = None,
    ) -> StarknetContract:
        """
        Declares and deploys a contract from a given address.
        Note: deploy_from is currently assumed to be controlled by a mock account, so signing is not
        required.
        """
        # Declare contract class.
        await self.declare(contract_class=contract_class)
        # Construct the deployment tx.
        salt = fields.ContractAddressSalt.get_random_value()
        deployed_contract_address, deploy_tx = create_internal_deploy_tx_for_testing(
            account_address=deploy_from,
            contract_class=contract_class,
            constructor_calldata=constructor_calldata,
            salt=salt,
            max_fee=0,
            nonce=nonce,
            signature=signature,
        )
        # Execute the deployment tx.
        execution_info = await self.state.execute_tx(tx=deploy_tx)
        # Wrap and return the deployed contract.
        abi = get_deprecated_compiled_class_abi(contract_class=contract_class)
        deploy_call_info = execution_info_to_call_info(execution_info=execution_info, abi=abi)
        deployed_contract = StarknetContract(
            state=self.state,
            abi=abi,
            contract_address=deployed_contract_address,
            deploy_call_info=deploy_call_info,
        )
        return deployed_contract
