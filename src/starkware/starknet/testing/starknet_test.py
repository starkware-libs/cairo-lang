import os

import pytest

from starkware.starknet.compiler.compile import compile_starknet_files
from starkware.starknet.testing.starknet import Starknet

CONTRACT_FILE = os.path.join(os.path.dirname(__file__), "test.cairo")


@pytest.mark.asyncio
async def test_basic():
    starknet = await Starknet.empty()
    contract = await starknet.deploy(CONTRACT_FILE)
    res = await contract.increase_value(address=100, value=5).invoke()
    assert res == ()
    assert await contract.get_value(address=100).call() == (5,)

    # Check deploy without compilation.
    contract_def = compile_starknet_files(files=[CONTRACT_FILE])
    other_contract = await starknet.deploy(contract_def=contract_def)
