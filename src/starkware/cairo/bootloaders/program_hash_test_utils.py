import json

from starkware.cairo.bootloaders.hash_program import compute_program_hash_chain
from starkware.cairo.lang.compiler.program import Program


def run_generate_hash_test(fix: bool, program_path: str, hash_path: str, command: str):
    compiled_program = Program.Schema().load(json.load(open(program_path)))
    program_hash = hex(compute_program_hash_chain(program=compiled_program))
    program_hash_key = "program_hash"

    if fix:
        with open(hash_path, "w") as fp:
            fp.write(json.dumps({program_hash_key: program_hash}, indent=4) + "\n")
        return

    expected_hash = json.load(open(hash_path))[program_hash_key]
    assert expected_hash == program_hash, (
        f"Wrong program hash in program_hash.json. Found: {program_hash}. "
        f"Expected: {expected_hash}. Please run {command}."
    )


def program_hash_test_main(program_path: str, hash_path: str, command: str):
    import argparse

    parser = argparse.ArgumentParser(description="Create or test the program hash.")
    parser.add_argument("--fix", action="store_true", help="Fix the value of the program hash.")

    args = parser.parse_args()
    run_generate_hash_test(
        fix=args.fix, program_path=program_path, hash_path=hash_path, command=command
    )
