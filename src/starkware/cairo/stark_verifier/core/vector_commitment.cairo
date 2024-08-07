from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.builtin_poseidon.poseidon import poseidon_hash
from starkware.cairo.common.cairo_blake2s.blake2s import blake2s_add_felt, blake2s_bigend
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin, PoseidonBuiltin
from starkware.cairo.common.math import assert_nn, assert_nn_le, unsigned_div_rem
from starkware.cairo.common.math_cmp import is_nn
from starkware.cairo.common.pow import pow
from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.stark_verifier.core.channel import (
    Channel,
    ChannelSentFelt,
    ChannelUnsentFelt,
    read_felt_from_prover,
)

// Commitment values for a vector commitment. Used to generate a commitment by "reading" these
// values from the channel.
struct VectorUnsentCommitment {
    commitment_hash: ChannelUnsentFelt,
}

// Commitment for a vector of field elements.
struct VectorCommitment {
    config: VectorCommitmentConfig*,
    commitment_hash: ChannelSentFelt,
}

struct VectorCommitmentConfig {
    height: felt,
    n_verifier_friendly_commitment_layers: felt,
}

// Witness for a decommitment over queries.
struct VectorCommitmentWitness {
    // The authentication values: all the siblings of the subtree generated by the queried indices,
    // bottom layer up, left to right.
    n_authentications: felt,
    authentications: felt*,
}

// A query to the vector commitment.
struct VectorQuery {
    index: felt,
    value: felt,
}

// A query to the vector commitment that contains also the depth of the query in the Merkle tree.
struct VectorQueryWithDepth {
    index: felt,
    value: felt,
    depth: felt,
}

func validate_vector_commitment{range_check_ptr}(
    config: VectorCommitmentConfig*,
    expected_height: felt,
    n_verifier_friendly_commitment_layers: felt,
) {
    assert config.height = expected_height;
    // Note that n_verifier_friendly_commitment_layers can be greater than height (in such a case,
    // all Merkle layers use the verifier-friendly hash).
    assert config.n_verifier_friendly_commitment_layers = n_verifier_friendly_commitment_layers;
    return ();
}

func vector_commit{poseidon_ptr: PoseidonBuiltin*, channel: Channel, range_check_ptr}(
    unsent_commitment: VectorUnsentCommitment, config: VectorCommitmentConfig*
) -> (res: VectorCommitment*) {
    let (commitment_hash_value) = read_felt_from_prover(value=unsent_commitment.commitment_hash);
    return (res=new VectorCommitment(config=config, commitment_hash=commitment_hash_value));
}

// Decommits a VectorCommitment at multiple indices.
// Indices must be sorted and unique.
func vector_commitment_decommit{
    range_check_ptr,
    blake2s_ptr: felt*,
    bitwise_ptr: BitwiseBuiltin*,
    poseidon_ptr: PoseidonBuiltin*,
}(
    commitment: VectorCommitment*,
    n_queries: felt,
    queries: VectorQuery*,
    witness: VectorCommitmentWitness*,
) {
    alloc_locals;

    // Shift query indices.
    let (shift) = pow(2, commitment.config.height);
    let (shifted_queries: VectorQueryWithDepth*) = alloc();
    shift_queries(
        n_queries=n_queries,
        queries=queries,
        shifted_queries=shifted_queries,
        shift=shift,
        height=commitment.config.height,
    );

    let authentications = witness.authentications;

    let (expected_commitment) = compute_root_from_queries{authentications=authentications}(
        queue_head=shifted_queries,
        queue_tail=&shifted_queries[n_queries],
        n_verifier_friendly_layers=commitment.config.n_verifier_friendly_commitment_layers,
    );
    assert authentications = &witness.authentications[witness.n_authentications];

    assert expected_commitment = commitment.commitment_hash.value;
    return ();
}

// Shifts the query indices by shift=2**height, to convert index representation to heap-like.
// Validates the query index range.
func shift_queries{range_check_ptr}(
    n_queries: felt,
    queries: VectorQuery*,
    shifted_queries: VectorQueryWithDepth*,
    shift: felt,
    height: felt,
) {
    if (n_queries == 0) {
        return ();
    }
    assert_nn_le(queries.index, shift - 1);
    assert [shifted_queries] = VectorQueryWithDepth(
        index=queries.index + shift, value=queries.value, depth=height
    );
    return shift_queries(
        n_queries=n_queries - 1,
        queries=&queries[1],
        shifted_queries=&shifted_queries[1],
        shift=shift,
        height=height,
    );
}

// Verifies a queue of Merkle queries. [queue_head, queue_tail) is a queue, where each element
// represents a node index (given in a heap-like indexing) and value (either an inner
// node or a leaf).
func compute_root_from_queries{
    range_check_ptr,
    blake2s_ptr: felt*,
    bitwise_ptr: BitwiseBuiltin*,
    poseidon_ptr: PoseidonBuiltin*,
    authentications: felt*,
}(
    queue_head: VectorQueryWithDepth*,
    queue_tail: VectorQueryWithDepth*,
    n_verifier_friendly_layers: felt,
) -> (hash: felt) {
    alloc_locals;

    let current: VectorQueryWithDepth = queue_head[0];
    let next: VectorQueryWithDepth* = &queue_head[1];

    // Check if we're at the root.
    if (current.index == 1) {
        assert current.depth = 0;
        // Make sure the queue is empty.
        assert next = queue_tail;
        return (hash=current.value);
    }

    // Extract parent index.
    local bit;
    %{ ids.bit = ids.current.index & 1 %}
    assert bit = bit * bit;
    local parent_idx = (current.index - bit) / 2;
    assert [range_check_ptr] = parent_idx;
    let range_check_ptr = range_check_ptr + 1;

    // Write parent to queue.
    assert queue_tail.index = parent_idx;
    assert queue_tail.depth = current.depth - 1;
    let is_verifier_friendly = is_nn(n_verifier_friendly_layers - current.depth);
    if (bit == 0) {
        // Left child.
        if (next != queue_tail and current.index + 1 == next.index) {
            // Next holds the sibling.
            let (hash) = hash_blake_or_poseidon(current.value, next.value, is_verifier_friendly);
            assert queue_tail.value = hash;
            return compute_root_from_queries(
                queue_head=&queue_head[2],
                queue_tail=&queue_tail[1],
                n_verifier_friendly_layers=n_verifier_friendly_layers,
            );
        }
        let (hash) = hash_blake_or_poseidon(
            current.value, authentications[0], is_verifier_friendly
        );
    } else {
        // Right child.
        let (hash) = hash_blake_or_poseidon(
            authentications[0], current.value, is_verifier_friendly
        );
    }

    assert queue_tail.value = hash;
    let authentications = &authentications[1];
    return compute_root_from_queries(
        queue_head=&queue_head[1],
        queue_tail=&queue_tail[1],
        n_verifier_friendly_layers=n_verifier_friendly_layers,
    );
}

func hash_blake_or_poseidon{
    range_check_ptr,
    blake2s_ptr: felt*,
    bitwise_ptr: BitwiseBuiltin*,
    poseidon_ptr: PoseidonBuiltin*,
}(x: felt, y: felt, is_verifier_friendly: felt) -> (res: felt) {
    if (is_verifier_friendly == 1) {
        let (res) = poseidon_hash(x=x, y=y);
        return (res=res);
    } else {
        let (res) = truncated_blake2s(x, y);
        return (res=res);
    }
}

// A 248 LSB truncated version of blake2s.
// hash:
//   blake2s(x, y) & ((1 << 248) - 1).
func truncated_blake2s{range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*}(
    x: felt, y: felt
) -> (res: felt) {
    alloc_locals;
    let (data: felt*) = alloc();
    let data_start = data;

    with data {
        blake2s_add_felt(num=x, bigend=1);
        blake2s_add_felt(num=y, bigend=1);
    }
    let (hash: Uint256) = blake2s_bigend(data=data_start, n_bytes=64);

    // Truncate hash - convert value to felt, by taking the least significant 248 bits.
    let (high_h, high_l) = unsigned_div_rem(hash.high, 2 ** 120);
    return (res=hash.low + high_l * 2 ** 128);
}
