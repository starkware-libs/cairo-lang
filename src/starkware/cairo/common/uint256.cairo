from starkware.cairo.common.math import assert_nn_le, assert_not_zero
from starkware.cairo.common.math_cmp import is_le

# Represents an integer in the range [0, 2^256).
struct Uint256:
    # The low 128 bits of the value.
    member low : felt
    # The high 128 bits of the value.
    member high : felt
end

const SHIFT = 2 ** 128
const HALF_SHIFT = 2 ** 64

# Verifies that the given integer is valid.
func uint256_check{range_check_ptr}(a : Uint256):
    [range_check_ptr] = a.low
    [range_check_ptr + 1] = a.high
    let range_check_ptr = range_check_ptr + 2
    return ()
end

# Arithmetics.

# Adds two integers. Returns the result as a 256-bit integer and the (1-bit) carry.
func uint256_add{range_check_ptr}(a : Uint256, b : Uint256) -> (res : Uint256, carry : felt):
    alloc_locals
    local res : Uint256
    local carry_low : felt
    local carry_high : felt
    %{
        sum_low = ids.a.low + ids.b.low
        ids.carry_low = 1 if sum_low >= ids.SHIFT else 0
        sum_high = ids.a.high + ids.b.high + ids.carry_low
        ids.carry_high = 1 if sum_high >= ids.SHIFT else 0
    %}

    assert carry_low * carry_low = carry_low
    assert carry_high * carry_high = carry_high

    assert res.low = a.low + b.low - carry_low * SHIFT
    assert res.high = a.high + b.high + carry_low - carry_high * SHIFT
    uint256_check(res)

    return (res, carry_high)
end

# Splits a field element in the range [0, 2^192) to its low 64-bit and high 128-bit parts.
func split_64{range_check_ptr}(a : felt) -> (low : felt, high : felt):
    alloc_locals
    local low : felt
    local high : felt

    %{
        ids.low = ids.a & ((1<<64) - 1)
        ids.high = ids.a >> 64
    %}
    assert_nn_le(low, HALF_SHIFT)
    [range_check_ptr] = high
    let range_check_ptr = range_check_ptr + 1
    return (low, high)
end

# Multiplies two integers. Returns the result as two 256-bit integers (low and high parts).
func uint256_mul{range_check_ptr}(a : Uint256, b : Uint256) -> (low : Uint256, high : Uint256):
    alloc_locals
    let (a0, a1) = split_64(a.low)
    let (a2, a3) = split_64(a.high)
    let (b0, b1) = split_64(b.low)
    let (b2, b3) = split_64(b.high)

    let (res0, carry) = split_64(a0 * b0)
    let (res1, carry) = split_64(a1 * b0 + a0 * b1 + carry)
    let (res2, carry) = split_64(a2 * b0 + a1 * b1 + a0 * b2 + carry)
    let (res3, carry) = split_64(a3 * b0 + a2 * b1 + a1 * b2 + a0 * b3 + carry)
    let (res4, carry) = split_64(a3 * b1 + a2 * b2 + a1 * b3 + carry)
    let (res5, carry) = split_64(a3 * b2 + a2 * b3 + carry)
    let (res6, carry) = split_64(a3 * b3 + carry)

    return (
        low=Uint256(low=res0 + HALF_SHIFT * res1, high=res2 + HALF_SHIFT * res3),
        high=Uint256(low=res4 + HALF_SHIFT * res5, high=res6 + HALF_SHIFT * carry))
end
