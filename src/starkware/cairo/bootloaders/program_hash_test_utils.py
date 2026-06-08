import json
from typing import Any, Callable, Optional

from starkware.cairo.bootloaders.hash_program import HashFunction, compute_program_hash_chain
from starkware.cairo.lang.compiler.program import Program


def run_generate_hash_test(
    fix: bool,
    program_path: str,
    hash_path: str,
    command: str,
    post_process: Optional[Callable[[Any], Any]] = None,
):
    """
    Compares the JSON content of 'hash_path' with the program hash of the given program.
    If post_process is given, it may add additional fields to the expected JSON.
    """
    compiled_program = Program.Schema().load(json.load(open(program_path)))
    program_hash = hex(
        compute_program_hash_chain(
            program=compiled_program, program_hash_function=HashFunction.PEDERSEN
        )
    )
    program_hash_key = "program_hash"

    expected_json = {program_hash_key: program_hash}
    if post_process is not None:
        expected_json = post_process(expected_json)

    if fix:
        with open(hash_path, "w") as fp:
            fp.write(json.dumps(expected_json, indent=4) + "\n")
        return

    with open(hash_path) as fp:
        actual_json = json.load(fp)
    assert expected_json == actual_json, (
        "Wrong value in program_hash.json. Found:\n"
        f"{json.dumps(actual_json, indent=4)}\n"
        "Expected:\n"
        f"{json.dumps(expected_json, indent=4)}\n"
        f"Please run {command}."
    )


def program_hash_test_main(
    program_path: str,
    hash_path: str,
    command: str,
    post_process: Optional[Callable[[Any], Any]] = None,
):
    import argparse

    parser = argparse.ArgumentParser(description="Create or test the program hash.")
    parser.add_argument("--fix", action="store_true", help="Fix the value of the program hash.")

    args = parser.parse_args()
    run_generate_hash_test(
        fix=args.fix,
        program_path=program_path,
        hash_path=hash_path,
        command=command,
        post_process=post_process,
    )
