import functools
from typing import Dict, List

from starkware.cairo.bootloaders.bootloaders_consts import (
    get_circuit_applicative_bootloader_program,
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
def calculate_circuit_applicative_bootloader_program_hash(
    program_hash_function: HashFunction = HashFunction.BLAKE,
) -> int:
    circuit_applicative_bootloader_program = get_circuit_applicative_bootloader_program()
    return compute_program_hash_chain(
        program=circuit_applicative_bootloader_program, program_hash_function=program_hash_function
    )


def calculate_supported_bootloaders_hash_dict() -> Dict[str, str]:
    """
    Computes the supported-bootloaders hashes: the simple bootloader hash list hash and the
    circuit applicative bootloader program hash.
    """
    return {
        "supported_simple_bootloader_hash_list_hash": hex(
            compute_hash_on_elements(data=calculate_supported_simple_bootloader_hash_list())
        ),
        "circuit_applicative_bootloader_config_program_hash": hex(
            calculate_circuit_applicative_bootloader_program_hash()
        ),
    }


def combine_bootloader_config_hash(
    supported_simple_bootloader_hash_list_hash: int,
    circuit_applicative_bootloader_program_hash: int,
    circuit_applicative_config_commitment: int,
    supported_cairo_verifiers_hash: int,
) -> int:
    """
    Folds the four bootloader-config sub-hashes into the single felt that the bootloader outputs
    (see serialize_bootloader_config in run_bootloader.cairo) and that the verifier contract stores
    on-chain. The element order MUST match the Cairo side. compute_hash_on_elements is the Pedersen
    length-suffixed hash chain, identical to Cairo's hash_felts.
    """
    return compute_hash_on_elements(
        data=[
            supported_simple_bootloader_hash_list_hash,
            circuit_applicative_bootloader_program_hash,
            circuit_applicative_config_commitment,
            supported_cairo_verifiers_hash,
        ]
    )
