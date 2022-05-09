from starkware.cairo.common.bitwise import bitwise_and, bitwise_or, bitwise_xor
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.math import assert_in_range, assert_le, assert_nn_le, assert_not_zero
from starkware.cairo.common.math_cmp import is_le
from starkware.cairo.common.pow import pow
from starkware.cairo.common.registers import get_ap, get_fp_and_pc

# Represents an integer in the range [0, 2^256).
struct Uint256:
    # The low 128 bits of the value.
    member low : felt
    # The high 128 bits of the value.
    member high : felt
end

const SHIFT = 2 ** 128
const ALL_ONES = 2 ** 128 - 1
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
    assert a = low + high * HALF_SHIFT
    assert [range_check_ptr + 0] = low
    assert [range_check_ptr + 1] = HALF_SHIFT - 1 - low
    assert [range_check_ptr + 2] = high
    let range_check_ptr = range_check_ptr + 3
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
        high=Uint256(low=res4 + HALF_SHIFT * res5, high=res6 + HALF_SHIFT * carry),
    )
end

# Returns the floor value of the square root of a uint256 integer.
func uint256_sqrt{range_check_ptr}(n : Uint256) -> (res : Uint256):
    alloc_locals
    local root : Uint256

    %{
        from starkware.python.math_utils import isqrt
        n = (ids.n.high << 128) + ids.n.low
        root = isqrt(n)
        assert 0 <= root < 2 ** 128
        ids.root.low = root
        ids.root.high = 0
    %}

    # Verify that 0 <= root < 2**128.
    assert root.high = 0
    [range_check_ptr] = root.low
    let range_check_ptr = range_check_ptr + 1

    # Verify that n >= root**2.
    let (root_squared, carry) = uint256_mul(root, root)
    assert carry = Uint256(0, 0)
    let (check_lower_bound) = uint256_le(root_squared, n)
    assert check_lower_bound = 1

    # Verify that n <= (root+1)**2 - 1.
    # In the case where root = 2**128 - 1, we will have next_root_squared=0, since
    # (root+1)**2 = 2**256. Therefore next_root_squared - 1 = 2**256 - 1, as desired.
    let (next_root, add_carry) = uint256_add(root, Uint256(1, 0))
    assert add_carry = 0
    let (next_root_squared, _) = uint256_mul(next_root, next_root)
    let (next_root_squared_minus_one) = uint256_sub(next_root_squared, Uint256(1, 0))
    let (check_upper_bound) = uint256_le(n, next_root_squared_minus_one)
    assert check_upper_bound = 1

    return (res=root)
end

# Returns 1 if the first unsigned integer is less than the second unsigned integer.
func uint256_lt{range_check_ptr}(a : Uint256, b : Uint256) -> (res):
    if a.high == b.high:
        return is_le(a.low + 1, b.low)
    end
    return is_le(a.high + 1, b.high)
end

# Returns 1 if the first signed integer is less than the second signed integer.
func uint256_signed_lt{range_check_ptr}(a : Uint256, b : Uint256) -> (res):
    let (a, _) = uint256_add(a, cast((low=0, high=2 ** 127), Uint256))
    let (b, _) = uint256_add(b, cast((low=0, high=2 ** 127), Uint256))
    return uint256_lt(a, b)
end

# Returns 1 if the first unsigned integer is less than or equal to the second unsigned integer.
func uint256_le{range_check_ptr}(a : Uint256, b : Uint256) -> (res):
    let (not_le) = uint256_lt(a=b, b=a)
    return (1 - not_le)
end

# Returns 1 if the first signed integer is less than or equal to the second signed integer.
func uint256_signed_le{range_check_ptr}(a : Uint256, b : Uint256) -> (res):
    let (not_le) = uint256_signed_lt(a=b, b=a)
    return (1 - not_le)
end

# Returns 1 if the signed integer is nonnegative.
@known_ap_change
func uint256_signed_nn{range_check_ptr}(a : Uint256) -> (res):
    %{ memory[ap] = 1 if 0 <= (ids.a.high % PRIME) < 2 ** 127 else 0 %}
    jmp non_negative if [ap] != 0; ap++

    assert [range_check_ptr] = a.high - 2 ** 127
    let range_check_ptr = range_check_ptr + 1
    return (res=0)

    non_negative:
    assert [range_check_ptr] = a.high + 2 ** 127
    let range_check_ptr = range_check_ptr + 1
    return (res=1)
end

# Returns 1 if the first signed integer is less than or equal to the second signed integer
# and is greater than or equal to zero.
func uint256_signed_nn_le{range_check_ptr}(a : Uint256, b : Uint256) -> (res):
    let (is_le) = uint256_signed_le(a=a, b=b)
    if is_le == 0:
        return (res=0)
    end
    let (is_nn) = uint256_signed_nn(a=a)
    return (res=is_nn)
end

# Unsigned integer division between two integers. Returns the quotient and the remainder.
# Conforms to EVM specifications: division by 0 yields 0.
func uint256_unsigned_div_rem{range_check_ptr}(a : Uint256, div : Uint256) -> (
    quotient : Uint256, remainder : Uint256
):
    alloc_locals
    local quotient : Uint256
    local remainder : Uint256

    # If div == 0, return (0, 0).
    if div.low + div.high == 0:
        return (quotient=Uint256(0, 0), remainder=Uint256(0, 0))
    end

    %{
        a = (ids.a.high << 128) + ids.a.low
        div = (ids.div.high << 128) + ids.div.low
        quotient, remainder = divmod(a, div)

        ids.quotient.low = quotient & ((1 << 128) - 1)
        ids.quotient.high = quotient >> 128
        ids.remainder.low = remainder & ((1 << 128) - 1)
        ids.remainder.high = remainder >> 128
    %}
    let (res_mul, carry) = uint256_mul(quotient, div)
    assert carry = Uint256(0, 0)

    let (check_val, add_carry) = uint256_add(res_mul, remainder)
    assert check_val = a
    assert add_carry = 0

    let (is_valid) = uint256_lt(remainder, div)
    assert is_valid = 1
    return (quotient=quotient, remainder=remainder)
end

# Returns the bitwise NOT of an integer.
func uint256_not{range_check_ptr}(a : Uint256) -> (res : Uint256):
    return (Uint256(low=ALL_ONES - a.low, high=ALL_ONES - a.high))
end

# Returns the negation of an integer.
# Note that the negation of -2**255 is -2**255.
func uint256_neg{range_check_ptr}(a : Uint256) -> (res : Uint256):
    let (not_num) = uint256_not(a)
    let (res, _) = uint256_add(not_num, Uint256(low=1, high=0))
    return (res)
end

# Conditionally negates an integer.
func uint256_cond_neg{range_check_ptr}(a : Uint256, should_neg) -> (res : Uint256):
    if should_neg != 0:
        return uint256_neg(a)
    else:
        return (res=a)
    end
end

# Signed integer division between two integers. Returns the quotient and the remainder.
# Conforms to EVM specifications.
# See ethereum yellow paper (https://ethereum.github.io/yellowpaper/paper.pdf, page 29).
# Note that the remainder may be negative if one of the inputs is negative and that
# (-2**255) / (-1) = -2**255 because 2*255 is out of range.
func uint256_signed_div_rem{range_check_ptr}(a : Uint256, div : Uint256) -> (
    quot : Uint256, rem : Uint256
):
    alloc_locals

    # When div=-1, simply return -a.
    if div.low == SHIFT - 1:
        if div.high == SHIFT - 1:
            let (quot) = uint256_neg(a)
            return (quot, cast((0, 0), Uint256))
        end
    end

    # Take the absolute value of a.
    let (local a_sign) = is_le(2 ** 127, a.high)
    local range_check_ptr = range_check_ptr
    let (local a) = uint256_cond_neg(a, should_neg=a_sign)

    # Take the absolute value of div.
    let (local div_sign) = is_le(2 ** 127, div.high)
    local range_check_ptr = range_check_ptr
    let (div) = uint256_cond_neg(div, should_neg=div_sign)

    # Unsigned division.
    let (local quot, local rem) = uint256_unsigned_div_rem(a, div)
    local range_check_ptr = range_check_ptr

    # Fix the remainder according to the sign of a.
    let (rem) = uint256_cond_neg(rem, should_neg=a_sign)

    # Fix the quotient according to the signs of a and div.
    if a_sign == div_sign:
        return (quot=quot, rem=rem)
    end
    let (local quot_neg) = uint256_neg(quot)

    return (quot=quot_neg, rem=rem)
end

# Subtracts two integers. Returns the result as a 256-bit integer.
func uint256_sub{range_check_ptr}(a : Uint256, b : Uint256) -> (res : Uint256):
    let (b_neg) = uint256_neg(b)
    let (res, _) = uint256_add(a, b_neg)
    return (res)
end

# Bitwise.

# Return true if both integers are equal.
func uint256_eq{range_check_ptr}(a : Uint256, b : Uint256) -> (res):
    if a.high != b.high:
        return (0)
    end
    if a.low != b.low:
        return (0)
    end
    return (1)
end

# Computes the bitwise XOR of 2 uint256 integers.
func uint256_xor{range_check_ptr, bitwise_ptr : BitwiseBuiltin*}(a : Uint256, b : Uint256) -> (
    res : Uint256
):
    let (low) = bitwise_xor(a.low, b.low)
    let (high) = bitwise_xor(a.high, b.high)
    return (Uint256(low, high))
end

# Computes the bitwise AND of 2 uint256 integers.
func uint256_and{range_check_ptr, bitwise_ptr : BitwiseBuiltin*}(a : Uint256, b : Uint256) -> (
    res : Uint256
):
    let (low) = bitwise_and(a.low, b.low)
    let (high) = bitwise_and(a.high, b.high)
    return (Uint256(low, high))
end

# Computes the bitwise OR of 2 uint256 integers.
func uint256_or{range_check_ptr, bitwise_ptr : BitwiseBuiltin*}(a : Uint256, b : Uint256) -> (
    res : Uint256
):
    let (low) = bitwise_or(a.low, b.low)
    let (high) = bitwise_or(a.high, b.high)
    return (Uint256(low, high))
end

# Computes 2**exp % 2**256 as a uint256 integer.
func uint256_pow2{range_check_ptr}(exp : Uint256) -> (res : Uint256):
    # If exp >= 256, the result will be zero modulo 2**256.
    let (res) = uint256_lt(exp, Uint256(256, 0))
    if res == 0:
        return (Uint256(0, 0))
    end

    let (res) = is_le(exp.low, 127)
    if res != 0:
        let (x) = pow(2, exp.low)
        return (Uint256(x, 0))
    else:
        let (x) = pow(2, exp.low - 128)
        return (Uint256(0, x))
    end
end

# Computes the logical left shift of a uint256 integer.
func uint256_shl{range_check_ptr}(a : Uint256, b : Uint256) -> (res : Uint256):
    let (c) = uint256_pow2(b)
    let (res, _) = uint256_mul(a, c)
    return (res)
end

# Computes the logical right shift of a uint256 integer.
func uint256_shr{range_check_ptr}(a : Uint256, b : Uint256) -> (res : Uint256):
    let (c) = uint256_pow2(b)
    let (res, _) = uint256_unsigned_div_rem(a, c)
    return (res)
end

# Reverses byte endianness of a 128-bit word.
#
# The algorithm works in steps. Generally speaking, on the i-th step,
# we switch between every two consecutive sequences of 2 ** i bytes.
# To illustrate how it works, here are the steps when running
# on a 64-bit word = [b0, b1, b2, b3, b4, b5, b6, b7] (3 steps instead of 4):
#
# step 1:
# [b0, b1, b2, b3, b4, b5, b6, b7] -
# [b0, 0,  b2, 0,  b4, 0,  b6, 0 ] +
# [0,  0,  b0, 0,  b2, 0,  b4, 0,  b6] =
# [0,  b1, b0, b3, b2, b5, b4, b7, b6]
#
# step 2:
# [0, b1, b0, b3, b2, b5, b4, b7, b6] -
# [0, b1, b0, 0,  0,  b5, b4, 0,  0 ] +
# [0, 0,  0,  0,  0,  b1, b0, 0,  0,  b5, b4] =
# [0, 0,  0,  b3, b2, b1, b0, b7, b6, b5, b4]
#
# step 3:
# [0, 0, 0, b3, b2, b1, b0, b7, b6, b5, b4] -
# [0, 0, 0, b3, b2, b1, b0, 0,  0,  0,  0 ] +
# [0, 0, 0, 0,  0,  0,  0,  0,  0,  0,  0,  b3, b2, b1, b0] =
# [0, 0, 0, 0,  0,  0,  0,  b7, b6, b5, b4, b3, b2, b1, b0]
#
# Next, we divide by 2 ** (8 + 16 + 32) and get [b7, b6, b5, b4, b3, b2, b1, b0].
func word_reverse_endian{bitwise_ptr : BitwiseBuiltin*}(word : felt) -> (res : felt):
    # Step 1.
    assert bitwise_ptr[0].x = word
    assert bitwise_ptr[0].y = 0x00ff00ff00ff00ff00ff00ff00ff00ff
    tempvar word = word + (2 ** 16 - 1) * bitwise_ptr[0].x_and_y
    # Step 2.
    assert bitwise_ptr[1].x = word
    assert bitwise_ptr[1].y = 0x00ffff0000ffff0000ffff0000ffff00
    tempvar word = word + (2 ** 32 - 1) * bitwise_ptr[1].x_and_y
    # Step 3.
    assert bitwise_ptr[2].x = word
    assert bitwise_ptr[2].y = 0x00ffffffff00000000ffffffff000000
    tempvar word = word + (2 ** 64 - 1) * bitwise_ptr[2].x_and_y
    # Step 4.
    assert bitwise_ptr[3].x = word
    assert bitwise_ptr[3].y = 0x00ffffffffffffffff00000000000000
    tempvar word = word + (2 ** 128 - 1) * bitwise_ptr[3].x_and_y

    let bitwise_ptr = bitwise_ptr + 4 * BitwiseBuiltin.SIZE
    return (res=word / 2 ** (8 + 16 + 32 + 64))
end

# Reverses byte endianness of a uint256 integer.
func uint256_reverse_endian{bitwise_ptr : BitwiseBuiltin*}(num : Uint256) -> (res : Uint256):
    let (high) = word_reverse_endian(num.high)
    let (low) = word_reverse_endian(num.low)

    return (res=Uint256(low=high, high=low))
end
