import os
import re
from typing import Tuple

import pytest

from starkware.starknet.compiler.compile import compile_starknet_files
from starkware.starknet.testing.contract import StarknetContract
from starkware.starknet.testing.state import StarknetState

CONTRACT_FILE = os.path.join(os.path.dirname(__file__), "test.cairo")


@pytest.mark.asyncio
async def test_function_call():
    contract_definition = compile_starknet_files([CONTRACT_FILE], debug_info=True)
    state = await StarknetState.empty()
    contract_address = await state.deploy(
        constructor_calldata=[],
        contract_definition=contract_definition,
    )
    contract = StarknetContract(
        state=state, abi=contract_definition.abi, contract_address=contract_address
    )

    await contract.increase_value(address=132, value=3).invoke()
    await contract.increase_value(132, 5).invoke()
    await contract.increase_value(132, 10).call()

    # Since the return type is a named tuple, the result can be checked in multiple ways.
    execution_info = await contract.get_value(address=132).invoke()
    assert execution_info.result == (8,)
    execution_info = await contract.get_value(address=132).call()
    assert execution_info.result.res == 8  # Access by the name of the return value, `res`.
    execution_info = await contract.takes_array(a=[1, 2, 4]).invoke()
    assert execution_info.result[0] == 6  # Access by location.

    # Pass signature values using invoke's signature argument.
    execution_info = await contract.get_signature().invoke(signature=[1, 2, 4, 10])
    assert execution_info.result == ([1, 2, 4, 10],)

    # Check structs.
    point_1 = contract.Point(x=1, y=2)
    point_2 = contract.Point(x=3, y=4)
    execution_info = await contract.sum_points(points=(point_1, point_2)).invoke()
    assert execution_info.result == ((4, 6),)
    execution_info = await contract.sum_points(((1, 2), (3, 4))).invoke()
    assert execution_info.result.res == (4, 6)

    # Check multiple return values.
    execution_info = await contract.sum_and_mult_points(points=(point_1, point_2)).invoke()
    assert execution_info.result == (contract.Point(x=4, y=6), 11)

    # Check struct type consistency.
    assert isinstance(execution_info.result.sum_res, contract.Point)

    # Check type annotatins.
    func_annotations = contract.sum_and_mult_points.__annotations__
    expected_annotations = {
        "points": Tuple[Tuple[int, int], Tuple[int, int]],
        "return": (Tuple[int, int], int),
    }
    assert func_annotations == expected_annotations

    # Check negative flows.
    with pytest.raises(
        TypeError, match=re.escape("argument points[1] has wrong number of elements")
    ):
        contract.sum_points(points=((1, 2), (3, 4, 5)))

    with pytest.raises(TypeError, match=re.escape("type of argument points[0][1] must be int")):
        contract.sum_points(points=((1, 2.5), (3, 4)))

    point = contract.Point(x="1", y=2)
    with pytest.raises(TypeError, match=re.escape("type of argument points[0][0] must be int")):
        contract.sum_points(points=(point, (1, 2)))

    with pytest.raises(TypeError, match=re.escape("sum_points() takes 1 positional argument")):
        contract.sum_points(1, 2, 3, 4)
