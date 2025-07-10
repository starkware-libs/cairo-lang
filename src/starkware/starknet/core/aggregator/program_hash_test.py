import os

from starkware.cairo.bootloaders.aggregator_utils import add_aggregator_prefix
from starkware.cairo.bootloaders.program_hash_test_utils import (
    program_hash_test_main,
    run_generate_hash_test,
)
from starkware.starknet.core.aggregator.utils import AGGREGATOR_PROGRAM_HASH_PATH as HASH_PATH

PROGRAM_PATH = os.path.join(os.path.dirname(__file__), "aggregator.json")

COMMAND = "aggregator_program_hash_test_fix"


def post_process(data):
    data["program_hash_with_aggregator_prefix"] = hex(
        add_aggregator_prefix(int(data["program_hash"], 16))
    )
    return data


def test_aggregator_program_hash():
    run_generate_hash_test(
        fix=False,
        program_path=PROGRAM_PATH,
        hash_path=HASH_PATH,
        command=COMMAND,
        post_process=post_process,
    )


if __name__ == "__main__":
    program_hash_test_main(
        program_path=PROGRAM_PATH, hash_path=HASH_PATH, command=COMMAND, post_process=post_process
    )
