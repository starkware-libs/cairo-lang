# Functions for various actions on the STARK curve:
#   y^2 = x^3 + alpha * x + beta
# where alpha = 1 and beta = 0x6f21413efbe40de150e596d72f7a8c5609ad26c15c915c1f4cdfcb99cee9e89.
# The point at infinity is represented as (0, 0).

from starkware.cairo.common.cairo_builtins import EcOpBuiltin
from starkware.cairo.common.ec_point import EcPoint

const CURVE_ALPHA = 1
const CURVE_BETA = 0x6f21413efbe40de150e596d72f7a8c5609ad26c15c915c1f4cdfcb99cee9e89

# Asserts that an EC point is on the STARK curve.
#
# Arguments:
#   p - an EC point.
func assert_on_curve(p : EcPoint):
    # Because the curve order is odd, there is no point (except (0, 0), which represents the point
    # at infinity) with y = 0.
    if p.y == 0:
        assert p.x = 0
        return ()
    end
    tempvar rhs = (p.x * p.x + CURVE_ALPHA) * p.x + CURVE_BETA
    assert p.y * p.y = rhs
    return ()
end

# Doubles a point (computes p + p) on the elliptic curve.
#
# Arguments:
#   p - an EC point.
#
# Returns:
#   r = p + p.
#
# Assumptions:
#   p is a valid point on the curve.
func ec_double(p : EcPoint) -> (r : EcPoint):
    # (0, 0), which represents the point at infinity, is the only point with y = 0.
    if p.y == 0:
        return (r=p)
    end
    tempvar slope = (3 * p.x * p.x + CURVE_ALPHA) / (2 * p.y)
    tempvar r_x = slope * slope - p.x - p.x
    return (r=EcPoint(x=r_x, y=slope * (p.x - r_x) - p.y))
end

# Adds two points on the EC.
#
# Arguments:
#   p - an EC point.
#   q - an EC point.
#
# Returns:
#   r = p + q.
#
# Assumptions:
#   p and q are valid points on the curve.
func ec_add(p : EcPoint, q : EcPoint) -> (r : EcPoint):
    # (0, 0), which represents the point at infinity, is the only point with y = 0.
    if p.y == 0:
        return (r=q)
    end
    if q.y == 0:
        return (r=p)
    end
    if p.x == q.x:
        if p.y == q.y:
            return ec_double(p)
        end
        # In this case, because p and q are on the curve, p.y = -q.y.
        return (r=EcPoint(x=0, y=0))
    end
    tempvar slope = (p.y - q.y) / (p.x - q.x)
    tempvar r_x = slope * slope - p.x - q.x
    return (r=EcPoint(x=r_x, y=slope * (p.x - r_x) - p.y))
end

# Computes p + m * q on the elliptic curve.
# Because the EC operation builtin cannot handle inputs where additions of points with the same x
# coordinate arise during the computation, this function adds and subtracts a nondeterministic
# point s to the computation, so that regardless of input, the probability that such additions
# arise will become negligibly small.
# The precise computation is therefore:
# ((p + s) + m * q) - s
# so that the inputs to the builtin itself are (p + s), m, and q.
#
# Arguments:
#   ec_op_ptr - the ec_op builtin pointer.
#   p - an EC point.
#   m - the multiplication coefficient of Q.
#   q - an EC point.
#
# Returns:
#   r = p + m * q.
#
# Assumptions:
#   p and q are valid points on the curve.
func ec_op{ec_op_ptr : EcOpBuiltin*}(p : EcPoint, m : felt, q : EcPoint) -> (r : EcPoint):
    alloc_locals

    # (0, 0), which represents the point at infinity, is the only point with y = 0.
    if q.y == 0:
        return (r=p)
    end

    local s : EcPoint
    %{
        from starkware.crypto.signature.signature import ALPHA, BETA, FIELD_PRIME
        from starkware.python.math_utils import random_ec_point
        def to_bytes(n):
            return n.to_bytes(256, "little")

        # Define a seed for random_ec_point that's dependent on all the input, so that:
        #   (1) The added point s is deterministic.
        #   (2) It's hard to choose inputs for which the builtin will fail.
        seed = b"".join(map(to_bytes, [ids.p.x, ids.p.y, ids.m, ids.q.x, ids.q.y]))
        ids.s.x, ids.s.y = random_ec_point(FIELD_PRIME, ALPHA, BETA, seed)
    %}
    let p_plus_s : EcPoint = ec_add(p, s)

    assert ec_op_ptr.p = p_plus_s
    assert ec_op_ptr.m = m
    assert ec_op_ptr.q = q
    let r : EcPoint = ec_add(ec_op_ptr.r, EcPoint(x=s.x, y=-s.y))
    let ec_op_ptr = ec_op_ptr + EcOpBuiltin.SIZE
    return (r=r)
end
