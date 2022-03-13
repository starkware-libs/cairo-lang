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
from starkware.cairo.lang.builtins.bitwise.instance_def import CELLS_PER_BITWISE
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.compiler.cairo_compile import compile_cairo_files
from starkware.python.math_utils import div_ceil, safe_div
from starkware.python.utils import blockify

CAIRO_FILE = os.path.join(os.path.dirname(__file__), "blake2s_test.cairo")


@pytest.fixture(scope="session")
def program():
    return compile_cairo_files([CAIRO_FILE], prime=DEFAULT_PRIME, debug_info=True)


def test_blake_round(program):
    runner = CairoFunctionRunner(program, layout="all")

    state = [random.randrange(0, 2 ** 32) for i in range(16)]
    message = [random.randrange(0, 2 ** 32) for i in range(16)]
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

    h = [[random.randrange(0, 2 ** 32) for _ in range(8)] for _ in range(N_INSTANCES)]
    message = [[random.randrange(0, 2 ** 32) for _ in range(16)] for _ in range(N_INSTANCES)]
    t0 = [random.randrange(0, 2 ** 32) for _ in range(N_INSTANCES)]
    f0 = [random.randrange(0, 2 ** 32) for _ in range(N_INSTANCES)]

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
def test_blake2s(program, n_bytes):
    runner = CairoFunctionRunner(program, layout="all")

    value = bytes([random.randrange(256) for i in range(n_bytes)])
    value_words = [int.from_bytes(x, "little") for x in blockify(value, 4)]
    blake2s_ptr = runner.segments.add()
    runner.run(
        "blake2s",
        range_check_ptr=runner.range_check_builtin.base,
        blake2s_ptr=blake2s_ptr,
        data=value_words,
        n_bytes=n_bytes,
    )
    range_check_builtin_end, blake2s_ptr_end, output = runner.get_return_values(3)
    assert range_check_builtin_end.segment_index == runner.range_check_builtin.base.segment_index

    n_instances = max(1, div_ceil(n_bytes, 64))
    INSTANCE_SIZE = program.get_const("INSTANCE_SIZE")
    assert blake2s_ptr_end == blake2s_ptr + INSTANCE_SIZE * n_instances

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

    output = "".join(x.to_bytes(4, "little").hex() for x in runner.memory.get_range(output, 8))
    expected_output = hashlib.blake2s(value).hexdigest()
    assert expected_output == output


@pytest.mark.parametrize("n", [0, 1, 6, 7, 8, 13, 14, 15])
def test_finalize_blake2s(program, n):
    random.seed(0)
    runner = CairoFunctionRunner(program, layout="all")

    values = []
    for _ in range(n):
        h = [random.randrange(0, 2 ** 32) for _ in range(8)]
        message = [random.randrange(0, 2 ** 32) for _ in range(16)]
        t0 = random.randrange(0, 2 ** 32)
        f0 = random.randrange(0, 2 ** 32)
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
