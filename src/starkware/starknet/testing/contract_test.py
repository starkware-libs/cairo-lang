import os

import pytest

from starkware.starknet.compiler.compile import compile_starknet_files
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.testing.state import StarknetState

CONTRACT_FILE = os.path.join(os.path.dirname(__file__), "test.cairo")


@pytest.mark.asyncio
async def test_function_call():
    contract_definition = compile_starknet_files([CONTRACT_FILE], debug_info=True)
    state = await StarknetState.empty()
    contract_address = await state.deploy(contract_definition=contract_definition)
    contract = StarknetContract(
        state=state, abi=contract_definition.abi, contract_address=contract_address
    )

    await contract.increase_value(address=132, value=3).invoke()
    await contract.increase_value(132, 5).invoke()
    await contract.increase_value(132, 10).call()

    # Since the return type is a named tuple, the result can be checked in multiple ways.
    assert await contract.get_value(address=132).invoke() == (8,)
    assert (await contract.get_value(address=132).call()).res == 8
    assert (await contract.takes_array(a=[1, 2, 4]).invoke())[0] == 6
