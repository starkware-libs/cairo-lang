from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.builtin_poseidon.poseidon import (
    poseidon_hash_many,
    poseidon_hash_single,
)
from starkware.cairo.common.cairo_builtins import PoseidonBuiltin
from starkware.cairo.common.memcpy import memcpy

// Stores a sequence of elements. New elements can be added to the hash state using
// hash_update() and hash_update_single().
// The final hash of the entire sequence, can be obtained using hash_finalize().
struct HashState {
    start: felt*,
    end: felt*,
}

// Initializes a new HashState with no elements and returns it.
func hash_init() -> HashState {
    let (start: felt*) = alloc();
    return (HashState(start=start, end=start));
}

// Adds a single item to the HashState.
func hash_update_single{hash_state: HashState}(item: felt) {
    let current_end = hash_state.end;
    assert [current_end] = item;
    let hash_state = HashState(start=hash_state.start, end=current_end + 1);
    return ();
}

// Adds each element in the array to the HashState.
func hash_update{hash_state: HashState}(data_ptr: felt*, data_length: felt) {
    let current_end = hash_state.end;
    memcpy(dst=current_end, src=data_ptr, len=data_length);
    let hash_state = HashState(start=hash_state.start, end=current_end + data_length);
    return ();
}

// Computes a hash on the given array, and adds the hash as a single element to the HashState.
// Used when intermediate hash computation is required.
func hash_update_with_nested_hash{poseidon_ptr: PoseidonBuiltin*, hash_state: HashState}(
    data_ptr: felt*, data_length: felt
) {
    let (hash) = poseidon_hash_many(n=data_length, elements=data_ptr);
    hash_update_single(item=hash);
    return ();
}

// Returns the hash result of the HashState.
func hash_finalize{poseidon_ptr: PoseidonBuiltin*}(hash_state: HashState) -> felt {
    let (hash) = poseidon_hash_many(n=hash_state.end - hash_state.start, elements=hash_state.start);
    return (hash);
}
