from starkware.cairo.bootloaders.program_hash_test_utils import (
    program_hash_test_main,
    run_generate_hash_test,
)
from starkware.python.utils import get_build_dir_path, get_source_dir_path

PROGRAM_PATH = get_build_dir_path(
    "src/starkware/cairo/cairo_verifier/cairo_verifier_compiled_all_cairo.json"
)
HASH_PATH = get_source_dir_path(
    rel_path="src/starkware/cairo/cairo_verifier/layouts/all_cairo/program_hash.json",
    default_value=get_build_dir_path(
        "src/starkware/cairo/cairo_verifier/layouts/all_cairo/program_hash.json"
    ),
)

COMMAND = "generate_cairo_verifier_program_hash_all_cairo"


def test_program_hash():
    run_generate_hash_test(
        fix=False, program_path=PROGRAM_PATH, hash_path=HASH_PATH, command=COMMAND
    )


if __name__ == "__main__":
    program_hash_test_main(program_path=PROGRAM_PATH, hash_path=HASH_PATH, command=COMMAND)
