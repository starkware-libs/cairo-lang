import argparse
import json
from enum import Enum

from starkware.cairo.common.cairo_blake2s.blake2s_utils import calculate_blake2s_hash_from_felt252s
from starkware.cairo.common.hash_chain import compute_hash_chain
from starkware.cairo.lang.compiler.program import Program, ProgramBase
from starkware.cairo.lang.version import __version__
from starkware.cairo.lang.vm.crypto import get_crypto_lib_context_manager, poseidon_hash_many
from starkware.python.utils import from_bytes


class HashFunction(Enum):
    """
    A hash function. These can be used e.g. for hashing a program within the bootloader.
    """

    PEDERSEN = 0
    POSEIDON = 1
    BLAKE = 2


def compute_program_hash_chain(
    program: ProgramBase,
    program_hash_function: HashFunction,
    bootloader_version=0,
    encode_blake2s_input: bool = False,
    little_endian_for_blake2s: bool = True,
):
    """
    Computes a hash chain over a program, including the length of the data chain.
    If `encode_blake2s_input` is True, the data chain is encoded according to the specification
    documented inside the `calculate_blake2s_hash_from_felt252s` function.
    If `little_endian_for_blake2s` is True, the blake input is encoded in little-endian u32s.
    """
    builtin_list = [from_bytes(builtin.encode("ascii")) for builtin in program.builtins]
    # The program header below is missing the data length, which is later added to the data_chain.
    program_header = [bootloader_version, program.main, len(program.builtins)] + builtin_list
    data_chain = program_header + program.data

    if program_hash_function == HashFunction.POSEIDON:
        return poseidon_hash_many(data_chain)
    elif program_hash_function == HashFunction.PEDERSEN:
        return compute_hash_chain([len(data_chain)] + data_chain)
    else:
        assert program_hash_function == HashFunction.BLAKE
        return calculate_blake2s_hash_from_felt252s(
            data=data_chain,
            encode=encode_blake2s_input,
            little_endian=little_endian_for_blake2s,
            prime=program.prime,
        )


def main():
    parser = argparse.ArgumentParser(description="A tool to compute the hash of a cairo program")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--program",
        type=argparse.FileType("r"),
        required=True,
        help="The name of the program json file.",
    )
    parser.add_argument(
        "--flavor",
        type=str,
        default="Release",
        choices=["Debug", "Release", "RelWithDebInfo"],
        help="Build flavor",
    )
    parser.add_argument(
        "--program-hash-function",
        type=str,
        choices=[hf.name.lower() for hf in HashFunction],
        default=HashFunction.PEDERSEN.name.lower(),
        help="Hash function to be used. Options: pedersen, poseidon, blake. Default: pedersen.",
    )
    args = parser.parse_args()

    with get_crypto_lib_context_manager(args.flavor):
        program = Program.Schema().load(json.load(args.program))
        print(
            hex(
                compute_program_hash_chain(
                    program=program,
                    program_hash_function=HashFunction[args.program_hash_function.upper()],
                )
            )
        )


if __name__ == "__main__":
    main()
