from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_blake2s.blake2s import blake2s_add_uint256_bigend, blake2s_bigend
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.math import assert_in_range, assert_lt, assert_nn_le, unsigned_div_rem
from starkware.cairo.common.pow import pow
from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.stark_verifier.core.channel import (
    Channel,
    ChannelSentFelt,
    ChannelUnsentFelt,
    read_uint64_from_prover,
)

const MAX_PROOF_OF_WORK_BITS = 50;
const MAX_NONCE = 2 ** 64 - 1;
const BYTE_UPPER_BOUND = 256;
const WORD_UPPER_BOUND = BYTE_UPPER_BOUND ** 8;

struct ProofOfWorkConfig {
    // Proof of work difficulty (number of bits required to be 0).
    n_bits: felt,
}

struct ProofOfWorkUnsentCommitment {
    nonce: ChannelUnsentFelt,
}

func proof_of_work_config_validate{range_check_ptr}(config: ProofOfWorkConfig*) {
    assert_in_range(config.n_bits, 1, MAX_PROOF_OF_WORK_BITS + 1);
    return ();
}

// Assumption: 0 < n_bits <= 64.
func proof_of_work_commit{
    range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel
}(unsent_commitment: ProofOfWorkUnsentCommitment*, config: ProofOfWorkConfig*) {
    alloc_locals;
    let digest = channel.digest;
    let (nonce) = read_uint64_from_prover(unsent_commitment.nonce);
    verify_proof_of_work(digest=digest, n_bits=config.n_bits, nonce=nonce);
    return ();
}

func verify_proof_of_work{range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*}(
    digest: Uint256, n_bits: felt, nonce: ChannelSentFelt
) {
    alloc_locals;
    // Validate ranges.
    assert_nn_le(nonce.value, MAX_NONCE);

    // Compute the initial hash.
    // Hash(0123456789abcded ||  digest_h  ||  digest_l  || n_bits).
    //          0x8 bytes    || 0x10 bytes || 0x10 bytes || 1 byte.
    // Total of 0x29 bytes.
    // Arrange the hash input according to the keccak requirement of 0x10 byte chunks.
    let (digest_hh, digest_hl) = unsigned_div_rem(digest.high, WORD_UPPER_BOUND);
    let (digest_lh, digest_ll) = unsigned_div_rem(digest.low, WORD_UPPER_BOUND);
    let (data) = alloc();
    let data_start = data;
    blake2s_add_uint256_bigend{data=data}(
        Uint256(
            low=digest_hl * WORD_UPPER_BOUND + digest_lh,
            high=0x123456789abcded * WORD_UPPER_BOUND + digest_hh,
        ),
    );
    // Align 72 bit value to MSB.
    blake2s_add_uint256_bigend{data=data}(
        Uint256(low=0, high=(digest_ll * BYTE_UPPER_BOUND + n_bits) * 2 ** 56)
    );
    let (init_hash) = blake2s_bigend(data=data_start, n_bytes=0x29);

    // Compute Hash(init_hash_high || init_hash_low || nonce)
    //                0x10 bytes   ||  0x10 bytes   || 8 bytes
    // Total of 0x28 bytes.
    let (data) = alloc();
    let data_start = data;
    blake2s_add_uint256_bigend{data=data}(init_hash);
    // Align 64 bit value to MSB.
    static_assert MAX_NONCE == 2 ** 64 - 1;
    blake2s_add_uint256_bigend{data=data}(Uint256(low=0, high=nonce.value * 2 ** 64));
    let (result) = blake2s_bigend(data=data_start, n_bytes=0x28);
    let (work_limit) = pow(2, 128 - n_bits);

    // Check.
    assert_lt(result.high, work_limit);
    return ();
}
