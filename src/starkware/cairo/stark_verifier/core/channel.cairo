from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_blake2s.blake2s import (
    blake2s_add_felt,
    blake2s_add_uint256_bigend,
    blake2s_bigend,
)
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.math import (
    assert_nn,
    assert_nn_le,
    assert_not_equal,
    split_felt,
    unsigned_div_rem,
)
from starkware.cairo.common.uint256 import Uint256, uint256_lt

// The Prover uses Montgomery form with R = 2**256 for field elements. This effects the
// non-interactive communication in several places.
const MONTGOMERY_R = 2 ** 256;

// Represents a non-interactive communication channel using the Fiat Shamir heuristic.
// In this context, "reading from the prover" means hashing a value into the state.
struct Channel {
    digest: Uint256,
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

func channel_new(digest: Uint256) -> (res: Channel) {
    return (res=Channel(digest=digest, counter=0));
}

// Generate randomness.
func random_uint256_to_prover{
    range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel
}() -> (res: Uint256) {
    alloc_locals;
    let (data: felt*) = alloc();
    let data_start = data;
    blake2s_add_uint256_bigend{data=data}(channel.digest);
    blake2s_add_uint256_bigend{data=data}(Uint256(low=channel.counter, high=0));
    let (res) = blake2s_bigend(data=data_start, n_bytes=64);
    let channel = Channel(digest=channel.digest, counter=channel.counter + 1);

    return (res=res);
}

func random_felts_to_prover{
    range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel
}(n_elements: felt, elements: felt*) -> () {
    alloc_locals;
    if (n_elements == 0) {
        return ();
    }

    let (local num: Uint256) = random_uint256_to_prover();
    local channel: Channel = channel;

    // To ensure a uniform distribution over field elements, if the generated 256-bit number x is in
    // range [0, C * PRIME), take x % PRIME. Otherwise, regenerate.
    // The maximal possible C is 2**256//PRIME = 31.

    const C_PRIME_AS_UINT256_LOW = 31 * 1;
    const C_PRIME_AS_UINT256_HIGH = 31 * 0x8000000000000110000000000000000;
    let (is_felt) = uint256_lt(
        num, Uint256(low=C_PRIME_AS_UINT256_LOW, high=C_PRIME_AS_UINT256_HIGH)
    );
    if (is_felt != 0) {
        // Note: This may overflow, but the computation should be done mod PRIME anyway.
        assert [elements] = (num.low + num.high * 2 ** 128) / MONTGOMERY_R;
        return random_felts_to_prover(n_elements=n_elements - 1, elements=&elements[1]);
    } else {
        return random_felts_to_prover(n_elements=n_elements, elements=elements);
    }
}

// Reads a truncated hash from the prover. See Channel.
func read_truncated_hash_from_prover{
    range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel
}(value: ChannelUnsentFelt) -> (value: ChannelSentFelt) {
    alloc_locals;
    let (data: felt*) = alloc();
    let data_start = data;
    assert_not_equal(channel.digest.low, 2 ** 128 - 1);
    blake2s_add_uint256_bigend{data=data}(
        Uint256(low=channel.digest.low + 1, high=channel.digest.high)
    );

    // value encodes the 160 most significant bits of a 256-bit hash.
    let (high, low) = unsigned_div_rem(value.value, 2 ** 32);
    assert_nn(high);
    blake2s_add_uint256_bigend{data=data}(Uint256(low=low * 2 ** 96, high=high));
    let (digest) = blake2s_bigend(data=data_start, n_bytes=64);
    let channel = Channel(digest=digest, counter=0);
    return (value=ChannelSentFelt(value.value));
}

// Reads a field element from the prover. See Channel.
func read_felt_from_prover{
    range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel
}(value: ChannelUnsentFelt) -> (value: ChannelSentFelt) {
    alloc_locals;
    let (data: felt*) = alloc();
    let data_start = data;
    assert_not_equal(channel.digest.low, 2 ** 128 - 1);
    blake2s_add_uint256_bigend{data=data}(
        Uint256(low=channel.digest.low + 1, high=channel.digest.high)
    );
    // The prover uses Montgomery form to generate randomness.
    blake2s_add_felt{data=data}(num=value.value * MONTGOMERY_R, bigend=1);
    let (digest) = blake2s_bigend(data=data_start, n_bytes=64);
    let channel = Channel(digest=digest, counter=0);
    return (value=ChannelSentFelt(value.value));
}

// Reads a 64bit integer from the prover. See Channel.
func read_uint64_from_prover{
    range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel
}(value: ChannelUnsentFelt) -> (value: ChannelSentFelt) {
    alloc_locals;
    assert_nn_le(value.value, 2 ** 64 - 1);
    let (data: felt*) = alloc();
    let data_start = data;
    assert_not_equal(channel.digest.low, 2 ** 128 - 1);
    blake2s_add_uint256_bigend{data=data}(
        Uint256(low=channel.digest.low + 1, high=channel.digest.high)
    );
    // Align 64 bit value to MSB.
    blake2s_add_uint256_bigend{data=data}(
        Uint256(
        low=0,
        high=value.value * 2 ** 64,
        )
    );
    let (digest) = blake2s_bigend(data=data_start, n_bytes=0x28);
    let channel = Channel(digest=digest, counter=0);
    return (value=ChannelSentFelt(value.value));
}

// Reads multiple field elements from the prover. Repeats read_felt_from_prover. See Channel.
func read_felts_from_prover{
    range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel
}(n_values: felt, values: ChannelUnsentFelt*) -> (values: ChannelSentFelt*) {
    read_felts_from_prover_inner(n_values=n_values, values=values);
    return (values=cast(values, ChannelSentFelt*));
}

func read_felts_from_prover_inner{
    range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel
}(n_values: felt, values: ChannelUnsentFelt*) -> () {
    if (n_values == 0) {
        return ();
    }

    let (value) = read_felt_from_prover(values[0]);
    return read_felts_from_prover_inner(n_values=n_values - 1, values=&values[1]);
}

// Reads a field element vector from the prover. Unlike read_felts_from_prover, this hashes all the
// field elements at once. See Channel.
func read_felt_vector_from_prover{
    range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel
}(n_values: felt, values: ChannelUnsentFelt*) -> (values: ChannelSentFelt*) {
    alloc_locals;
    let (data: felt*) = alloc();
    let data_start = data;
    assert_not_equal(channel.digest.low, 2 ** 128 - 1);
    blake2s_add_uint256_bigend{data=data}(
        Uint256(low=channel.digest.low + 1, high=channel.digest.high)
    );
    read_felt_vector_from_prover_inner{data=data}(n_values=n_values, values=values);
    let (digest) = blake2s_bigend(data=data_start, n_bytes=32 * (1 + n_values));
    let channel = Channel(digest=digest, counter=0);
    return (values=cast(values, ChannelSentFelt*));
}

func read_felt_vector_from_prover_inner{
    range_check_ptr, bitwise_ptr: BitwiseBuiltin*, channel: Channel, data: felt*
}(n_values: felt, values: ChannelUnsentFelt*) -> () {
    alloc_locals;
    if (n_values == 0) {
        return ();
    }
    blake2s_add_felt(num=values[0].value * MONTGOMERY_R, bigend=1);
    return read_felt_vector_from_prover_inner(n_values=n_values - 1, values=&values[1]);
}
