// Functions for various actions on the STARK curve:
//   y^2 = x^3 + alpha * x + beta
// where alpha = 1 and beta = 0x6f21413efbe40de150e596d72f7a8c5609ad26c15c915c1f4cdfcb99cee9e89.
// The point at infinity is represented as (0, 0).

from starkware.cairo.common.cairo_builtins import EcOpBuiltin
from starkware.cairo.common.ec_point import EcPoint
from starkware.cairo.common.math import is_quad_residue

namespace StarkCurve {
    const ALPHA = 1;
    const BETA = 0x6f21413efbe40de150e596d72f7a8c5609ad26c15c915c1f4cdfcb99cee9e89;
    const ORDER = 0x800000000000010ffffffffffffffffb781126dcae7b2321e66a241adc64d2f;
    const GEN_X = 0x1ef15c18599971b7beced415a40f0c7deacfd9b0d1819e03d723d8bc943cfca;
    const GEN_Y = 0x5668060aa49730b7be4801df46ec62de53ecd11abe43a32873000c36e8dc1f;
}

// Asserts that an EC point is on the STARK curve.
//
// Arguments:
//   p - an EC point.
func assert_on_curve(p: EcPoint) {
    // Because the curve order is odd, there is no point (except (0, 0), which represents the point
    // at infinity) with y = 0.
    if (p.y == 0) {
        assert p.x = 0;
        return ();
    }
    tempvar rhs = (p.x * p.x + StarkCurve.ALPHA) * p.x + StarkCurve.BETA;
    assert p.y * p.y = rhs;
    return ();
}

// Doubles a point (computes p + p) on the elliptic curve.
//
// Arguments:
//   p - an EC point.
//
// Returns:
//   r = p + p.
//
// Assumptions:
//   p is a valid point on the curve.
func ec_double(p: EcPoint) -> (r: EcPoint) {
    // (0, 0), which represents the point at infinity, is the only point with y = 0.
    if (p.y == 0) {
        return (r=p);
    }
    tempvar slope = (3 * p.x * p.x + StarkCurve.ALPHA) / (2 * p.y);
    tempvar r_x = slope * slope - p.x - p.x;
    return (r=EcPoint(x=r_x, y=slope * (p.x - r_x) - p.y));
}

// Adds two points on the EC.
//
// Arguments:
//   p - an EC point.
//   q - an EC point.
//
// Returns:
//   r = p + q.
//
// Assumptions:
//   p and q are valid points on the curve.
func ec_add(p: EcPoint, q: EcPoint) -> (r: EcPoint) {
    // (0, 0), which represents the point at infinity, is the only point with y = 0.
    if (p.y == 0) {
        return (r=q);
    }
    if (q.y == 0) {
        return (r=p);
    }
    if (p.x == q.x) {
        if (p.y == q.y) {
            return ec_double(p);
        }
        // In this case, because p and q are on the curve, p.y = -q.y.
        return (r=EcPoint(x=0, y=0));
    }
    tempvar slope = (p.y - q.y) / (p.x - q.x);
    tempvar r_x = slope * slope - p.x - q.x;
    return (r=EcPoint(x=r_x, y=slope * (p.x - r_x) - p.y));
}

// Subtracts a point from another on the EC.
//
// Arguments:
//   p - an EC point.
//   q - an EC point.
//
// Returns:
//   r = p - q.
//
// Assumptions:
//   p and q are valid points on the curve.
func ec_sub(p: EcPoint, q: EcPoint) -> (r: EcPoint) {
    return ec_add(p=p, q=EcPoint(x=q.x, y=-q.y));
}

// Computes p + m * q on the elliptic curve.
// Because the EC operation builtin cannot handle inputs where additions of points with the same x
// coordinate arise during the computation, this function adds and subtracts a nondeterministic
// point s to the computation, so that regardless of input, the probability that such additions
// arise will become negligibly small.
// The precise computation is therefore:
// ((p + s) + m * q) - s
// so that the inputs to the builtin itself are (p + s), m, and q.
//
// Arguments:
//   ec_op_ptr - the ec_op builtin pointer.
//   p - an EC point.
//   m - the multiplication coefficient of Q.
//   q - an EC point.
//
// Returns:
//   r = p + m * q.
//
// Assumptions:
//   p and q are valid points on the curve.
func ec_op{ec_op_ptr: EcOpBuiltin*}(p: EcPoint, m: felt, q: EcPoint) -> (r: EcPoint) {
    alloc_locals;

    // (0, 0), which represents the point at infinity, is the only point with y = 0.
    if (q.y == 0) {
        return (r=p);
    }

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
    let p_plus_s: EcPoint = ec_add(p, s);

    assert ec_op_ptr.p = p_plus_s;
    assert ec_op_ptr.m = m;
    assert ec_op_ptr.q = q;
    let r: EcPoint = ec_add(ec_op_ptr.r, EcPoint(x=s.x, y=-s.y));
    let ec_op_ptr = ec_op_ptr + EcOpBuiltin.SIZE;
    return (r=r);
}

// Computes m * p on the elliptic curve.
//
// Arguments:
//   ec_op_ptr - the ec_op builtin pointer.
//   m - the multiplication coefficient of p.
//   p - an EC point.
//
// Returns:
//   r = m * p.
//
// Assumptions:
//   p is a valid point on the curve.
func ec_mul{ec_op_ptr: EcOpBuiltin*}(m: felt, p: EcPoint) -> (r: EcPoint) {
    return ec_op(p=EcPoint(x=0, y=0), m=m, q=p);
}

// Computes p + m[0] * q[0] + m[1] * q[1] + ... m[len - 1] * q[len - 1] on the elliptic curve.
// Because the EC operation builtin cannot handle inputs where additions of points with the same x
// coordinate arise during the computation, this function adds and removes a nondeterministic
// point s to the computation, so that regardless of input, the probability that such additions
// arise will become negligibly small.
// The precise computation is therefore:
// ((p + s) + m[0] * q[0] + m[1] + q[1] + ... + m[len - 1] * q[len - 1]) - s.
//
// Arguments:
//   ec_op_ptr - the ec_op builtin pointer.
//   p - an EC point.
//   m - an array of multiplication coefficients.
//   q - an array of EC points.
//   len - the number of points in q.
//
// Returns:
//   r = p + m[0] * q[0] + m[1] * q[1] + ... + m[len - 1] * q[len - 1].
// Assumptions:
//   * All given EC points are on the STARK curve.
//   * len <= 1000.
func chained_ec_op{ec_op_ptr: EcOpBuiltin*}(p: EcPoint, m: felt*, q: EcPoint*, len: felt) -> (
    r: EcPoint
) {
    alloc_locals;
    local s: EcPoint;
    %{
        from starkware.crypto.signature.signature import ALPHA, BETA, FIELD_PRIME
        from starkware.python.math_utils import random_ec_point
        from starkware.python.utils import to_bytes

        n_elms = ids.len
        assert isinstance(n_elms, int) and n_elms >= 0, \
            f'Invalid value for len. Got: {n_elms}.'
        if '__chained_ec_op_max_len' in globals():
            assert n_elms <= __chained_ec_op_max_len, \
                f'chained_ec_op() can only be used with len<={__chained_ec_op_max_len}. ' \
                f'Got: n_elms={n_elms}.'

        # Define a seed for random_ec_point that's dependent on all the input, so that:
        #   (1) The added point s is deterministic.
        #   (2) It's hard to choose inputs for which the builtin will fail.
        seed = b"".join(
            map(
                to_bytes,
                [
                    ids.p.x,
                    ids.p.y,
                    *memory.get_range(ids.m, n_elms),
                    *memory.get_range(ids.q.address_, 2 * n_elms),
                ],
            )
        )
        ids.s.x, ids.s.y = random_ec_point(FIELD_PRIME, ALPHA, BETA, seed)
    %}
    let p_plus_s: EcPoint = ec_add(p, s);
    let r_plus_s: EcPoint = _chained_ec_op_inner(p=p_plus_s, m=m, q=q, len=len);
    let r: EcPoint = ec_add(r_plus_s, EcPoint(x=s.x, y=-s.y));
    return (r=r);
}

func _chained_ec_op_inner{ec_op_ptr: EcOpBuiltin*}(
    p: EcPoint, m: felt*, q: EcPoint*, len: felt
) -> (r: EcPoint) {
    if (len == 0) {
        return (r=p);
    }
    // (0, 0), representing the point at infinity, is the only point for which y = 0.
    if (q.y == 0) {
        return _chained_ec_op_inner(p=p, m=&m[1], q=&q[1], len=len - 1);
    }
    assert ec_op_ptr.p = p;
    assert ec_op_ptr.m = m[0];
    assert ec_op_ptr.q = q[0];
    let r = ec_op_ptr.r;
    let ec_op_ptr = &ec_op_ptr[1];
    return _chained_ec_op_inner(p=r, m=&m[1], q=&q[1], len=len - 1);
}

// Recovers the y coordinate of a point on the EC.
//
// Arguments:
//   x - the x coordinate of an EC point.
//
// Returns:
//   p - one of the two EC points with the given x coordinate (x, y).
//
// Assumptions:
//   There exists y such that (x, y) is on the curve. Otherwise the function's hint will throw a
//   python exception.
//
// Note:
//   This function will fail on x = 0 because there is no such point on the curve. The point at
//   infinity is represented as (0, 0), but this is just a representation, not actual coordinates.
func recover_y(x: felt) -> (p: EcPoint) {
    alloc_locals;
    local p: EcPoint;
    %{
        from starkware.crypto.signature.signature import ALPHA, BETA, FIELD_PRIME
        from starkware.python.math_utils import recover_y
        ids.p.x = ids.x
        # This raises an exception if `x` is not on the curve.
        ids.p.y = recover_y(ids.x, ALPHA, BETA, FIELD_PRIME)
    %}
    assert p.x = x;
    assert_on_curve(p);
    return (p=p);
}

// Checks if `x` represents the x coordinate of a point on the curve.
//
// Arguments:
//   x - a field element.
//
// Returns:
//   res - TRUE if `x` represents the x coordinate of a point on the curve, FALSE otherwise.
// Note:
//   Returns FALSE on x = 0 because there is no such point on the curve. The point at
//   infinity is represented as (0, 0), but this is just a representation, not actual coordinates.
func is_x_on_curve(x: felt) -> felt {
    return is_quad_residue(x=x * x * x + StarkCurve.ALPHA * x + StarkCurve.BETA);
}
