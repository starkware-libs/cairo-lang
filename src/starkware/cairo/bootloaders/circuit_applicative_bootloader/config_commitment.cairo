from starkware.cairo.bootloaders.circuit_applicative_bootloader.circuit_unpack import (
    BlakeHash,
    CircuitUnpackerConfig,
)
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.hash_state import hash_felts

// Computes the config commitment the circuit-unpacking applicative bootloader outputs: a Pedersen
// hash chain over the circuit verifier program hash and the hashes of the flattened multiverifier
// and leaf-verifier circuit hash lists (each circuit hash is eight little-endian u32 words).
//
// Shared so the on-chain unpacker can recompute the commitment when it sees the circuit
// applicative bootloader hash as a child fact.
func compute_circuit_applicative_bootloader_config_commitment{pedersen_ptr: HashBuiltin*}(
    verifier_program_hash: felt, config: CircuitUnpackerConfig*
) -> (commitment: felt) {
    alloc_locals;
    let (multiverifier_hashes_hash) = hash_felts{hash_ptr=pedersen_ptr}(
        data=config.multiverifier_hashes, length=config.n_multiverifier_hashes * BlakeHash.SIZE
    );
    let (leaf_verifier_hashes_hash) = hash_felts{hash_ptr=pedersen_ptr}(
        data=config.leaf_verifier_hashes, length=config.n_leaf_verifier_hashes * BlakeHash.SIZE
    );
    let (local config_elements: felt*) = alloc();
    assert config_elements[0] = verifier_program_hash;
    assert config_elements[1] = multiverifier_hashes_hash;
    assert config_elements[2] = leaf_verifier_hashes_hash;
    let (commitment) = hash_felts{hash_ptr=pedersen_ptr}(data=config_elements, length=3);
    return (commitment=commitment);
}
