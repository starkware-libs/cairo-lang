import os

from starkware.cairo.bootloaders.program_hash_test_utils import (
    program_hash_test_main,
    run_generate_hash_test,
)
from starkware.starknet.core.os.os_utils import OS_PROGRAM_HASH_PATH as HASH_PATH

PROGRAM_PATH = os.path.join(os.path.dirname(__file__), "starknet_os_compiled.json")
COMMAND = "starknet_os_program_hash_test_fix"


def test_starknet_program_hash():
    run_generate_hash_test(
        fix=False, program_path=PROGRAM_PATH, hash_path=HASH_PATH, command=COMMAND
    )


if __name__ == "__main__":
    program_hash_test_main(program_path=PROGRAM_PATH, hash_path=HASH_PATH, command=COMMAND)
