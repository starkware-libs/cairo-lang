import json
import os

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.common.structs import CairoStructFactory
from starkware.python.random_test_utils import random_test
from starkware.python.utils import get_source_dir_path
from starkware.starknet.core.os.os_config.os_config_hash import (
    STARKNET_OS_CONFIG_HASH_VERSION,
    calculate_starknet_config_hash,
)
from starkware.starknet.core.os.os_program import get_os_program
from starkware.starknet.definitions import fields
from starkware.starknet.definitions.chain_ids import CHAIN_ID_TO_FEE_TOKEN_ADDRESS, StarknetChainId
from starkware.starknet.definitions.general_config import STARKNET_LAYOUT_INSTANCE, StarknetOsConfig

CONFIG_HASH_DIR_PATH = get_source_dir_path(
    "src/starkware/starknet/core/os/os_config",
    default_value=os.path.dirname(__file__),
)
CONFIG_HASH_FILENAME = "os_config_hash.json"
PRIVATE_CONFIG_HASH_FILENAME = "private_os_config_hash.json"
CONFIG_HASH_PATH = os.path.join(CONFIG_HASH_DIR_PATH, CONFIG_HASH_FILENAME)
PRIVATE_CONFIG_HASH_PATH = os.path.join(CONFIG_HASH_DIR_PATH, PRIVATE_CONFIG_HASH_FILENAME)
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

    runner = CairoFunctionRunner(os_program, layout=STARKNET_LAYOUT_INSTANCE.layout_name)
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
            chain_id=starknet_os_config.chain_id,
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
        chain_id.name: StarknetOsConfig(
            chain_id=chain_id.value, fee_token_address=CHAIN_ID_TO_FEE_TOKEN_ADDRESS[chain_id]
        )
        for chain_id in StarknetChainId
    }
    config_hashes = {
        chain_id.name: hex(
            calculate_starknet_config_hash(starknet_os_config=configs[chain_id.name])
        )
        for chain_id in StarknetChainId
    }
    private_config_hashes = {
        chain_id.name: config_hashes[chain_id.name]
        for chain_id in StarknetChainId
        if chain_id.is_private()
    }
    public_config_hashes = {
        chain_id.name: config_hashes[chain_id.name]
        for chain_id in StarknetChainId
        if not chain_id.is_private()
    }

    if fix:
        with open(CONFIG_HASH_PATH, "w") as fp:
            fp.write(json.dumps(public_config_hashes, indent=4) + "\n")
        with open(PRIVATE_CONFIG_HASH_PATH, "w") as fp:
            fp.write(json.dumps(private_config_hashes, indent=4) + "\n")
        return

    # Assert all hashes in PRIVATE_CONFIG_HASH_PATH are for private chains and that all hashes in
    #   CONFIG_HASH_FILENAME are for public.
    public_expected_hashes = json.load(open(CONFIG_HASH_PATH))
    private_expected_hashes = json.load(open(PRIVATE_CONFIG_HASH_PATH))
    assert not any(
        (StarknetChainId[config_name].is_private() for config_name in public_expected_hashes)
    ), f"{CONFIG_HASH_FILENAME} should not contain any private chains' hashes."
    assert all(
        (StarknetChainId[config_name].is_private() for config_name in private_expected_hashes)
    ), f"{PRIVATE_CONFIG_HASH_FILENAME} should only contain private chains' hashes."

    # Assert the computed hashes are the same as the expected hashes.
    all_expected_hashes = {**public_expected_hashes, **private_expected_hashes}
    for config_name, computed_hash in config_hashes.items():
        assert (
            config_name in all_expected_hashes
        ), f"Missing StarkNet OS config hash for {config_name=}."
        expected_hash = all_expected_hashes[config_name]
        config_hash_filename = (
            PRIVATE_CONFIG_HASH_FILENAME
            if StarknetChainId[config_name].is_private()
            else CONFIG_HASH_FILENAME
        )
        assert expected_hash == computed_hash, (
            f"Wrong StarkNet OS config hash in {config_hash_filename}.\n"
            f"Computed hash: {computed_hash}. Expected: {expected_hash}.\n"
            f"Please run {FIX_COMMAND}."
        )
    assert len(all_expected_hashes) == len(
        config_hashes
    ), f"Unexpected hashes in {PRIVATE_CONFIG_HASH_FILENAME} or {CONFIG_HASH_FILENAME}."


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
