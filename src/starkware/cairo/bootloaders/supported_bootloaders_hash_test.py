import json
import os

from starkware.cairo.bootloaders.supported_bootloaders_hash import (
    calculate_supported_bootloaders_hash_dict,
)
from starkware.python.utils import get_source_dir_path

SUPPORTED_BOOTLOADERS_HASH_PATH = get_source_dir_path(
    "src/starkware/cairo/bootloaders/supported_bootloaders_hash.json",
    default_value=os.path.join(os.path.dirname(__file__), "supported_bootloaders_hash.json"),
)


def test_supported_bootloaders_hash():
    run_supported_bootloaders_hash_test(fix=False)


def run_supported_bootloaders_hash_test(fix: bool):
    computed_supported_bootloaders_hash_dict = calculate_supported_bootloaders_hash_dict()

    if fix:
        with open(SUPPORTED_BOOTLOADERS_HASH_PATH, "w") as fp:
            fp.write(json.dumps(computed_supported_bootloaders_hash_dict, indent=4) + "\n")
        return

    expected_supported_bootloaders_hash_dict = json.load(open(SUPPORTED_BOOTLOADERS_HASH_PATH))

    assert expected_supported_bootloaders_hash_dict == computed_supported_bootloaders_hash_dict


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Create or test the supported bootloaders hashes.")
    parser.add_argument(
        "--fix", action="store_true", help="Fix the values of the supported bootloaders hashes."
    )

    args = parser.parse_args()
    run_supported_bootloaders_hash_test(fix=args.fix)


if __name__ == "__main__":
    main()
