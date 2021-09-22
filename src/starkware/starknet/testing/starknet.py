from typing import List, Optional, Union

from starkware.starknet.compiler.compile import compile_starknet_files
from starkware.starknet.definitions.general_config import StarknetGeneralConfig
from starkware.starknet.services.api.contract_definition import ContractDefinition
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.testing.state import StarknetState


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

    @classmethod
    async def empty(cls, general_config: Optional[StarknetGeneralConfig] = None) -> "Starknet":
        return Starknet(state=await StarknetState.empty(general_config=general_config))

    async def deploy(
        self,
        source: Optional[str] = None,
        contract_def: Optional[ContractDefinition] = None,
        contract_address: Optional[Union[int, str]] = None,
        cairo_path: Optional[List[str]] = None,
    ) -> StarknetContract:
        assert (0 if source is None else 1) + (
            0 if contract_def is None else 1
        ) == 1, "Exactly one of source, contract_def should be supplied."
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
        address = await self.state.deploy(
            contract_definition=contract_def, contract_address=contract_address
        )
        assert contract_def.abi is not None, "Missing ABI."
        return StarknetContract(state=self.state, abi=contract_def.abi, contract_address=address)
