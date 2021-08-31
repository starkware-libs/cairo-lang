import os
import pytest

from starkware.starknet.compiler.compile import compile_starknet_files
from starkware.starknet.testing.starknet import Starknet

CONTRACT_FILE = os.path.join(os.path.dirname(__file__), "test.cairo")


@pytest.mark.asyncio
async def test_basic():
    contract_definition = compile_starknet_files([CONTRACT_FILE], debug_info=True)
    starknet = await Starknet.empty()

    contract_address = await starknet.deploy(contract_definition=contract_definition)
    res = await starknet.invoke_raw(
        contract_address=contract_address, selector="increase_value", calldata=[100, 5]
    )
    assert res.retdata == []

    res = await starknet.invoke_raw(
        contract_address=contract_address, selector="get_value", calldata=[100]
    )
    assert res.retdata == [5]
