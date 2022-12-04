import json
import os

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.structs import CairoStructFactory
from starkware.python.random_test import random_test
from starkware.python.utils import get_source_dir_path
from starkware.starknet.core.os.os_config.os_config_hash import (
    STARKNET_OS_CONFIG_HASH_VERSION,
    calculate_starknet_config_hash,
)
from starkware.starknet.core.os.os_program import get_os_program
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.general_config import StarknetChainId, StarknetOsConfig

HASH_PATH = get_source_dir_path(
    "src/starkware/starknet/core/os/os_config/os_config_hash.json",
    default_value=os.path.join(os.path.dirname(__file__), "os_config_hash.json"),
)
FEE_TOKEN_ADDRESS = 0x49D36570D4E46F48E99674BD3FCC84644DDD6B96F7C741B1562B82F9E004DC7
FIX_COMMAND = "starknet_os_config_hash_fix"


@random_test()
def test_get_starknet_config_hash(seed: int):
    """
    Tests the consistency between the Cairo implementation and the python one.
    """
    os_program = get_os_program()

    config_version = os_program.get_const(
        name="starkware.starknet.core.os.os_config.os_config.STARKNET_OS_CONFIG_VERSION",
        full_name_lookup=True,
    )
    assert config_version == STARKNET_OS_CONFIG_HASH_VERSION

    runner = CairoFunctionRunner(os_program, layout="all")
    starknet_os_config = StarknetOsConfig(
        fee_token_address=fields.AddressField.get_random_value(),
    )
    structs = CairoStructFactory(
        identifiers=os_program.identifiers,
        additional_imports=[
            "starkware.starknet.core.os.os_config.os_config.StarknetOsConfig",
        ],
    ).structs
    runner.run(
        "starkware.starknet.core.os.os_config.os_config.get_starknet_os_config_hash",
        hash_ptr=runner.pedersen_builtin.base,
        starknet_os_config=structs.StarknetOsConfig(
            chain_id=starknet_os_config.chain_id.value,
            fee_token_address=starknet_os_config.fee_token_address,
        ),
        use_full_name=True,
        verify_secure=True,
    )
    pedersen_ptr, starknet_config_hash = runner.get_return_values(2)
    assert pedersen_ptr == runner.pedersen_builtin.base + (
        (2 + structs.StarknetOsConfig.size) * runner.pedersen_builtin.cells_per_instance
    )
    assert starknet_config_hash == calculate_starknet_config_hash(
        starknet_os_config=starknet_os_config
    )


def run_starknet_os_config_hash_test(fix: bool):
    configs = {
        chain_id.name: StarknetOsConfig(chain_id=chain_id, fee_token_address=FEE_TOKEN_ADDRESS)
        for chain_id in StarknetChainId
    }
    config_hashes = {
        config_name: hex(calculate_starknet_config_hash(starknet_os_config=config))
        for config_name, config in configs.items()
    }

    if fix:
        with open(HASH_PATH, "w") as fp:
            fp.write(json.dumps(config_hashes, indent=4) + "\n")
        return

    expected_hashes = json.load(open(HASH_PATH))
    for config_name, computed_hash in config_hashes.items():
        expected_hash = expected_hashes[config_name]
        assert expected_hash == computed_hash, (
            f"Wrong StarkNet OS config hash in os_config_hash.json.\n"
            f"Computed hash: {computed_hash}. Expected: {expected_hash}.\n"
            f"Please run {FIX_COMMAND}."
        )


def test_reference_config_hash():
    run_starknet_os_config_hash_test(fix=False)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Create or test the StarkNet OS config hash.")
    parser.add_argument(
        "--fix", action="store_true", help="Fix the value of the StarkNet OS config hash."
    )

    args = parser.parse_args()
    run_starknet_os_config_hash_test(fix=args.fix)


if __name__ == "__main__":
    main()
