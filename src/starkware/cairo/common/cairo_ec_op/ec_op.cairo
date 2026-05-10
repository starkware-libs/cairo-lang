from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import EcOpBuiltin
from starkware.cairo.common.ec import StarkCurve, assert_on_curve, ec_add, ec_sub
from starkware.cairo.common.ec_point import EcPoint
from starkware.cairo.common.math import assert_not_zero
from starkware.cairo.common.memset import memset

// The maximal number of bits allowed in the scalar m.
const M_MAX_BITS = 252;

// Computes m * p where m is a scalar and p is a point on the STARK elliptic curve.
//
// Arguments:
//   ec_op_ptr - the ec_op builtin pointer.
//   p - an EC point.
//   m - the multiplication coefficient of p.
//
// Returns:
//   r = m * p.
//
// Assumptions:
//   p is a valid point on the curve.
func ec_mul_cairo(m: felt, p: EcPoint) -> (r: EcPoint) {
    alloc_locals;

    // (0, 0), which represents the point at infinity, is the only point with y = 0.
    if (p.y == 0) {
        return (r=p);
    }

    // Define `q` for the following hint to work.
    let q = p;

    local s: EcPoint;
    %{
        from starkware.crypto.signature.signature import ALPHA, BETA, FIELD_PRIME
        from starkware.python.math_utils import random_ec_point
        from starkware.python.utils import to_bytes

        # Define a seed for random_ec_point that's dependent on all the input, so that:
        #   (1) The added point s is deterministic.
        #   (2) It's hard to choose inputs for which the builtin will fail.
        seed = b"".join(map(to_bytes, [ids.p.x, ids.p.y, ids.m, ids.q.x, ids.q.y]))
        ids.s.x, ids.s.y = random_ec_point(FIELD_PRIME, ALPHA, BETA, seed)
    %}
    assert_on_curve(s);

    let (r_plus_s) = simulate_builtin_ec_op_with_cairo(p=s, m=m, q=p);
    let r: EcPoint = ec_sub(r_plus_s, s);
    return (r=r);
}

// Returns the result of the EC operation P + m * Q.
// where P = (p_x, p_y), Q = (q_x, q_y) are points on the elliptic curve defined as
// y^2 = x^3 + alpha * x + beta (mod prime).
//
// Mimics the operation of the AIR, so that this function fails whenever the builtin AIR
// would not yield a correct result, i.e. when any part of the computation attempts to add
// two points with the same x coordinate.
func simulate_builtin_ec_op_with_cairo(p: EcPoint, m: felt, q: EcPoint) -> (r: EcPoint) {
    alloc_locals;
    // Assert that the points are on the curve and are not the point at infinity.
    assert p.y * p.y = (p.x * p.x + StarkCurve.ALPHA) * p.x + StarkCurve.BETA;
    assert q.y * q.y = (q.x * q.x + StarkCurve.ALPHA) * q.x + StarkCurve.BETA;

    let (local m_bit_unpacking: felt*) = alloc();  // Starts from lsb.
    %{
        curr_m = ids.m
        for i in range(ids.M_MAX_BITS):
            memory[ids.m_bit_unpacking + i] = curr_m % 2
            curr_m = curr_m >> 1
    %}

    // Verify that the bit unpacking is of a number num smaller than PRIME.
    verify_bit_unpacking_is_reduced(unpacking=m_bit_unpacking);

    // Compute the result.
    let result = _ec_op_inner(
        partial_sum=p, doubled_point=q, m_bit_unpacking=m_bit_unpacking, index=0, curr_m=m
    );

    // Assert that the result is on the curve.
    assert_on_curve(p=result);

    // Output the result.
    return (r=result);
}

// Computes the EC operation partial_sum + curr_m * doubled_point.
// It is called recursively, with the recursion being terminated when the index reaches M_MAX_BITS.
// The function also verifies that the bit unpacking is indeed of curr_m (modulo PRIME).
func _ec_op_inner(
    partial_sum: EcPoint, doubled_point: EcPoint, m_bit_unpacking: felt*, index: felt, curr_m: felt
) -> EcPoint {
    alloc_locals;
    if (index == M_MAX_BITS) {
        assert curr_m = 0;
        return partial_sum;
    }

    tempvar x_diff = doubled_point.x - partial_sum.x;
    assert_not_zero(x_diff);

    if (m_bit_unpacking[0] == 0) {
        tempvar partial_sum = partial_sum;
    } else {
        // Inline ec_add for input p=partial_sum, q=doubled_point.
        // Note: no need to compare doubled_point.y to 0 since simulate_builtin_ec_op_with_cairo
        // has already verified that p is not the point at infinity and every time partial_sum
        // gets updated, it is the addition of two points with different x coordinates.
        // We also do not need to address the case where partial_sum.x == doubled_point.x because
        // we have already verified that it is not the case.
        assert m_bit_unpacking[0] = 1;
        tempvar slope = (doubled_point.y - partial_sum.y) / x_diff;
        tempvar r_x = slope * slope - partial_sum.x - doubled_point.x;
        tempvar partial_sum = EcPoint(x=r_x, y=slope * (partial_sum.x - r_x) - partial_sum.y);
    }

    // Inline ec_double for input p=doubled_point.
    // Note: we do not need to compare doubled_point.y to 0 since simulate_builtin_ec_op_with_cairo
    // has already verified that q is not the point at infinity and doubled_point = 2**index * q
    // and the EC group is of an odd order.
    tempvar slope = (3 * doubled_point.x * doubled_point.x + StarkCurve.ALPHA) / (
        doubled_point.y + doubled_point.y
    );
    tempvar r_x = slope * slope - doubled_point.x - doubled_point.x;
    local doubled_point: EcPoint = EcPoint(
        x=r_x, y=slope * (doubled_point.x - r_x) - doubled_point.y
    );

    tempvar x_diff = doubled_point.x - partial_sum.x;
    assert_not_zero(x_diff);

    if (m_bit_unpacking[1] == 0) {
        tempvar partial_sum = partial_sum;
    } else {
        // Inline ec_add for input p=partial_sum, q=doubled_point.
        assert m_bit_unpacking[1] = 1;
        tempvar slope = (doubled_point.y - partial_sum.y) / x_diff;
        tempvar r_x = slope * slope - partial_sum.x - doubled_point.x;
        tempvar partial_sum = EcPoint(x=r_x, y=slope * (partial_sum.x - r_x) - partial_sum.y);
    }

    // Inline ec_double for input p=doubled_point.
    tempvar slope = (3 * doubled_point.x * doubled_point.x + StarkCurve.ALPHA) / (
        doubled_point.y + doubled_point.y
    );
    tempvar r_x = slope * slope - doubled_point.x - doubled_point.x;
    let doubled_point: EcPoint = EcPoint(
        x=r_x, y=slope * (doubled_point.x - r_x) - doubled_point.y
    );

    return _ec_op_inner(
        partial_sum=partial_sum,
        doubled_point=doubled_point,
        m_bit_unpacking=m_bit_unpacking + 2,
        index=index + 2,
        curr_m=(curr_m - m_bit_unpacking[0] - m_bit_unpacking[1] - m_bit_unpacking[1]) / 4,
    );
}

// Asserts that the bit unpacking is of a number num smaller than PRIME.
func verify_bit_unpacking_is_reduced(unpacking: felt*) {
    // The four bits set to one in binary representation of the Stone prime, from most significant
    // to least significant.
    const P_ONE_BIT_POS_1 = 251;
    const P_ONE_BIT_POS_2 = 196;
    const P_ONE_BIT_POS_3 = 192;
    const P_ONE_BIT_POS_4 = 0;
    if (unpacking[P_ONE_BIT_POS_1] == 0) {
        return ();
    }
    memset(dst=&unpacking[P_ONE_BIT_POS_2 + 1], value=0, n=P_ONE_BIT_POS_1 - P_ONE_BIT_POS_2 - 1);
    if (unpacking[P_ONE_BIT_POS_2] == 0) {
        return ();
    }
    memset(dst=&unpacking[P_ONE_BIT_POS_3 + 1], value=0, n=P_ONE_BIT_POS_2 - P_ONE_BIT_POS_3 - 1);
    if (unpacking[P_ONE_BIT_POS_3] == 0) {
        return ();
    }
    memset(dst=&unpacking[P_ONE_BIT_POS_4 + 1], value=0, n=P_ONE_BIT_POS_3 - P_ONE_BIT_POS_4 - 1);
    assert unpacking[P_ONE_BIT_POS_4] = 0;
    return ();
}
