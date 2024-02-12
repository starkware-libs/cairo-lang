from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.builtin_poseidon.poseidon import poseidon_hash, poseidon_hash_many
from starkware.cairo.common.cairo_builtins import PoseidonBuiltin
from starkware.cairo.common.math import assert_nn, assert_nn_le
from starkware.cairo.stark_verifier.core.serialize_utils import append_felt, append_felts

// The Prover uses Montgomery form with R = 2**256 for field elements. This effects the
// non-interactive communication in several places.
const MONTGOMERY_R = 2 ** 256;

// Represents a non-interactive verifier-friendly communication channel using the Fiat Shamir
// heuristic.
// In this context, "reading from the prover" means hashing a value into the state.
struct Channel {
    digest: felt,
    counter: felt,
}

// A wrapper around felt with a guarantee that the felt must be read from the channel before
// use.
struct ChannelUnsentFelt {
    value: felt,
}

// A wrapper around felt with a guarantee that the felt was read from the channel as data from the
// prover.
struct ChannelSentFelt {
    value: felt,
}

func channel_new(digest: felt) -> (res: Channel) {
    return (res=Channel(digest=digest, counter=0));
}

// Generate randomness.
func random_felt_to_prover{range_check_ptr, poseidon_ptr: PoseidonBuiltin*, channel: Channel}() -> (
    res: felt
) {
    alloc_locals;
    let (felt_to_prover: felt) = poseidon_hash(x=channel.digest, y=channel.counter);
    let channel = Channel(digest=channel.digest, counter=channel.counter + 1);
    return (res=felt_to_prover);
}

func random_felts_to_prover{range_check_ptr, poseidon_ptr: PoseidonBuiltin*, channel: Channel}(
    n_elements: felt, elements: felt*
) -> () {
    if (n_elements == 0) {
        return ();
    }
    alloc_locals;
    let (value: felt) = random_felt_to_prover();

    assert elements[0] = value;
    return random_felts_to_prover(n_elements=n_elements - 1, elements=&elements[1]);
}

// Reads a field element from the prover.
func read_felt_from_prover{range_check_ptr, poseidon_ptr: PoseidonBuiltin*, channel: Channel}(
    value: ChannelUnsentFelt
) -> (value: ChannelSentFelt) {
    // Use poseidon_hash_many() instead of poseidon_hash() since the current prover handles all the
    // data it sends as an array of arbitrary size.
    let (digest: felt) = poseidon_hash_many(n=2, elements=new (channel.digest + 1, value.value));
    let channel = Channel(digest=digest, counter=0);
    return (value=ChannelSentFelt(value.value));
}

// Reads a 64bit integer from the prover.
func read_uint64_from_prover{range_check_ptr, poseidon_ptr: PoseidonBuiltin*, channel: Channel}(
    value: ChannelUnsentFelt
) -> (value: ChannelSentFelt) {
    assert_nn_le(value.value, 2 ** 64 - 1);
    return read_felt_from_prover(value);
}

// Reads a field element vector from the prover. This hashes all the field elements at once.
func read_felt_vector_from_prover{poseidon_ptr: PoseidonBuiltin*, channel: Channel}(
    n_values: felt, values: ChannelUnsentFelt*
) -> (values: ChannelSentFelt*) {
    // For append_felts we assume ChannelUnsentFelt is a struct with one felt.
    static_assert ChannelUnsentFelt.SIZE == 1;
    static_assert ChannelSentFelt.SIZE == 1;
    alloc_locals;
    let (data: felt*) = alloc();
    let data_start = data;
    append_felt{data=data}(channel.digest + 1);
    append_felts{data=data}(len=n_values, arr=values);
    let (digest) = poseidon_hash_many(n=(1 + n_values), elements=data_start);
    let channel = Channel(digest=digest, counter=0);
    return (values=cast(values, ChannelSentFelt*));
}
