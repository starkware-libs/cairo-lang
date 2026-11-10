import json
import os
from typing import List

from starkware.cairo.common.hash_state import compute_hash_on_elements

# A committed copy of the circuit registry the proving repo published at the commit recorded in
# the bootloaders README, the file the proving binaries are given.
PRODUCTION_CIRCUIT_REGISTRY_PATH = os.path.join(
    os.path.dirname(__file__), "production_circuit_registry.json"
)
# The blake program hash of the stwo circuit verifier program published for the same commit, the
# verifier task of the circuit applicative flow. Written by supported_program_hashes_fix from the
# published program.
CIRCUIT_VERIFIER_PROGRAM_HASH_PATH = os.path.join(
    os.path.dirname(__file__), "circuit_verifier_program_hash.json"
)


def _get_canonical_circuit_hashes(registry_key: str) -> List[List[int]]:
    """
    Returns the production family registry's circuit hashes under `registry_key`, each as eight
    little-endian u32 words.
    """
    with open(PRODUCTION_CIRCUIT_REGISTRY_PATH, "r") as fp:
        registry = json.load(fp)
    return [[int(word, 16) for word in entry["circuit_hash"]] for entry in registry[registry_key]]


def get_canonical_multiverifier_hashes() -> List[List[int]]:
    """
    Returns the multiverifier circuit hashes (the circuit-tree unpacking's fold-node trust
    anchors).
    """
    return _get_canonical_circuit_hashes(registry_key="multiverifiers")


def get_canonical_leaf_verifier_hashes() -> List[List[int]]:
    """
    Returns the leaf verifier circuit hashes (the circuit-tree unpacking's leaf trust anchors).
    """
    return _get_canonical_circuit_hashes(registry_key="leaf_verifiers")


def get_circuit_verifier_program_hash() -> int:
    """
    Returns the committed blake program hash of the stwo circuit verifier program.
    """
    with open(CIRCUIT_VERIFIER_PROGRAM_HASH_PATH, "r") as fp:
        return int(json.load(fp)["circuit_verifier_program_hash"], 16)


def compute_circuit_applicative_bootloader_config_commitment(
    verifier_program_hash: int,
    multiverifier_hashes: List[List[int]],
    leaf_verifier_hashes: List[List[int]],
) -> int:
    """
    Computes the config commitment the circuit-unpacking applicative bootloader outputs: a Pedersen
    hash chain (compute_hash_on_elements, mirroring `config_commitment.cairo`) over the circuit
    verifier program hash and the hashes of the flattened multiverifier and leaf-verifier circuit
    hash lists (each circuit hash is eight little-endian u32 words). The on-chain unpacker
    recomputes this commitment to verify soundness when it sees the circuit applicative bootloader
    hash as a child.
    """

    def flat_hash(circuit_hashes: List[List[int]]) -> int:
        return compute_hash_on_elements(
            data=[word for circuit_hash in circuit_hashes for word in circuit_hash]
        )

    return compute_hash_on_elements(
        data=[
            verifier_program_hash,
            flat_hash(multiverifier_hashes),
            flat_hash(leaf_verifier_hashes),
        ]
    )


def compute_committed_circuit_applicative_config_commitment() -> int:
    """
    Computes the config commitment from the committed inputs alone: the circuit verifier program
    hash and the circuit hashes in the committed registry. Needs no access to the artifacts
    bucket, so the commitment the bootloader config carries can be checked from these sources.
    """
    return compute_circuit_applicative_bootloader_config_commitment(
        verifier_program_hash=get_circuit_verifier_program_hash(),
        multiverifier_hashes=get_canonical_multiverifier_hashes(),
        leaf_verifier_hashes=get_canonical_leaf_verifier_hashes(),
    )
