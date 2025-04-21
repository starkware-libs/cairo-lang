import os

import cachetools

from starkware.cairo.bootloaders.hash_program import HashFunction, compute_program_hash_chain
from starkware.cairo.lang.compiler.program import Program

STARKNET_OS_COMPILED_PATH = os.path.join(os.path.dirname(__file__), "starknet_os_compiled.json")


@cachetools.cached(cache={})
def get_os_casm() -> str:
    with open(STARKNET_OS_COMPILED_PATH, "r") as file:
        return file.read()


@cachetools.cached(cache={})
def get_os_program() -> Program:
    return Program.loads(get_os_casm())


@cachetools.cached(cache={})
def get_os_program_hash() -> int:
    program = get_os_program()
    return compute_program_hash_chain(program=program, program_hash_function=HashFunction.PEDERSEN)
