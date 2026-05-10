from typing import List

from starkware.cairo.bootloaders.hash_program import HashFunction
from starkware.cairo.common.cairo_blake2s.blake2s_utils import calculate_blake2s_hash_from_felt252s
from starkware.cairo.lang.vm.crypto import pedersen_hash
from starkware.python.utils import from_bytes


def get_aggregator_input_size(program_output: List[int]) -> int:
    """
    Returns the size of the input to an aggregator program.
    """
    assert len(program_output) > 0, "Invalid program output for an aggregator program."
    n_tasks = program_output[0]

    offset = 1
    for _ in range(n_tasks):
        assert len(program_output) > offset, "Invalid program output for an aggregator program."
        task_size = program_output[offset]
        offset += task_size

    return offset


def add_aggregator_prefix(program_hash: int, program_hash_function: HashFunction) -> int:
    """
    Computes H("AGGREGATOR", program_hash) which indicates that the program was treated by the
    bootloader as an aggregator program.
    """
    assert program_hash_function in [
        HashFunction.PEDERSEN,
        HashFunction.BLAKE,
    ], "Invalid program hash function."
    data = [from_bytes(b"AGGREGATOR"), program_hash]
    if program_hash_function == HashFunction.PEDERSEN:
        return pedersen_hash(*data)
    return calculate_blake2s_hash_from_felt252s(data=data, encode=True, little_endian=False)
