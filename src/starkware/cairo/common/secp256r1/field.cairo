from starkware.cairo.common.cairo_secp.bigint3 import BigInt3, SumBigInt3, UnreducedBigInt3
from starkware.cairo.common.math import assert_nn_le
from starkware.cairo.common.secp256r1.bigint import nondet_bigint3
from starkware.cairo.common.secp256r1.constants import (
    BASE,
    BASE3_MOD_P0,
    BASE3_MOD_P1,
    BASE3_MOD_P2,
    BASE4_MOD_P0,
    BASE4_MOD_P1,
    BASE4_MOD_P2,
    P0,
    P1,
    P2,
    SECP_REM0,
    SECP_REM1,
    SECP_REM2,
)

// Computes the multiplication of two big integers, given in BigInt3 representation, modulo the
// secp256r1 prime.
//
// Arguments:
//   a, b - the two BigInt3 to operate on.
//
// Returns:
//   a * b in an UnreducedBigInt3 representation (the returned limbs are unreduced).
//

// If the most significant limb of each input is in the range (-x, x), and the other limbs
// are in the range (-8x, 8x) the result's limbs are guaranteed to be in the range
// (-x**2 * (2 ** 76.01), x**2 * (2 ** 76.01)).
//
// This means that if unreduced_mul is called on the results of nondet_bigint3, or the difference
// between two such results, the limbs of the result are in the range (-2**244.01, 2****244.01).
func unreduced_mul(a: BigInt3, b: BigInt3) -> (res_low: UnreducedBigInt3) {
    tempvar limb0 = a.d0 * b.d0;  // < (8x)*(8x).
    tempvar limb1 = a.d0 * b.d1 + a.d1 * b.d0;  // < 2*(8x)*(8x).
    tempvar limb2 = a.d0 * b.d2 + a.d1 * b.d1 + a.d2 * b.d0;  // < x*(8x) + (8x)*(8x) + x*(8x).
    tempvar limb3 = a.d1 * b.d2 + a.d2 * b.d1;  // < (8x)*x+x*(8x) = 2*(8x)*x.
    tempvar limb4 = a.d2 * b.d2;  // < x*x.

    // The result of the product is:
    //   sum_{i, j} a.d_i * b.d_j * BASE**(i + j)
    // Since we are computing it mod secp256r1_prime, we replace
    // BASE**3 with BASE3_MOD_P and BASE**4 with BASE3_MOD_P4.

    // Assuming the input limbs are as in the documentation of the function:
    // |d0| < (8x)*(8x) + 4*2*(8x)*x + 2**56*x*x  < 2**56.01 * x**2
    // |d1| < 2*(8x)*(8x) + (2**12)*2*(8x)*x + (2**66 - 4)*x*x < 2**66.01 * x**2
    // |d2| < x*(8x) + (8x)*(8x) + (8x)*x + (2**54 - 2**22)*2*(8x)*x + (2**76 + 2**12)*x*x <
    // 2**76.01 * x**2.

    return (
        UnreducedBigInt3(
            d0=limb0 + BASE3_MOD_P0 * limb3 + BASE4_MOD_P0 * limb4,
            d1=limb1 + BASE3_MOD_P1 * limb3 + BASE4_MOD_P1 * limb4,
            d2=limb2 + BASE3_MOD_P2 * limb3 + BASE4_MOD_P2 * limb4,
        ),
    );
}

// Computes the square of a big integer, given in BigInt3 representation, modulo the
// secp256r1 prime.
//
// Has the same guarantees as in unreduced_mul(a, a).
func unreduced_sqr(a: BigInt3) -> (res_low: UnreducedBigInt3) {
    tempvar twice_d0 = a.d0 + a.d0;
    tempvar d1d2 = a.d1 * a.d2;
    tempvar limb0 = a.d0 * a.d0;
    tempvar limb1 = twice_d0 * a.d1;
    tempvar limb2 = a.d2 * twice_d0 + a.d1 * a.d1;
    tempvar limb3 = d1d2 + d1d2;
    tempvar limb4 = a.d2 * a.d2;

    return (
        UnreducedBigInt3(
            d0=limb0 + BASE3_MOD_P0 * limb3 + BASE4_MOD_P0 * limb4,
            d1=limb1 + BASE3_MOD_P1 * limb3 + BASE4_MOD_P1 * limb4,
            d2=limb2 + BASE3_MOD_P2 * limb3 + BASE4_MOD_P2 * limb4,
        ),
    );
}

// Asserts that 'value' is in the range [0, 2**165).
@known_ap_change
func assert_165_bit{range_check_ptr}(value) {
    const UPPER_BOUND = 2 ** 165;
    const SHIFT = 2 ** 128;
    const HIGH_BOUND = UPPER_BOUND / SHIFT;

    let low = [range_check_ptr];
    let high = [range_check_ptr + 1];

    %{
        from starkware.cairo.common.math_utils import as_int

        # Correctness check.
        value = as_int(ids.value, PRIME) % PRIME
        assert value < ids.UPPER_BOUND, f'{value} is outside of the range [0, 2**165).'

        # Calculation for the assertion.
        ids.high, ids.low = divmod(ids.value, ids.SHIFT)
    %}

    // Copy high to a tempvar it going to be used twice.
    tempvar high = high;
    assert [range_check_ptr + 2] = high + (SHIFT - HIGH_BOUND);

    assert value = high * SHIFT + low;
    let range_check_ptr = range_check_ptr + 3;
    return ();
}

// Verifies that the given unreduced value is equal to zero modulo the secp256r1 prime.
//
// Completeness assumption: val's limbs are in the range (-2**247.99, 2**247.99).
// Soundness assumption: val's limbs are in the range (-2**249.99, 2**249.99).
func verify_zero{range_check_ptr}(val: UnreducedBigInt3) {
    alloc_locals;

    // The show that `val = 0 mod secp256r1`, we show that there is a `q` such that
    // val.d2*BASE**2 + val.d1 * BASE + val.d0 = q * secp256r1.
    local q;
    %{
        from starkware.cairo.common.cairo_secp.secp256r1_utils import SECP256R1_P
        from starkware.cairo.common.cairo_secp.secp_utils import pack

        q, r = divmod(pack(ids.val, PRIME), SECP256R1_P)
        assert r == 0, f"verify_zero: Invalid input {ids.val.d0, ids.val.d1, ids.val.d2}."
        ids.q = q % PRIME
    %}

    // Assuming the absolute values of the limbs are bounded by 2**247.99, the absolute value
    // of q = (val.d2 * BASE**2 + val.d1 * BASE + val.d0) / secp256r1, is bounded by
    // 2**247.995 * (2 ** 86)**2 / 2**255.995 = 2**164.
    assert_165_bit(q + 2 ** 164);

    tempvar r1 = (val.d0 + q * SECP_REM0) / BASE;
    assert_165_bit(r1 + 2 ** 164);
    // r1 in [-2**164, 2**164) => r1 * BASE is in the range [-2**250, 2**250).
    // so r1 * BASE = val.d0 + q*SECP_REM0 in the integers.

    tempvar r2 = (val.d1 + q * SECP_REM1 + r1) / BASE;
    assert_165_bit(r2 + 2 ** 164);
    // r2 in [-2**164, 2**164) following the same as above,
    // r2 * BASE = val.d1 + q*SECP_REM1 + r1 in the integers
    // so r2 * BASE ** 2 = val.d1 * BASE + q*SECP_REM1 * BASE + r1 * BASE.

    assert val.d2 + q * SECP_REM2 = q * (BASE / 4) - r2;
    // Similarly, this implies that val.d2 = q * BASE / 4 - r2 (as integers).
    // Therefore,
    // val.d2*BASE**2 + q * SECP_REM2*BASE**2
    //     = q * (2**256) - val.d1 * BASE + q*SECP_REM1 * BASE + val.d0 + q*SECP_REM0
    // Hence, val = q * (BASE**3 / 4 - SECP_REM) = q * (2**256 - SECP_REM) = q * secp256k1_prime.

    return ();
}

// Returns 1 if x == 0 (mod secp256r1_prime), and 0 otherwise.
//
// We assume that 'x' satisfies the bounds of nondet_bigint3, or that it is the sum or difference
// of two such values.
func is_zero{range_check_ptr}(x: SumBigInt3) -> (res: felt) {
    %{
        from starkware.cairo.common.cairo_secp.secp256r1_utils import SECP256R1_P
        from starkware.cairo.common.cairo_secp.secp_utils import pack

        x = pack(ids.x, PRIME) % SECP256R1_P
    %}
    if (nondet %{ x == 0 %} != 0) {
        verify_zero(UnreducedBigInt3(d0=x.d0, d1=x.d1, d2=x.d2));
        return (res=1);
    }

    %{
        from starkware.python.math_utils import div_mod

        value = div_mod(1, x, SECP256R1_P)
    %}
    let (x_inv) = nondet_bigint3();
    // Note that we pass `SumBigInt3` to `unreduced_mul` so the bounds on
    // `x_x_inv` are (-2**245.01, 2**245.01).
    let (x_x_inv) = unreduced_mul(BigInt3(d0=x.d0, d1=x.d1, d2=x.d2), x_inv);

    // Check that x * x_inv = 1 to verify that x != 0.
    verify_zero(UnreducedBigInt3(d0=x_x_inv.d0 - 1, d1=x_x_inv.d1, d2=x_x_inv.d2));
    return (res=0);
}

// Receives an unreduced number, and returns a number that is equal to the original number mod
// SECP256R1_P and in reduced form.
//
// Has the same guarantees as verify_zero(x).
func reduce{range_check_ptr}(x: UnreducedBigInt3) -> (reduced_x: BigInt3) {
    let orig_x = x;

    %{
        from starkware.cairo.common.cairo_secp.secp256r1_utils import SECP256R1_P
        from starkware.cairo.common.cairo_secp.secp_utils import pack
        value = pack(ids.x, PRIME) % SECP256R1_P
    %}

    let (reduced_x: BigInt3) = nondet_bigint3();

    verify_zero(
        UnreducedBigInt3(
            d0=orig_x.d0 - reduced_x.d0, d1=orig_x.d1 - reduced_x.d1, d2=orig_x.d2 - reduced_x.d2
        ),
    );
    return (reduced_x=reduced_x);
}

// Verifies that val is in the range [0, p) (where p is secp256r1 prime) and that the limbs of
// val are in the range [0, BASE). This guarantees unique representation.
func validate_reduced_field_element{range_check_ptr}(val: BigInt3) {
    assert_nn_le(val.d2, P2);
    assert_nn_le(val.d1, BASE - 1);
    assert_nn_le(val.d0, BASE - 1);

    if (val.d2 == P2) {
        if (val.d1 == P1) {
            assert_nn_le(val.d0, P0 - 1);
            return ();
        }
        assert_nn_le(val.d1, P1 - 1);
        return ();
    }
    return ();
}
