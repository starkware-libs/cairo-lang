import functools
from typing import Dict, List

from starkware.cairo.bootloaders.bootloaders_consts import (
    get_applicative_bootloader_program,
    get_no_builtin_simulation_simple_bootloader_program,
    get_simple_bootloader_program,
)
from starkware.cairo.bootloaders.hash_program import HashFunction, compute_program_hash_chain
from starkware.cairo.common.cairo_blake2s.blake2s_utils import calculate_blake2s_hash_from_felt252s
from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.cairo.lang.compiler.program import Program
from starkware.cairo.lang.vm.crypto import poseidon_hash_many


def calculate_supported_simple_bootloader_hash_list() -> List[int]:
    """
    Returns the hashes of the simple bootloader program that we use in our verifiers.
    Blake2s in the full/stripped stwo verifier and poseidon in the poseidon-stwo and stone
    verifiers.
    """
    simple_bootloader_program: Program = get_simple_bootloader_program()
    no_builtin_simulation_simple_bootloader_program: Program = (
        get_no_builtin_simulation_simple_bootloader_program()
    )
    return [
        poseidon_hash_many(array=simple_bootloader_program.data),
        calculate_blake2s_hash_from_felt252s(
            data=simple_bootloader_program.data,
            encode=True,
            prime=simple_bootloader_program.prime,
            little_endian=False,
        ),
        poseidon_hash_many(array=no_builtin_simulation_simple_bootloader_program.data),
        calculate_blake2s_hash_from_felt252s(
            data=no_builtin_simulation_simple_bootloader_program.data,
            encode=True,
            prime=no_builtin_simulation_simple_bootloader_program.prime,
            little_endian=False,
        ),
    ]


@functools.lru_cache(None)
def calculate_applicative_bootloader_program_hash(
    program_hash_function: HashFunction = HashFunction.BLAKE,
) -> int:
    applicative_bootloader_program = get_applicative_bootloader_program()
    return compute_program_hash_chain(
        program=applicative_bootloader_program, program_hash_function=program_hash_function
    )


def calculate_supported_bootloaders_hash_dict() -> Dict[str, str]:
    """
    Computes the supported-bootloaders hashes: the simple bootloader hash list hash and the
    applicative bootloader program hash.
    """
    return {
        "supported_simple_bootloader_hash_list_hash": hex(
            compute_hash_on_elements(data=calculate_supported_simple_bootloader_hash_list())
        ),
        "applicative_bootloader_config_program_hash": hex(
            calculate_applicative_bootloader_program_hash()
        ),
    }
