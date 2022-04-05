from typing import List, Optional, Union

from starkware.starknet.business_logic.execution.objects import TransactionExecutionInfo
from starkware.starknet.compiler.compile import compile_starknet_files
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.services.api.contract_definition import ContractDefinition, EntryPointType
from starkware.starknet.services.api.messages import StarknetMessageToL1
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.testing.contract_utils import get_abi
from starkware.starknet.testing.objects import StarknetTransactionExecutionInfo
from starkware.starknet.testing.state import CastableToAddress, CastableToAddressSalt, StarknetState


class Starknet:
    """
    A high level interface to a StarkNet state object.
    Example:
      starknet = await Starknet.empty()
      contract = await starknet.deploy('contract.cairo')
      await contract.foo(a=1, b=[2, 3]).invoke()
    """

    def __init__(self, state: StarknetState):
        self.state = state

        # l1_to_l2_nonce starts from 2**128 to avoid nonce collisions with
        # messages that were sent using starkware.starknet.testing.postman.Postman.
        self.l1_to_l2_nonce = 2 ** 128

    @classmethod
    async def empty(cls, general_config: Optional[StarknetGeneralConfig] = None) -> "Starknet":
        return Starknet(state=await StarknetState.empty(general_config=general_config))

    async def deploy(
        self,
        source: Optional[str] = None,
        contract_def: Optional[ContractDefinition] = None,
        contract_address_salt: Optional[CastableToAddressSalt] = None,
        cairo_path: Optional[List[str]] = None,
        constructor_calldata: Optional[List[int]] = None,
    ) -> StarknetContract:
        assert (source is None) != (
            contract_def is None
        ), "Exactly one of source, contract_def should be supplied."
        if contract_def is None:
            contract_def = compile_starknet_files(
                files=[source], debug_info=True, cairo_path=cairo_path
            )
            source = None
            cairo_path = None
        assert (
            cairo_path is None
        ), "The cairo_path argument can only be used with the source argument."
        assert contract_def is not None
        address, execution_info = await self.state.deploy(
            contract_definition=contract_def,
            contract_address_salt=contract_address_salt,
            constructor_calldata=[] if constructor_calldata is None else constructor_calldata,
        )

        deploy_execution_info = StarknetTransactionExecutionInfo.from_internal(
            tx_execution_info=execution_info, result=(), main_call_events=[]
        )
        return StarknetContract(
            state=self.state,
            abi=get_abi(contract_definition=contract_def),
            contract_address=address,
            deploy_execution_info=deploy_execution_info,
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
    ) -> TransactionExecutionInfo:
        """
        Mocks the L1 contract function sendMessageToL2.

        Takes an optional nonce paramater to force a specific nonce, this
        should only be used by the Postman class.
        """
        if nonce is None:
            nonce = self.l1_to_l2_nonce
            self.l1_to_l2_nonce += 1

        return await self.state.invoke_raw(
            contract_address=to_address,
            selector=selector,
            calldata=[from_address, *payload],
            caller_address=0,
            max_fee=max_fee,
            entry_point_type=EntryPointType.L1_HANDLER,
            nonce=nonce,
        )
