import json
import os
from typing import List

SUPPORTED_PROGRAM_HASH_LIST_PATH = os.path.join(
    os.path.dirname(__file__), "supported_program_hashes.json"
)


def get_supported_cairo_verifier_hash_list() -> List[int]:
    """
    Returns a list of the supported Cairo verifier program hashes.
    """
    hex_hash_list = json.load(open(SUPPORTED_PROGRAM_HASH_LIST_PATH))[
        "supported_cairo_verifier_program_hashes"
    ]
    return [int(hex_hash, 16) for hex_hash in hex_hash_list]


def get_circuit_applicative_config_commitment() -> int:
    """
    Returns the circuit applicative bootloader config commitment the bootloader input carries.
    bootloader_config_hash_test checks it against the commitment recomputed from the committed
    circuit verifier program hash and circuit registry (see config_commitment.py), and
    supported_program_hashes_test checks it against the published verifier programs.
    """
    return int(
        json.load(open(SUPPORTED_PROGRAM_HASH_LIST_PATH))["circuit_applicative_config_commitment"],
        16,
    )
