from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.registers import get_fp_and_pc

const N_PACKED_INSTANCES = 7
const ALL_ONES = 2 ** 251 - 1
const SHIFTS = 1 + 2 ** 35 + 2 ** (35 * 2) + 2 ** (35 * 3) + 2 ** (35 * 4) + 2 ** (35 * 5) +
    2 ** (35 * 6)

func mix{bitwise_ptr : BitwiseBuiltin*}(
    a : felt, b : felt, c : felt, d : felt, m0 : felt, m1 : felt
) -> (a : felt, b : felt, c : felt, d : felt):
    alloc_locals

    # Defining the following constant as local variables saves some instructions.
    local mask32ones = SHIFTS * (2 ** 32 - 1)

    # a = (a + b + m0) % 2**32
    assert bitwise_ptr[0].x = a + b + m0
    assert bitwise_ptr[0].y = mask32ones
    tempvar a = bitwise_ptr[0].x_and_y
    let bitwise_ptr = bitwise_ptr + BitwiseBuiltin.SIZE

    # d = right_rot((d ^ a), 16)
    assert bitwise_ptr[0].x = a
    assert bitwise_ptr[0].y = d
    tempvar a_xor_d = bitwise_ptr[0].x_xor_y
    assert bitwise_ptr[1].x = a_xor_d
    assert bitwise_ptr[1].y = SHIFTS * (2 ** 32 - 2 ** 16)
    tempvar d = (2 ** (32 - 16)) * a_xor_d + (1 / 2 ** 16 - 2 ** (32 - 16)) * bitwise_ptr[1].x_and_y
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE

    # c = (c + d) % 2**32
    assert bitwise_ptr[0].x = c + d
    assert bitwise_ptr[0].y = mask32ones
    tempvar c = bitwise_ptr[0].x_and_y
    let bitwise_ptr = bitwise_ptr + BitwiseBuiltin.SIZE

    # b = right_rot((b ^ c), 12)
    assert bitwise_ptr[0].x = b
    assert bitwise_ptr[0].y = c
    tempvar b_xor_c = bitwise_ptr[0].x_xor_y
    assert bitwise_ptr[1].x = b_xor_c
    assert bitwise_ptr[1].y = SHIFTS * (2 ** 32 - 2 ** 12)
    tempvar b = (2 ** (32 - 12)) * b_xor_c + (1 / 2 ** 12 - 2 ** (32 - 12)) * bitwise_ptr[1].x_and_y
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE

    # a = (a + b + m1) % 2**32
    assert bitwise_ptr[0].x = a + b + m1
    assert bitwise_ptr[0].y = mask32ones
    tempvar a = bitwise_ptr[0].x_and_y
    let bitwise_ptr = bitwise_ptr + BitwiseBuiltin.SIZE

    # d = right_rot((d ^ a), 8)
    assert bitwise_ptr[0].x = d
    assert bitwise_ptr[0].y = a
    tempvar d_xor_a = bitwise_ptr[0].x_xor_y
    assert bitwise_ptr[1].x = d_xor_a
    assert bitwise_ptr[1].y = SHIFTS * (2 ** 32 - 2 ** 8)
    tempvar d = (2 ** (32 - 8)) * d_xor_a + (1 / 2 ** 8 - 2 ** (32 - 8)) * bitwise_ptr[1].x_and_y
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE

    # c = (c + d) % 2**32
    assert bitwise_ptr[0].x = c + d
    assert bitwise_ptr[0].y = mask32ones
    tempvar c = bitwise_ptr[0].x_and_y
    let bitwise_ptr = bitwise_ptr + BitwiseBuiltin.SIZE

    # b = right_rot((b ^ c), 7)
    assert bitwise_ptr[0].x = b
    assert bitwise_ptr[0].y = c
    tempvar b_xor_c = bitwise_ptr[0].x_xor_y
    assert bitwise_ptr[1].x = b_xor_c
    assert bitwise_ptr[1].y = SHIFTS * (2 ** 32 - 2 ** 7)
    tempvar b = (2 ** (32 - 7)) * b_xor_c + (1 / 2 ** 7 - 2 ** (32 - 7)) * bitwise_ptr[1].x_and_y
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE

    return (a, b, c, d)
end

func blake_round{bitwise_ptr : BitwiseBuiltin*}(state : felt*, message : felt*, sigma : felt*) -> (
    new_state : felt*
):
    let state0 = state[0]
    let state1 = state[1]
    let state2 = state[2]
    let state3 = state[3]
    let state4 = state[4]
    let state5 = state[5]
    let state6 = state[6]
    let state7 = state[7]
    let state8 = state[8]
    let state9 = state[9]
    let state10 = state[10]
    let state11 = state[11]
    let state12 = state[12]
    let state13 = state[13]
    let state14 = state[14]
    let state15 = state[15]

    let (state0, state4, state8, state12) = mix(
        state0, state4, state8, state12, message[sigma[0]], message[sigma[1]]
    )
    let (state1, state5, state9, state13) = mix(
        state1, state5, state9, state13, message[sigma[2]], message[sigma[3]]
    )
    let (state2, state6, state10, state14) = mix(
        state2, state6, state10, state14, message[sigma[4]], message[sigma[5]]
    )
    let (state3, state7, state11, state15) = mix(
        state3, state7, state11, state15, message[sigma[6]], message[sigma[7]]
    )

    let (state0, state5, state10, state15) = mix(
        state0, state5, state10, state15, message[sigma[8]], message[sigma[9]]
    )
    let (state1, state6, state11, state12) = mix(
        state1, state6, state11, state12, message[sigma[10]], message[sigma[11]]
    )
    let (state2, state7, state8, state13) = mix(
        state2, state7, state8, state13, message[sigma[12]], message[sigma[13]]
    )
    let (state3, state4, state9, state14) = mix(
        state3, state4, state9, state14, message[sigma[14]], message[sigma[15]]
    )

    let (new_state : felt*) = alloc()
    assert new_state[0] = state0
    assert new_state[1] = state1
    assert new_state[2] = state2
    assert new_state[3] = state3
    assert new_state[4] = state4
    assert new_state[5] = state5
    assert new_state[6] = state6
    assert new_state[7] = state7
    assert new_state[8] = state8
    assert new_state[9] = state9
    assert new_state[10] = state10
    assert new_state[11] = state11
    assert new_state[12] = state12
    assert new_state[13] = state13
    assert new_state[14] = state14
    assert new_state[15] = state15

    return (new_state)
end

# Performs the blake compression function.
#
# h is a list of 8 32-bit words.
# message is a list of 16 32-bit words.
# t1 and f1 are assumed to be 0.
func blake2s_compress{bitwise_ptr : BitwiseBuiltin*}(
    h : felt*, message : felt*, t0 : felt, f0 : felt, sigma : felt*, output : felt*
):
    alloc_locals
    let (__fp__, _) = get_fp_and_pc()

    # Compute state[12].
    assert bitwise_ptr[0].x = 0x510e527f * SHIFTS
    assert bitwise_ptr[0].y = t0
    let state12 = bitwise_ptr[0].x_xor_y
    let bitwise_ptr = bitwise_ptr + BitwiseBuiltin.SIZE

    # Compute state[14].
    assert bitwise_ptr[0].x = 0x1f83d9ab * SHIFTS
    assert bitwise_ptr[0].y = f0
    let state14 = bitwise_ptr[0].x_xor_y
    let bitwise_ptr = bitwise_ptr + BitwiseBuiltin.SIZE

    local initial_state = h[0]
    local initial_state_ = h[1]
    local initial_state_ = h[2]
    local initial_state_ = h[3]
    local initial_state_ = h[4]
    local initial_state_ = h[5]
    local initial_state_ = h[6]
    local initial_state_ = h[7]
    local initial_state_ = 0x6a09e667 * SHIFTS
    local initial_state_ = 0xbb67ae85 * SHIFTS
    local initial_state_ = 0x3c6ef372 * SHIFTS
    local initial_state_ = 0xa54ff53a * SHIFTS
    local initial_state_ = state12
    local initial_state_ = 0x9b05688c * SHIFTS
    local initial_state_ = state14
    local initial_state_ = 0x5be0cd19 * SHIFTS

    let state = &initial_state

    let (state) = blake_round(state, message, sigma + 16 * 0)
    let (state) = blake_round(state, message, sigma + 16 * 1)
    let (state) = blake_round(state, message, sigma + 16 * 2)
    let (state) = blake_round(state, message, sigma + 16 * 3)
    let (state) = blake_round(state, message, sigma + 16 * 4)
    let (state) = blake_round(state, message, sigma + 16 * 5)
    let (state) = blake_round(state, message, sigma + 16 * 6)
    let (state) = blake_round(state, message, sigma + 16 * 7)
    let (state) = blake_round(state, message, sigma + 16 * 8)
    let (state) = blake_round(state, message, sigma + 16 * 9)

    tempvar old_h = h
    tempvar last_state = state
    tempvar new_h = output
    tempvar bitwise_ptr = bitwise_ptr
    tempvar n = 8

    loop:
    assert bitwise_ptr[0].x = old_h[0]
    assert bitwise_ptr[0].y = last_state[0]
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_xor_y
    assert bitwise_ptr[1].y = last_state[8]
    assert new_h[0] = bitwise_ptr[1].x_xor_y

    tempvar old_h = old_h + 1
    tempvar last_state = last_state + 1
    tempvar new_h = new_h + 1
    tempvar bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE
    tempvar n = n - 1
    jmp loop if n != 0

    return ()
end
