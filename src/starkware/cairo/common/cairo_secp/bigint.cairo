from starkware.cairo.common.cairo_secp.constants import BASE
from starkware.cairo.common.math import assert_nn, assert_nn_le, unsigned_div_rem
from starkware.cairo.common.math_cmp import RC_BOUND
from starkware.cairo.common.uint256 import Uint256

# Represents a big integer defined by:
#   d0 + BASE * d1 + BASE**2 * d2.
# Note that the limbs (d_i) are NOT restricted to the range [0, BASE) and in particular they
# can be negative.
# In most cases this is used to represent a secp256k1 field element.
struct UnreducedBigInt3:
    member d0 : felt
    member d1 : felt
    member d2 : felt
end

# Same as UnreducedBigInt3, except that d0, d1 and d2 must be in the range [0, 3 * BASE).
# In most cases this is used to represent a secp256k1 field element.
struct BigInt3:
    member d0 : felt
    member d1 : felt
    member d2 : felt
end

# Represents a big integer defined by:
#   sum_i(BASE**i * d_i).
# Note that the limbs (d_i) are NOT restricted to the range [0, BASE) and in particular they
# can be negative.
struct UnreducedBigInt5:
    member d0 : felt
    member d1 : felt
    member d2 : felt
    member d3 : felt
    member d4 : felt
end

# Computes the multiplication of two big integers, given in BigInt3 representation.
#
# Arguments:
#   x, y - the two BigInt3 to operate on.
#
# Returns:
#   x * y in an UnreducedBigInt5 representation.
func bigint_mul(x : BigInt3, y : BigInt3) -> (res : UnreducedBigInt5):
    return (
        UnreducedBigInt5(
        d0=x.d0 * y.d0,
        d1=x.d0 * y.d1 + x.d1 * y.d0,
        d2=x.d0 * y.d2 + x.d1 * y.d1 + x.d2 * y.d0,
        d3=x.d1 * y.d2 + x.d2 * y.d1,
        d4=x.d2 * y.d2),
    )
end

# Returns a BigInt3 instance whose value is controlled by a prover hint.
#
# Soundness guarantee: each limb is in the range [0, 3 * BASE).
# Completeness guarantee (honest prover): the value is in reduced form and in particular,
# each limb is in the range [0, BASE).
#
# Implicit arguments:
#   range_check_ptr - range check builtin pointer.
#
# Hint arguments: value.
func nondet_bigint3{range_check_ptr}() -> (res : BigInt3):
    # The result should be at the end of the stack after the function returns.
    let res : BigInt3 = [cast(ap + 5, BigInt3*)]
    %{
        from starkware.cairo.common.cairo_secp.secp_utils import split

        segments.write_arg(ids.res.address_, split(value))
    %}
    # The maximal possible sum of the limbs, assuming each of them is in the range [0, BASE).
    const MAX_SUM = 3 * (BASE - 1)
    assert [range_check_ptr] = MAX_SUM - (res.d0 + res.d1 + res.d2)

    # Prepare the result at the end of the stack.
    tempvar range_check_ptr = range_check_ptr + 4
    [range_check_ptr - 3] = res.d0; ap++
    [range_check_ptr - 2] = res.d1; ap++
    [range_check_ptr - 1] = res.d2; ap++
    static_assert &res + BigInt3.SIZE == ap
    return (res=res)
end

# Converts a BigInt3 instance into a Uint256.
#
# Assumptions:
# * The limbs of x are in the range [0, BASE * 3).
# * x is in the range [0, 2 ** 256).
# * PRIME is at least 174 bits.
# Implicit arguments:
#   range_check_ptr - range check builtin pointer.
func bigint_to_uint256{range_check_ptr}(x : BigInt3) -> (res : Uint256):
    let low = [range_check_ptr]
    let high = [range_check_ptr + 1]
    let range_check_ptr = range_check_ptr + 2
    %{ ids.low = (ids.x.d0 + ids.x.d1 * ids.BASE) & ((1 << 128) - 1) %}
    # Because PRIME is at least 174 bits, the numerator doesn't overflow.
    tempvar a = ((x.d0 + x.d1 * BASE) - low) / RC_BOUND
    const D2_SHIFT = BASE * BASE / RC_BOUND
    const A_BOUND = 4 * D2_SHIFT
    # We'll check that the division in `a` doesn't cause an overflow. This means that the 128 LSB
    # of (x.d0 + x.d1 * BASE) and low are identical, which ensures that low is correct.
    assert_nn_le(a, A_BOUND - 1)
    # high * RC_BOUND = a * RC_BOUND + x.d2 * BASE ** 2 =
    #   = x.d0 + x.d1 * BASE + x.d2 * BASE ** 2 - low = num - low.
    with_attr error_message("x out of range"):
        assert high = a + x.d2 * D2_SHIFT
    end

    return (res=Uint256(low=low, high=high))
end

# Converts a Uint256 instance into a BigInt3.
# Assuming x is a valid Uint256 (its two limbs are below 2 ** 128), the resulting number will have
#   limbs in the range [0, BASE).
func uint256_to_bigint{range_check_ptr}(x : Uint256) -> (res : BigInt3):
    const D1_HIGH_BOUND = BASE ** 2 / RC_BOUND
    const D1_LOW_BOUND = RC_BOUND / BASE
    let (d1_low, d0) = unsigned_div_rem(x.low, BASE)
    let (d2, d1_high) = unsigned_div_rem(x.high, D1_HIGH_BOUND)
    let d1 = d1_high * D1_LOW_BOUND + d1_low
    return (BigInt3(d0=d0, d1=d1, d2=d2))
end
