import os

import pytest

from starkware.starknet.compiler.compile import compile_starknet_files
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.testing.starknet import Starknet

CONTRACT_FILE = os.path.join(os.path.dirname(__file__), "test.cairo")


@pytest.fixture
async def starknet() -> Starknet:
    return await Starknet.empty()


@pytest.fixture
async def contract(starknet: Starknet) -> StarknetContract:
    return await starknet.deploy(source=CONTRACT_FILE)


@pytest.mark.asyncio
async def test_basic(starknet: Starknet, contract: StarknetContract):
    execution_info = await contract.increase_value(address=100, value=5).invoke()
    assert execution_info.result == ()
    execution_info = await contract.get_value(address=100).call()
    assert execution_info.result == (5,)

    # Check caller address.
    execution_info = await contract.get_caller().invoke()
    assert execution_info.result == (0,)
    execution_info = await contract.get_caller().invoke(caller_address=1234)
    assert execution_info.result == (1234,)

    # Check deploy without compilation.
    contract_def = compile_starknet_files(files=[CONTRACT_FILE])
    await starknet.deploy(contract_def=contract_def)


@pytest.mark.asyncio
async def test_l2_to_l1_message(starknet: Starknet, contract: StarknetContract):
    l1_address = int("0xce08635cc6477f3634551db7613cc4f36b4e49dc", 16)
    payload = [6, 28]
    await contract.send_message(to_address=l1_address, payload=payload).invoke()

    # Consume the message.
    starknet.consume_message_from_l2(
        from_address=contract.contract_address, to_address=l1_address, payload=payload
    )

    # Try to consume the message again; should fail.
    with pytest.raises(AssertionError):
        starknet.consume_message_from_l2(
            from_address=contract.contract_address, to_address=l1_address, payload=payload
        )


@pytest.mark.asyncio
async def test_l1_to_l2_message(starknet: Starknet, contract: StarknetContract):
    l1_address = int("0xce08635cc6477f3634551db7613cc4f36b4e49dc", 16)
    user = 6
    amount = 28

    # Send message to L2: Deposit 28 to user 6.
    await starknet.send_message_to_l2(
        from_address=l1_address,
        to_address=contract.contract_address,
        selector="deposit",
        payload=[user, amount],
    )
    execution_info = await contract.get_value(address=user).invoke()
    assert execution_info.result == (28,)
