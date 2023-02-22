import os

from starkware.cairo.bootloaders.program_hash_test_utils import (
    program_hash_test_main,
    run_generate_hash_test,
)

CURRENT_DIR_PATH = os.path.dirname(__file__)
PROGRAM_PATH = os.path.join(CURRENT_DIR_PATH, "cairo_verifier_compiled_all_cairo.json")
HASH_PATH = os.path.join(CURRENT_DIR_PATH, "program_hash.json")
COMMAND = "generate_cairo_verifier_program_hash_all_cairo"


def test_program_hash():
    run_generate_hash_test(
        fix=False, program_path=PROGRAM_PATH, hash_path=HASH_PATH, command=COMMAND
    )


if __name__ == "__main__":
    program_hash_test_main(program_path=PROGRAM_PATH, hash_path=HASH_PATH, command=COMMAND)
