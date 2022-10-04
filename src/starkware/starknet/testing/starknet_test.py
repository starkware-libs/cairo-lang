import os
import re

import pytest
import pytest_asyncio

from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.starknet.compiler.compile import compile_starknet_files
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.testing.starknet import Starknet

CONTRACT_FILE = os.path.join(os.path.dirname(__file__), "test.cairo")
HINT_CONTRACT_FILE = os.path.join(os.path.dirname(__file__), "test_unwhitelisted_hint.cairo")


@pytest_asyncio.fixture
async def starknet() -> Starknet:
    return await Starknet.empty()


@pytest_asyncio.fixture
async def contract(starknet: Starknet) -> StarknetContract:
    return await starknet.deploy(source=CONTRACT_FILE)


@pytest.mark.asyncio
async def test_basic(starknet: Starknet, contract: StarknetContract):
    call_info = contract.deploy_call_info
    assert call_info.result == ()

    call_info = await contract.increase_value(address=100, value=5).execute()
    assert call_info.result == ()
    call_info = await contract.get_value(address=100).call()
    assert call_info.result == (5,)

    # Check caller address.
    call_info = await contract.get_caller().execute()
    assert call_info.result == (0,)
    call_info = await contract.get_caller().execute(caller_address=1234)
    assert call_info.result == (1234,)

    # Check deploy without compilation.
    contract_class = compile_starknet_files(files=[CONTRACT_FILE])
    await starknet.deploy(contract_class=contract_class)


@pytest.mark.asyncio
async def test_l2_to_l1_message(starknet: Starknet, contract: StarknetContract):
    l1_address = int("0xce08635cc6477f3634551db7613cc4f36b4e49dc", 16)
    payload = [6, 28]
    await contract.send_message(to_address=l1_address, payload=payload).execute()

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
    execution_info = await contract.get_value(address=user).execute()
    assert execution_info.result == (28,)


@pytest.mark.asyncio
async def test_contract_interaction(starknet: Starknet):
    contract_class = compile_starknet_files([CONTRACT_FILE], debug_info=True)
    contract = await starknet.deploy(contract_class=contract_class)
    proxy_contract = await starknet.deploy(contract_class=contract_class)

    await proxy_contract.call_increase_value(contract.contract_address, 123, 234).execute()
    assert (await proxy_contract.get_value(123).execute()).result == (0,)
    assert (await contract.get_value(123).execute()).result == (234,)


@pytest.mark.asyncio
async def test_struct_arrays(starknet: Starknet):
    contract_class = compile_starknet_files([CONTRACT_FILE], debug_info=True)
    contract = await starknet.deploy(contract_class=contract_class)
    assert (await contract.transpose([(123, 234), (4, 5)]).execute()).result == (
        [
            contract.Point(x=123, y=4),
            contract.Point(x=234, y=5),
        ],
    )

    with pytest.raises(
        TypeError,
        match=re.escape("argument inp[1] has wrong number of elements (expected 2, got 3 instead)"),
    ):
        await contract.transpose([(123, 234), (4, 5, 6)]).execute()


@pytest.mark.asyncio
async def test_declare_unwhitelisted_hint_contract(starknet: Starknet):
    with pytest.raises(
        PreprocessorError,
        match=re.escape(
            "This may indicate that this library function cannot be used in StarkNet contracts."
        ),
    ):
        await starknet.declare(source=HINT_CONTRACT_FILE)

    # Check that declare() does not throw an error with disable_hint_validation.
    await starknet.declare(source=HINT_CONTRACT_FILE, disable_hint_validation=True)


@pytest.mark.asyncio
async def test_deploy_unwhitelisted_hint_contract(starknet: Starknet):
    with pytest.raises(
        PreprocessorError,
        match=re.escape(
            "This may indicate that this library function cannot be used in StarkNet contracts."
        ),
    ):
        await starknet.deploy(source=HINT_CONTRACT_FILE)

    # Check that deploy() does not throw an error with disable_hint_validation.
    await starknet.deploy(source=HINT_CONTRACT_FILE, disable_hint_validation=True)
