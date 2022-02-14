import os

import cachetools

from starkware.cairo.bootloader.hash_program import compute_program_hash_chain
from starkware.cairo.lang.compiler.program import Program

STARKNET_OS_COMPILED_PATH = os.path.join(os.path.dirname(__file__), "starknet_os_compiled.json")


@cachetools.cached(cache={})
def get_os_program() -> Program:
    with open(STARKNET_OS_COMPILED_PATH, "r") as file:
        return Program.Schema().loads(json_data=file.read())

@cachetools.cached(cache={})
def get_os_program_hash() -> int:
    program = get_os_program()
    return compute_program_hash_chain(program=program)

# Call this once here so that the cache gets warmed up at
# the beginning of the script run.
OS_PROGRAM = get_os_program()
OS_PROGRAM_HASH = get_os_program_hash()
