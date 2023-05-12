// Specifies a sponge builtin (e.g., Poseidon builtin) as a 2-to-1 hash function.
// x, y - inputs to the hash function.
// c_in - the capacity part of the input (must be initialized to a constant, we use 2).
// result - the output of the hash function.
// result1 - can be used as another output element if a longer output is needed.
// c_out - the capacity part of the output (it is unsafe to use it as an output).
struct SpongeHashBuiltin {
    x: felt,
    y: felt,
    c_in: felt,
    result: felt,
    result1: felt,
    c_out: felt,
}

// Computes the hash of two given field elements.
// The hash function is defined by the hash_ptr used.
// For example, pass the poseidon builtin pointer to compute Poseidon hash.
//
// Arguments:
//   hash_ptr - the sponge hash builtin pointer.
//   x, y - the two field elements to be hashed, in this order.
//
// Returns:
//   result - the field element result of the hash.
func sponge_hash2{hash_ptr: SpongeHashBuiltin*}(x: felt, y: felt) -> (result: felt) {
    hash_ptr.x = x;
    hash_ptr.y = y;
    assert hash_ptr.c_in = 2;
    let result = hash_ptr.result;
    let hash_ptr = hash_ptr + SpongeHashBuiltin.SIZE;
    return (result=result);
}
