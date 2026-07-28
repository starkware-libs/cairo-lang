import json
import os

from starkware.cairo.bootloaders.bootloader.supported_program_hashes_utils import (
    get_supported_cairo_verifier_hash_list,
)
from starkware.cairo.bootloaders.supported_bootloaders_hash import (
    calculate_supported_bootloaders_hash_dict,
)
from starkware.cairo.common.hash_state import compute_hash_on_elements
from starkware.python.utils import get_source_dir_path

BOOTLOADER_CONFIG_HASH_PATH = get_source_dir_path(
    "src/starkware/cairo/bootloaders/bootloader/bootloader_config_hash.json",
    default_value=os.path.join(os.path.dirname(__file__), "bootloader_config_hash.json"),
)


def test_bootloader_config_hash():
    run_bootloader_config_hash_test(fix=False)


def run_bootloader_config_hash_test(fix: bool):
    supported_cairo_verifier_hash_list_hash = hex(
        compute_hash_on_elements(data=get_supported_cairo_verifier_hash_list())
    )
    computed_bootloader_config_hash_dict = {
        **calculate_supported_bootloaders_hash_dict(),
        "supported_cairo_verifier_hash_list_hash": supported_cairo_verifier_hash_list_hash,
    }

    if fix:
        with open(BOOTLOADER_CONFIG_HASH_PATH, "w") as fp:
            fp.write(json.dumps(computed_bootloader_config_hash_dict, indent=4) + "\n")
        return

    expected_bootloader_config_hash_dict = json.load(open(BOOTLOADER_CONFIG_HASH_PATH))

    assert expected_bootloader_config_hash_dict == computed_bootloader_config_hash_dict


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Create or test the simple bootloader program hash."
    )
    parser.add_argument(
        "--fix", action="store_true", help="Fix the value of the simple bootloader program hash."
    )

    args = parser.parse_args()
    run_bootloader_config_hash_test(fix=args.fix)


if __name__ == "__main__":
    main()
