from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.cairo_keccak.keccak import finalize_keccak, keccak_uint256s_bigend
from starkware.cairo.common.cairo_secp.bigint import (
    BASE,
    BigInt3,
    UnreducedBigInt3,
    bigint_mul,
    bigint_to_uint256,
    nondet_bigint3,
    uint256_to_bigint,
)
from starkware.cairo.common.cairo_secp.constants import BETA, N0, N1, N2
from starkware.cairo.common.cairo_secp.ec import EcPoint, ec_add, ec_mul, ec_negate
from starkware.cairo.common.cairo_secp.field import (
    reduce,
    unreduced_mul,
    unreduced_sqr,
    validate_reduced_field_element,
    verify_zero,
)
from starkware.cairo.common.math import assert_nn, assert_nn_le, assert_not_zero, unsigned_div_rem
from starkware.cairo.common.math_cmp import RC_BOUND
from starkware.cairo.common.uint256 import Uint256

@known_ap_change
func get_generator_point() -> (point: EcPoint) {
    // generator_point = (
    //     0x79be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798,
    //     0x483ada7726a3c4655da4fbfc0e1108a8fd17b448a68554199c47d08ffb10d4b8
    // ).
    return (
        point=EcPoint(
            BigInt3(0xe28d959f2815b16f81798, 0xa573a1c2c1c0a6ff36cb7, 0x79be667ef9dcbbac55a06),
            BigInt3(0x554199c47d08ffb10d4b8, 0x2ff0384422a3f45ed1229a, 0x483ada7726a3c4655da4f),
        ),
    );
}

// Computes a * b^(-1) modulo the size of the elliptic curve (N).
//
// Prover assumptions:
// * All the limbs of a are in the range (-2 ** 210.99, 2 ** 210.99).
// * All the limbs of b are in the range (-2 ** 124.99, 2 ** 124.99).
// * b is in the range [0, 2 ** 256).
//
// Soundness assumptions:
// * The limbs of a are in the range (-2 ** 249, 2 ** 249).
// * The limbs of b are in the range (-2 ** 159.83, 2 ** 159.83).
func div_mod_n{range_check_ptr}(a: BigInt3, b: BigInt3) -> (res: BigInt3) {
    %{
        from starkware.cairo.common.cairo_secp.secp_utils import N, pack
        from starkware.python.math_utils import div_mod, safe_div

        a = pack(ids.a, PRIME)
        b = pack(ids.b, PRIME)
        value = res = div_mod(a, b, N)
    %}
    let (res) = nondet_bigint3();

    %{ value = k = safe_div(res * b - a, N) %}
    let (k) = nondet_bigint3();

    let (res_b) = bigint_mul(res, b);
    let n = BigInt3(N0, N1, N2);
    let (k_n) = bigint_mul(k, n);

    // We should now have res_b = k_n + a. Since the numbers are in unreduced form,
    // we should handle the carry.

    tempvar carry1 = (res_b.d0 - k_n.d0 - a.d0) / BASE;
    assert [range_check_ptr + 0] = carry1 + 2 ** 127;

    tempvar carry2 = (res_b.d1 - k_n.d1 - a.d1 + carry1) / BASE;
    assert [range_check_ptr + 1] = carry2 + 2 ** 127;

    tempvar carry3 = (res_b.d2 - k_n.d2 - a.d2 + carry2) / BASE;
    assert [range_check_ptr + 2] = carry3 + 2 ** 127;

    tempvar carry4 = (res_b.d3 - k_n.d3 + carry3) / BASE;
    assert [range_check_ptr + 3] = carry4 + 2 ** 127;

    assert res_b.d4 - k_n.d4 + carry4 = 0;

    let range_check_ptr = range_check_ptr + 4;

    return (res=res);
}

// Verifies that val is in the range [1, N) and that the limbs of val are in the range [0, BASE).
func validate_signature_entry{range_check_ptr}(val: BigInt3) {
    assert_nn_le(val.d2, N2);
    assert_nn_le(val.d1, BASE - 1);
    assert_nn_le(val.d0, BASE - 1);

    if (val.d2 == N2) {
        if (val.d1 == N1) {
            assert_nn_le(val.d0, N0 - 1);
            return ();
        }
        assert_nn_le(val.d1, N1 - 1);
        return ();
    }

    // Check that val > 0.
    if (val.d2 == 0) {
        if (val.d1 == 0) {
            assert_not_zero(val.d0);
            return ();
        }
    }
    return ();
}

// Converts a public key point to the corresponding Ethereum address.
func public_key_point_to_eth_address{
    range_check_ptr, bitwise_ptr: BitwiseBuiltin*, keccak_ptr: felt*
}(public_key_point: EcPoint) -> (eth_address: felt) {
    alloc_locals;
    let (local elements: Uint256*) = alloc();
    let (x_uint256: Uint256) = bigint_to_uint256(public_key_point.x);
    assert elements[0] = x_uint256;
    let (y_uint256: Uint256) = bigint_to_uint256(public_key_point.y);
    assert elements[1] = y_uint256;
    let (point_hash: Uint256) = keccak_uint256s_bigend(n_elements=2, elements=elements);

    // The Ethereum address is the 20 least significant bytes of the keccak of the public key.
    let (high_high, high_low) = unsigned_div_rem(point_hash.high, 2 ** 32);
    return (eth_address=point_hash.low + RC_BOUND * high_low);
}

// Returns a point on the secp256k1 curve with the given x coordinate. Chooses the y that has the
//   same parity as v (there are two y values that correspond to x, with different parities).
// Also verifies that v is in the range [0, 2 ** 128).
// Prover assumptions:
//   * x is the x coordinate of some nonzero point on the curve.
//   * The limbs of x are in the range (-2**87.99, 2**87.99).
// Soundness assumptions:
//   * The limbs of x are in the range (-2**106.99, 2**106.99).
func get_point_from_x{range_check_ptr}(x: BigInt3, v: felt) -> (point: EcPoint) {
    alloc_locals;
    with_attr error_message("Out of range v {v}.") {
        assert_nn(v);
    }
    let (x_square: UnreducedBigInt3) = unreduced_sqr(x);
    let (x_square_reduced: BigInt3) = reduce(x_square);
    let (x_cube: UnreducedBigInt3) = unreduced_mul(x, x_square_reduced);

    %{
        from starkware.cairo.common.cairo_secp.secp_utils import SECP_P, pack

        x_cube_int = pack(ids.x_cube, PRIME) % SECP_P
        y_square_int = (x_cube_int + ids.BETA) % SECP_P
        y = pow(y_square_int, (SECP_P + 1) // 4, SECP_P)

        # We need to decide whether to take y or SECP_P - y.
        if ids.v % 2 == y % 2:
            value = y
        else:
            value = (-y) % SECP_P
    %}
    let (local y: BigInt3) = nondet_bigint3();
    validate_reduced_field_element(y);

    // Check that y has same parity as v.
    assert_nn((y.d0 + v) / 2);

    let (y_square: UnreducedBigInt3) = unreduced_sqr(y);
    // Check that y_square = x_cube + BETA.
    verify_zero(
        UnreducedBigInt3(
            d0=x_cube.d0 + BETA - y_square.d0,
            d1=x_cube.d1 - y_square.d1,
            d2=x_cube.d2 - y_square.d2,
        ),
    );

    return (point=EcPoint(x, y));
}

// Receives a signature and the signed message hash.
// Returns the public key associated with the signer, represented as a point on the curve.
// Note:
//   Some places use the values 27 and 28 instead of 0 and 1 for v.
//   In that case, a subtraction by 27 returns a v that can be used by this function.
// Prover assumptions:
// * r is the x coordinate of some nonzero point on the curve.
// * All the limbs of s and msg_hash are in the range (-2 ** 210.99, 2 ** 210.99).
// * All the limbs of r are in the range (-2 ** 124.99, 2 ** 124.99).
func recover_public_key{range_check_ptr}(msg_hash: BigInt3, r: BigInt3, s: BigInt3, v: felt) -> (
    public_key_point: EcPoint
) {
    alloc_locals;
    let (local r_point: EcPoint) = get_point_from_x(x=r, v=v);
    let (generator_point: EcPoint) = get_generator_point();
    // The result is given by
    //   -(msg_hash / r) * gen + (s / r) * r_point
    // where the division by r is modulo N.

    let (u1: BigInt3) = div_mod_n(msg_hash, r);
    let (u2: BigInt3) = div_mod_n(s, r);

    let (point1) = ec_mul(generator_point, u1);
    // We prefer negating the point over negating the scalar because negating mod SECP_P is
    // computationally easier than mod N.
    let (minus_point1) = ec_negate(point1);

    let (point2) = ec_mul(r_point, u2);

    let (public_key_point) = ec_add(minus_point1, point2);
    return (public_key_point=public_key_point);
}

// Verifies a Secp256k1 ECDSA signature.
// Also verifies that r and s are in the range (0, N), that their limbs are in the range
//   [0, BASE), and that v is in the range [0, 2 ** 128).
// Receives a keccak_ptr for computing keccak. finalize_keccak should be called by the function's
//   caller after all the keccak calculations are done.
// Assumptions:
// * All the limbs of msg_hash are in the range [0, 3 * BASE).
func verify_eth_signature{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, keccak_ptr: felt*}(
    msg_hash: BigInt3, r: BigInt3, s: BigInt3, v: felt, eth_address: felt
) {
    alloc_locals;

    with_attr error_message("Signature out of range.") {
        validate_signature_entry(r);
        validate_signature_entry(s);
    }

    with_attr error_message("Invalid signature.") {
        let (public_key_point: EcPoint) = recover_public_key(msg_hash=msg_hash, r=r, s=s, v=v);
        let (calculated_eth_address) = public_key_point_to_eth_address(
            public_key_point=public_key_point
        );
        assert eth_address = calculated_eth_address;
    }
    return ();
}

// Same as verify_eth_signature, except that msg_hash, r and s are Uint256.
func verify_eth_signature_uint256{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, keccak_ptr: felt*}(
    msg_hash: Uint256, r: Uint256, s: Uint256, v: felt, eth_address: felt
) {
    let (msg_hash_bigint: BigInt3) = uint256_to_bigint(msg_hash);
    let (r_bigint: BigInt3) = uint256_to_bigint(r);
    let (s_bigint: BigInt3) = uint256_to_bigint(s);
    return verify_eth_signature(
        msg_hash=msg_hash_bigint, r=r_bigint, s=s_bigint, v=v, eth_address=eth_address
    );
}
