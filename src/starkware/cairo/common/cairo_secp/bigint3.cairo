// Represents a big integer defined by:
//   d0 + BASE * d1 + BASE**2 * d2.
// Note that the limbs (d_i) are NOT restricted to the range [0, BASE) and in particular they
// can be negative.
// In most cases this is used to represent a Secp256k1 or Secp256r1 field element.
struct UnreducedBigInt3 {
    d0: felt,
    d1: felt,
    d2: felt,
}

// Same as UnreducedBigInt3, except that d0, d1 and d2 satisfy the bounds of
// nondet_bigint3 or are the difference of two values satisfying those bounds.
// In most cases this is used to represent a Secp256k1 or Secp256r1 field element.
struct BigInt3 {
    d0: felt,
    d1: felt,
    d2: felt,
}

// Same as BigInt3, except the bounds on d0, d1 and d2 are twice as large.
struct SumBigInt3 {
    d0: felt,
    d1: felt,
    d2: felt,
}
