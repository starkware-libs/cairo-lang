from starkware.cairo.common.cairo_secp.bigint3 import BigInt3

// Represents a point on the secp256k1 elliptic curve.
// The zero point is represented as a point with x = 0 (there is no point on the curve with a zero
// x value).
// x and y satisfy the bounds of nondet_bigint3 for the relevant curve.
struct EcPoint {
    x: BigInt3,
    y: BigInt3,
}
