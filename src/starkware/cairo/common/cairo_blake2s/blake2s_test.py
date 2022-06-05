import hashlib
import itertools
import os
import random
from typing import List, Sequence

import pytest

from starkware.cairo.common.cairo_blake2s.blake2s_utils import (
    IV,
    SIGMA,
    blake2s_compress,
    blake_round,
)
from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.structs import CairoStructFactory, CairoStructProxy
from starkware.cairo.lang.builtins.bitwise.instance_def import CELLS_PER_BITWISE
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.cairo.lang.compiler.program import Program
from starkware.python.math_utils import div_ceil, safe_div
from starkware.python.utils import blockify

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "blake2s_test.cairo")


@pytest.fixture(scope="session")
def program():
    return compile_cairo_files([CAIRO_FILE], prime=DEFAULT_PRIME, debug_info=True)


@pytest.fixture
def structs(program: Program) -> CairoStructProxy:
    return CairoStructFactory.from_program(
        program,
        additional_imports=["starkware.cairo.common.uint256.Uint256"],
    ).structs


def test_blake_round(program):
    runner = CairoFunctionRunner(program, layout="all")

    state = [random.randrange(0, 2**32) for i in range(16)]
    message = [random.randrange(0, 2**32) for i in range(16)]
    sigma = list(range(16))
    random.shuffle(sigma)
    runner.run(
        "starkware.cairo.common.cairo_blake2s.packed_blake2s.blake_round",
        runner.bitwise_builtin.base,
        state,
        message,
        sigma,
        use_full_name=True,
    )
    bitwise_builtin_end, new_state_ptr = runner.get_return_values(2)
    assert bitwise_builtin_end == runner.bitwise_builtin.base + 96 * CELLS_PER_BITWISE
    new_state = runner.memory.get_range(new_state_ptr, 16)
    expected_new_state = blake_round(state=state, message=message, sigma=sigma)
    assert new_state == expected_new_state

    print(f"Number of steps: {runner.vm.current_step}.")


def test_compress(program):
    N_INSTANCES = 7
    SHIFT = 35

    runner = CairoFunctionRunner(program, layout="all")

    h = [[random.randrange(0, 2**32) for _ in range(8)] for _ in range(N_INSTANCES)]
    message = [[random.randrange(0, 2**32) for _ in range(16)] for _ in range(N_INSTANCES)]
    t0 = [random.randrange(0, 2**32) for _ in range(N_INSTANCES)]
    f0 = [random.randrange(0, 2**32) for _ in range(N_INSTANCES)]

    def pack_value(values: Sequence[int]) -> int:
        assert len(values) == N_INSTANCES
        return sum(val * 2 ** (SHIFT * i) for i, val in enumerate(values))

    def pack_array(lists: Sequence[Sequence[int]]) -> List[int]:
        return [pack_value(values) for values in zip(*lists)]

    new_h_ptr = runner.segments.add()
    runner.run(
        "starkware.cairo.common.cairo_blake2s.packed_blake2s.blake2s_compress",
        runner.bitwise_builtin.base,
        pack_array(h),
        pack_array(message),
        pack_value(t0),
        pack_value(f0),
        list(itertools.chain(*SIGMA)),
        new_h_ptr,
        use_full_name=True,
    )
    (bitwise_builtin_end,) = runner.get_return_values(1)
    assert bitwise_builtin_end == runner.bitwise_builtin.base + 978 * CELLS_PER_BITWISE
    new_h = [x for x in runner.memory.get_range(new_h_ptr, 8)]
    expected_new_h_list = [
        blake2s_compress(h=h[i], message=message[i], t0=t0[i], t1=0, f0=f0[i], f1=0)
        for i in range(N_INSTANCES)
    ]
    assert new_h == pack_array(expected_new_h_list)

    print(f"Number of steps: {runner.vm.current_step}.")


@pytest.mark.parametrize("n_bytes", list(range(70)) + [100, 200, 255, 256, 257])
def test_blake2s_func(program, n_bytes):
    value = bytes([random.randrange(256) for i in range(n_bytes)])
    value_words = [int.from_bytes(x, "little") for x in blockify(value, 4)]
    n_instances = max(1, div_ceil(n_bytes, 64))
    INSTANCE_SIZE = program.get_const("INSTANCE_SIZE")
    expected_output = hashlib.blake2s(value).hexdigest()

    def check_intermediate(runner, blake2s_ptr):
        h = IV[:]
        h[0] ^= 0x01010020
        for i in range(n_instances):
            message = (value_words[i * 16 : (i + 1) * 16] + [0] * 16)[:16]
            t = min((i + 1) * 64, n_bytes)
            f = 0xFFFFFFFF if n_bytes <= 64 * (i + 1) else 0
            next_state = blake2s_compress(h=h, message=message, t0=t, t1=0, f0=f, f1=0)
            assert runner.memory.get_range(blake2s_ptr + i * INSTANCE_SIZE, INSTANCE_SIZE) == (
                h + message + [t, f] + next_state
            )
            h = next_state

    def run_func(func_name: str, n_rets: int, has_bitwise: bool):
        runner = CairoFunctionRunner(program, layout="all")
        blake2s_ptr = runner.segments.add()
        runner.run(
            func_name,
            *([runner.bitwise_builtin.base] if has_bitwise else []),
            range_check_ptr=runner.range_check_builtin.base,
            blake2s_ptr=blake2s_ptr,
            data=value_words,
            n_bytes=n_bytes,
        )
        if has_bitwise:
            bitwise_ptr_end, *rets = runner.get_return_values(3 + n_rets)
            assert bitwise_ptr_end.segment_index == runner.bitwise_builtin.base.segment_index
        else:
            rets = runner.get_return_values(2 + n_rets)
        range_check_builtin_end, blake2s_ptr_end = rets[:2]
        assert (
            range_check_builtin_end.segment_index == runner.range_check_builtin.base.segment_index
        )
        assert blake2s_ptr_end == blake2s_ptr + INSTANCE_SIZE * n_instances
        check_intermediate(runner, blake2s_ptr)
        return (runner, *rets[2:])

    runner, output = run_func(func_name="blake2s_as_words", n_rets=1, has_bitwise=False)
    output = "".join(x.to_bytes(4, "little").hex() for x in runner.memory.get_range(output, 8))
    assert expected_output == output

    runner, res_low, res_high = run_func(func_name="blake2s", n_rets=2, has_bitwise=False)
    output = (res_low.to_bytes(16, "little") + res_high.to_bytes(16, "little")).hex()
    assert expected_output == output

    runner, res_low, res_high = run_func(func_name="blake2s_bigend", n_rets=2, has_bitwise=True)
    output = (res_high.to_bytes(16, "big") + res_low.to_bytes(16, "big")).hex()
    assert expected_output == output


@pytest.mark.parametrize("n", [0, 1, 6, 7, 8, 13, 14, 15])
def test_finalize_blake2s(program, n):
    random.seed(0)
    runner = CairoFunctionRunner(program, layout="all")

    values = []
    for _ in range(n):
        h = [random.randrange(0, 2**32) for _ in range(8)]
        message = [random.randrange(0, 2**32) for _ in range(16)]
        t0 = random.randrange(0, 2**32)
        f0 = random.randrange(0, 2**32)
        output = blake2s_compress(h=h, message=message, t0=t0, t1=0, f0=f0, f1=0)
        assert len(output) == 8
        values += h + message + [t0, f0] + output

    values_ptr = runner.segments.gen_arg(values)
    runner.run(
        "finalize_blake2s",
        runner.range_check_builtin.base,
        runner.bitwise_builtin.base,
        blake2s_ptr_start=values_ptr,
        blake2s_ptr_end=values_ptr + len(values),
    )
    range_check_builtin_end, bitwise_ptr_end = runner.get_return_values(2)
    assert range_check_builtin_end.segment_index == runner.range_check_builtin.base.segment_index
    n_bitwise = safe_div(bitwise_ptr_end - runner.bitwise_builtin.base, CELLS_PER_BITWISE)
    n_packed_instances = div_ceil(n, 7)
    assert n_bitwise == n_packed_instances * 978
    print("Steps:", runner.vm.current_step)
    print("Estimated trace cells:", 50 * runner.vm.current_step + 300 * n_bitwise)


@pytest.mark.parametrize("n", [0, 1, 7])
def test_run_and_finalize_blake2s(program, n):
    random.seed(0)
    runner = CairoFunctionRunner(program, layout="all")

    values = [
        bytes([random.randrange(256) for _ in range(random.randrange(257))]) for _ in range(n)
    ]
    n_expected_instances = sum(max(1, div_ceil(len(x), 64)) for x in values)
    n_expected_packed_instances = div_ceil(n_expected_instances, 7)

    runner.run(
        "run_blake2s_and_finalize",
        runner.range_check_builtin.base,
        runner.bitwise_builtin.base,
        [[int.from_bytes(x, "little") for x in blockify(value, 4)] for value in values],
        list(map(len, values)),
        n,
    )
    range_check_builtin_end, bitwise_ptr_end = runner.get_return_values(2)
    assert range_check_builtin_end.segment_index == runner.range_check_builtin.base.segment_index
    n_bitwise = safe_div(bitwise_ptr_end - runner.bitwise_builtin.base, CELLS_PER_BITWISE)
    assert n_bitwise == n_expected_packed_instances * 978

    print("Steps:", runner.vm.current_step)
    print("Estimated trace cells:", 50 * runner.vm.current_step + 300 * n_bitwise)


def cairo_blake_representation(data: bytes):
    """
    Converts a byte array to a list of 32-bit words (little-endian).
    """
    return [int.from_bytes(data[i : i + 4], "little") for i in range(0, len(data), 4)]


@pytest.mark.parametrize("big_endian", [False, True])
def test_blake2s_add_uint256(program, structs, big_endian: bool):
    runner = CairoFunctionRunner(program, layout="all")
    num = random.randrange(2**256)
    data = runner.segments.add()

    runner.run(
        "blake2s_add_uint256" + ("_bigend" if big_endian else ""),
        **(dict(bitwise_ptr=runner.bitwise_builtin.base) if big_endian else {}),
        data=data,
        num=structs.Uint256(low=num % 2**128, high=num // 2**128),
    )

    if big_endian:
        (res_bitwise_ptr, res_data) = runner.get_return_values(2)
        assert res_bitwise_ptr == runner.bitwise_builtin.base + 4 * 5
    else:
        (res_data,) = runner.get_return_values(1)

    assert runner.memory.get_range(data, res_data - data) == cairo_blake_representation(
        num.to_bytes(32, "big" if big_endian else "little")
    )


@pytest.mark.parametrize("big_endian", [False, True])
def test_blake2s_add_felts(program, structs, big_endian: bool):
    runner = CairoFunctionRunner(program, layout="all")
    nums = [random.randrange(DEFAULT_PRIME) for _ in range(5)]
    data = runner.segments.add()

    runner.run(
        "blake2s_add_felts",
        range_check_ptr=runner.range_check_builtin.base,
        bitwise_ptr=runner.bitwise_builtin.base,
        data=data,
        n_elements=len(nums),
        elements=nums,
        bigend=1 if big_endian else 0,
    )
    res_range_check_ptr, res_bitwise_ptr, res_data = runner.get_return_values(3)
    assert res_range_check_ptr.segment_index == runner.range_check_builtin.base.segment_index
    assert res_bitwise_ptr == runner.bitwise_builtin.base + (4 * 5 * len(nums) if big_endian else 0)
    assert runner.memory.get_range(data, res_data - data) == cairo_blake_representation(
        b"".join(num.to_bytes(32, "big" if big_endian else "little") for num in nums)
    )


@pytest.mark.parametrize("big_endian", [False, True])
def test_blake2s_felts(program, big_endian: bool):
    runner = CairoFunctionRunner(program, layout="all")
    nums = [random.randrange(DEFAULT_PRIME) for _ in range(5)]

    blake2s_ptr = runner.segments.add()
    runner.run(
        "blake2s_felts",
        range_check_ptr=runner.range_check_builtin.base,
        bitwise_ptr=runner.bitwise_builtin.base,
        blake2s_ptr=blake2s_ptr,
        n_elements=len(nums),
        elements=nums,
        bigend=1 if big_endian else 0,
    )
    (
        res_range_check_ptr,
        res_bitwise_ptr,
        res_blake2s_ptr,
        res_low,
        res_high,
    ) = runner.get_return_values(5)
    assert res_range_check_ptr.segment_index == runner.range_check_builtin.base.segment_index
    assert res_bitwise_ptr == runner.bitwise_builtin.base + (4 * 5 * len(nums) if big_endian else 0)
    assert res_blake2s_ptr.segment_index == blake2s_ptr.segment_index
    data = b"".join(num.to_bytes(32, "big" if big_endian else "little") for num in nums)
    expected_res = int.from_bytes(hashlib.blake2s(data).digest(), "little")
    assert expected_res == res_low + (res_high << 128)
