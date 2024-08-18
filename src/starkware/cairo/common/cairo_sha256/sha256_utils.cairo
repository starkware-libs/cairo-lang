from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.math import assert_nn_le, unsigned_div_rem
from starkware.cairo.common.registers import get_fp_and_pc, get_label_location

const BATCH_SIZE = 7;
const ALL_ONES = 2 ** 251 - 1;
// Pack the different instances with offsets of 35 bits. This is the maximal possible offset for
// 7 32-bit words and it allows space for carry bits in integer addition operations (up to
// 8 summands).
const SHIFTS = 1 + 2 ** 35 + 2 ** (35 * 2) + 2 ** (35 * 3) + 2 ** (35 * 4) + 2 ** (35 * 5) + 2 ** (
    35 * 6
);

// Given an array of size 16, extends it to the message schedule array (of size 64) by writing
// 48 more values.
// Each element represents 7 32-bit words from 7 difference instances, starting at bits
// 0, 35, 35 * 2, ..., 35 * 6.
func compute_message_schedule{bitwise_ptr: BitwiseBuiltin*}(message: felt*) {
    alloc_locals;

    // Defining the following constants as local variables saves some instructions.
    local shift_mask3 = SHIFTS * (2 ** 32 - 2 ** 3);
    local shift_mask7 = SHIFTS * (2 ** 32 - 2 ** 7);
    local shift_mask10 = SHIFTS * (2 ** 32 - 2 ** 10);
    local shift_mask17 = SHIFTS * (2 ** 32 - 2 ** 17);
    local shift_mask18 = SHIFTS * (2 ** 32 - 2 ** 18);
    local shift_mask19 = SHIFTS * (2 ** 32 - 2 ** 19);
    local mask32ones = SHIFTS * (2 ** 32 - 1);

    // Loop variables.
    tempvar bitwise_ptr = bitwise_ptr;
    tempvar message = message + 16;
    tempvar n = 64 - 16;

    loop:
    // Implementing a right rotation by k:
    // Let `x = upper + lower`,
    // where `upper` represents the upper 32-k bits of x and `lower` represents the lower k bits.
    // `upper` can be expressed as `x & (2 ** 32 - 2 ** k)` and `lower` as `x & (2 ** k - 1)`.
    // Consequently, right_rot(x, k) equals `lower * 2 ** (32 - k) + upper / 2 ** k`,
    // which simplifies to:
    // `(2 ** (32 - k)) * (lower + upper) + (1 / 2 ** k - 2 ** (32 - k)) * upper`.
    tempvar w0 = message[-15];
    assert bitwise_ptr[0].x = w0;
    assert bitwise_ptr[0].y = shift_mask7;
    let w0_rot7 = (2 ** (32 - 7)) * w0 + (1 / 2 ** 7 - 2 ** (32 - 7)) * bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].x = w0;
    assert bitwise_ptr[1].y = shift_mask18;
    let w0_rot18 = (2 ** (32 - 18)) * w0 + (1 / 2 ** 18 - 2 ** (32 - 18)) * bitwise_ptr[1].x_and_y;
    assert bitwise_ptr[2].x = w0;
    assert bitwise_ptr[2].y = shift_mask3;
    let w0_shift3 = (1 / 2 ** 3) * bitwise_ptr[2].x_and_y;
    assert bitwise_ptr[3].x = w0_rot7;
    assert bitwise_ptr[3].y = w0_rot18;
    assert bitwise_ptr[4].x = bitwise_ptr[3].x_xor_y;
    assert bitwise_ptr[4].y = w0_shift3;
    let s0 = bitwise_ptr[4].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 5 * BitwiseBuiltin.SIZE;

    // Compute s1 = right_rot(w[i - 2], 17) ^ right_rot(w[i - 2], 19) ^ (w[i - 2] >> 10).
    tempvar w1 = message[-2];
    assert bitwise_ptr[0].x = w1;
    assert bitwise_ptr[0].y = shift_mask17;
    let w1_rot17 = (2 ** (32 - 17)) * w1 + (1 / 2 ** 17 - 2 ** (32 - 17)) * bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].x = w1;
    assert bitwise_ptr[1].y = shift_mask19;
    let w1_rot19 = (2 ** (32 - 19)) * w1 + (1 / 2 ** 19 - 2 ** (32 - 19)) * bitwise_ptr[1].x_and_y;
    assert bitwise_ptr[2].x = w1;
    assert bitwise_ptr[2].y = shift_mask10;
    let w1_shift10 = (1 / 2 ** 10) * bitwise_ptr[2].x_and_y;
    assert bitwise_ptr[3].x = w1_rot17;
    assert bitwise_ptr[3].y = w1_rot19;
    assert bitwise_ptr[4].x = bitwise_ptr[3].x_xor_y;
    assert bitwise_ptr[4].y = w1_shift10;
    let s1 = bitwise_ptr[4].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 5 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = message[-16] + s0 + message[-7] + s1;
    assert bitwise_ptr[0].y = mask32ones;
    assert message[0] = bitwise_ptr[0].x_and_y;
    let bitwise_ptr = bitwise_ptr + BitwiseBuiltin.SIZE;

    tempvar bitwise_ptr = bitwise_ptr;
    tempvar message = message + 1;
    tempvar n = n - 1;
    jmp loop if n != 0;

    return ();
}

func sha2_compress{bitwise_ptr: BitwiseBuiltin*}(
    state: felt*, message: felt*, round_constants: felt*
) -> (new_state: felt*) {
    alloc_locals;

    // Defining the following constants as local variables saves some instructions.
    local shift_mask2 = SHIFTS * (2 ** 32 - 2 ** 2);
    local shift_mask13 = SHIFTS * (2 ** 32 - 2 ** 13);
    local shift_mask22 = SHIFTS * (2 ** 32 - 2 ** 22);
    local shift_mask6 = SHIFTS * (2 ** 32 - 2 ** 6);
    local shift_mask11 = SHIFTS * (2 ** 32 - 2 ** 11);
    local shift_mask25 = SHIFTS * (2 ** 32 - 2 ** 25);
    local mask32ones = SHIFTS * (2 ** 32 - 1);

    tempvar a = state[0];
    tempvar b = state[1];
    tempvar c = state[2];
    tempvar d = state[3];
    tempvar e = state[4];
    tempvar f = state[5];
    tempvar g = state[6];
    tempvar h = state[7];
    tempvar round_constants = round_constants;
    tempvar message = message;
    tempvar bitwise_ptr = bitwise_ptr;
    tempvar n = 64;

    loop:
    // Compute s0 = right_rot(a, 2) ^ right_rot(a, 13) ^ right_rot(a, 22).
    assert bitwise_ptr[0].x = a;
    assert bitwise_ptr[0].y = shift_mask2;
    let a_rot2 = (2 ** (32 - 2)) * a + (1 / 2 ** 2 - 2 ** (32 - 2)) * bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].x = a;
    assert bitwise_ptr[1].y = shift_mask13;
    let a_rot13 = (2 ** (32 - 13)) * a + (1 / 2 ** 13 - 2 ** (32 - 13)) * bitwise_ptr[1].x_and_y;
    assert bitwise_ptr[2].x = a;
    assert bitwise_ptr[2].y = shift_mask22;
    let a_rot22 = (2 ** (32 - 22)) * a + (1 / 2 ** 22 - 2 ** (32 - 22)) * bitwise_ptr[2].x_and_y;
    assert bitwise_ptr[3].x = a_rot2;
    assert bitwise_ptr[3].y = a_rot13;
    assert bitwise_ptr[4].x = bitwise_ptr[3].x_xor_y;
    assert bitwise_ptr[4].y = a_rot22;
    let s0 = bitwise_ptr[4].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 5 * BitwiseBuiltin.SIZE;

    // Compute s1 = right_rot(e, 6) ^ right_rot(e, 11) ^ right_rot(e, 25).
    assert bitwise_ptr[0].x = e;
    assert bitwise_ptr[0].y = shift_mask6;
    let e_rot6 = (2 ** (32 - 6)) * e + (1 / 2 ** 6 - 2 ** (32 - 6)) * bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].x = e;
    assert bitwise_ptr[1].y = shift_mask11;
    let e_rot11 = (2 ** (32 - 11)) * e + (1 / 2 ** 11 - 2 ** (32 - 11)) * bitwise_ptr[1].x_and_y;
    assert bitwise_ptr[2].x = e;
    assert bitwise_ptr[2].y = shift_mask25;
    let e_rot25 = (2 ** (32 - 25)) * e + (1 / 2 ** 25 - 2 ** (32 - 25)) * bitwise_ptr[2].x_and_y;
    assert bitwise_ptr[3].x = e_rot6;
    assert bitwise_ptr[3].y = e_rot11;
    assert bitwise_ptr[4].x = bitwise_ptr[3].x_xor_y;
    assert bitwise_ptr[4].y = e_rot25;
    let s1 = bitwise_ptr[4].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 5 * BitwiseBuiltin.SIZE;

    // Compute ch = (e & f) ^ ((~e) & g).
    assert bitwise_ptr[0].x = e;
    assert bitwise_ptr[0].y = f;
    assert bitwise_ptr[1].x = ALL_ONES - e;
    assert bitwise_ptr[1].y = g;
    let ch = bitwise_ptr[0].x_and_y + bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    // Compute maj = (a & b) ^ (a & c) ^ (b & c).
    // We use the following trick to compute the majority function:
    // look at the i-th bit
    // if 0 of the bits a[i],b[i],c[i] are 1, then a[i] + b[i] + c[i] - (a[i] ^ b[i] ^ c[i]) = 00
    // if 1 of the bits a[i],b[i],c[i] are 1, then a[i] + b[i] + c[i] - (a[i] ^ b[i] ^ c[i]) = 00
    // if 2 of the bits a[i],b[i],c[i] are 1, then a[i] + b[i] + c[i] - (a[i] ^ b[i] ^ c[i]) = 10
    // if 3 of the bits a[i],b[i],c[i] are 1, then a[i] + b[i] + c[i] - (a[i] ^ b[i] ^ c[i]) = 10
    // so a + b + c - (a ^ b ^ c)  is the majority shifted by 1.
    assert bitwise_ptr[0].x = a;
    assert bitwise_ptr[0].y = b;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].y = c;
    let maj = (a + b + c - bitwise_ptr[1].x_xor_y) / 2;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    tempvar temp1 = h + s1 + ch + round_constants[0] + message[0];
    tempvar temp2 = s0 + maj;

    assert bitwise_ptr[0].x = temp1 + temp2;
    assert bitwise_ptr[0].y = mask32ones;
    let new_a = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].x = d + temp1;
    assert bitwise_ptr[1].y = mask32ones;
    let new_e = bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    tempvar new_a = new_a;
    tempvar new_b = a;
    tempvar new_c = b;
    tempvar new_d = c;
    tempvar new_e = new_e;
    tempvar new_f = e;
    tempvar new_g = f;
    tempvar new_h = g;
    tempvar round_constants = round_constants + 1;
    tempvar message = message + 1;
    tempvar bitwise_ptr = bitwise_ptr;
    tempvar n = n - 1;
    jmp loop if n != 0;

    // Add the compression result to the original state:
    let (res) = alloc();
    assert bitwise_ptr[0].x = state[0] + new_a;
    assert bitwise_ptr[0].y = mask32ones;
    assert res[0] = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].x = state[1] + new_b;
    assert bitwise_ptr[1].y = mask32ones;
    assert res[1] = bitwise_ptr[1].x_and_y;
    assert bitwise_ptr[2].x = state[2] + new_c;
    assert bitwise_ptr[2].y = mask32ones;
    assert res[2] = bitwise_ptr[2].x_and_y;
    assert bitwise_ptr[3].x = state[3] + new_d;
    assert bitwise_ptr[3].y = mask32ones;
    assert res[3] = bitwise_ptr[3].x_and_y;
    assert bitwise_ptr[4].x = state[4] + new_e;
    assert bitwise_ptr[4].y = mask32ones;
    assert res[4] = bitwise_ptr[4].x_and_y;
    assert bitwise_ptr[5].x = state[5] + new_f;
    assert bitwise_ptr[5].y = mask32ones;
    assert res[5] = bitwise_ptr[5].x_and_y;
    assert bitwise_ptr[6].x = state[6] + new_g;
    assert bitwise_ptr[6].y = mask32ones;
    assert res[6] = bitwise_ptr[6].x_and_y;
    assert bitwise_ptr[7].x = state[7] + new_h;
    assert bitwise_ptr[7].y = mask32ones;
    assert res[7] = bitwise_ptr[7].x_and_y;
    let bitwise_ptr = bitwise_ptr + 8 * BitwiseBuiltin.SIZE;

    return (res,);
}

// Returns the 64 round constants of SHA256.
func get_round_constants() -> felt* {
    alloc_locals;
    let (round_constants) = get_label_location(data);
    return round_constants;

    data:
    dw 0x428A2F98 * SHIFTS;
    dw 0x71374491 * SHIFTS;
    dw 0xB5C0FBCF * SHIFTS;
    dw 0xE9B5DBA5 * SHIFTS;
    dw 0x3956C25B * SHIFTS;
    dw 0x59F111F1 * SHIFTS;
    dw 0x923F82A4 * SHIFTS;
    dw 0xAB1C5ED5 * SHIFTS;
    dw 0xD807AA98 * SHIFTS;
    dw 0x12835B01 * SHIFTS;
    dw 0x243185BE * SHIFTS;
    dw 0x550C7DC3 * SHIFTS;
    dw 0x72BE5D74 * SHIFTS;
    dw 0x80DEB1FE * SHIFTS;
    dw 0x9BDC06A7 * SHIFTS;
    dw 0xC19BF174 * SHIFTS;
    dw 0xE49B69C1 * SHIFTS;
    dw 0xEFBE4786 * SHIFTS;
    dw 0x0FC19DC6 * SHIFTS;
    dw 0x240CA1CC * SHIFTS;
    dw 0x2DE92C6F * SHIFTS;
    dw 0x4A7484AA * SHIFTS;
    dw 0x5CB0A9DC * SHIFTS;
    dw 0x76F988DA * SHIFTS;
    dw 0x983E5152 * SHIFTS;
    dw 0xA831C66D * SHIFTS;
    dw 0xB00327C8 * SHIFTS;
    dw 0xBF597FC7 * SHIFTS;
    dw 0xC6E00BF3 * SHIFTS;
    dw 0xD5A79147 * SHIFTS;
    dw 0x06CA6351 * SHIFTS;
    dw 0x14292967 * SHIFTS;
    dw 0x27B70A85 * SHIFTS;
    dw 0x2E1B2138 * SHIFTS;
    dw 0x4D2C6DFC * SHIFTS;
    dw 0x53380D13 * SHIFTS;
    dw 0x650A7354 * SHIFTS;
    dw 0x766A0ABB * SHIFTS;
    dw 0x81C2C92E * SHIFTS;
    dw 0x92722C85 * SHIFTS;
    dw 0xA2BFE8A1 * SHIFTS;
    dw 0xA81A664B * SHIFTS;
    dw 0xC24B8B70 * SHIFTS;
    dw 0xC76C51A3 * SHIFTS;
    dw 0xD192E819 * SHIFTS;
    dw 0xD6990624 * SHIFTS;
    dw 0xF40E3585 * SHIFTS;
    dw 0x106AA070 * SHIFTS;
    dw 0x19A4C116 * SHIFTS;
    dw 0x1E376C08 * SHIFTS;
    dw 0x2748774C * SHIFTS;
    dw 0x34B0BCB5 * SHIFTS;
    dw 0x391C0CB3 * SHIFTS;
    dw 0x4ED8AA4A * SHIFTS;
    dw 0x5B9CCA4F * SHIFTS;
    dw 0x682E6FF3 * SHIFTS;
    dw 0x748F82EE * SHIFTS;
    dw 0x78A5636F * SHIFTS;
    dw 0x84C87814 * SHIFTS;
    dw 0x8CC70208 * SHIFTS;
    dw 0x90BEFFFA * SHIFTS;
    dw 0xA4506CEB * SHIFTS;
    dw 0xBEF9A3F7 * SHIFTS;
    dw 0xC67178F2 * SHIFTS;
}

const SHA256_INPUT_CHUNK_SIZE_FELTS = 16;
const SHA256_INPUT_CHUNK_SIZE_BYTES = 64;
const SHA256_STATE_SIZE_FELTS = 8;
// Each instance consists of a message (16 words), an input state (8 words),
// and an output state (8 words).
const SHA256_INSTANCE_SIZE = SHA256_INPUT_CHUNK_SIZE_FELTS + 2 * SHA256_STATE_SIZE_FELTS;

func _finalize_sha256_inner{range_check_ptr, bitwise_ptr: BitwiseBuiltin*}(
    sha256_ptr: felt*, n: felt, round_constants: felt*
) {
    if (n == 0) {
        return ();
    }

    alloc_locals;

    local U32_MAX = 2 ** 32 - 1;

    let sha256_start = sha256_ptr;

    let (local message_start: felt*) = alloc();

    // Handle message.

    tempvar message = message_start;
    tempvar sha256_ptr = sha256_ptr;
    tempvar range_check_ptr = range_check_ptr;
    tempvar m = SHA256_INPUT_CHUNK_SIZE_FELTS;

    message_loop:
    tempvar x0 = sha256_ptr[0 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 0] = x0;
    assert [range_check_ptr + 1] = U32_MAX - x0;
    tempvar x1 = sha256_ptr[1 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 2] = x1;
    assert [range_check_ptr + 3] = U32_MAX - x1;
    tempvar x2 = sha256_ptr[2 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 4] = x2;
    assert [range_check_ptr + 5] = U32_MAX - x2;
    tempvar x3 = sha256_ptr[3 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 6] = x3;
    assert [range_check_ptr + 7] = U32_MAX - x3;
    tempvar x4 = sha256_ptr[4 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 8] = x4;
    assert [range_check_ptr + 9] = U32_MAX - x4;
    tempvar x5 = sha256_ptr[5 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 10] = x5;
    assert [range_check_ptr + 11] = U32_MAX - x5;
    tempvar x6 = sha256_ptr[6 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 12] = x6;
    assert [range_check_ptr + 13] = U32_MAX - x6;
    assert message[0] = x0 + 2 ** 35 * x1 + 2 ** (35 * 2) * x2 + 2 ** (35 * 3) * x3 + 2 ** (
        35 * 4
    ) * x4 + 2 ** (35 * 5) * x5 + 2 ** (35 * 6) * x6;

    tempvar message = message + 1;
    tempvar sha256_ptr = sha256_ptr + 1;
    tempvar range_check_ptr = range_check_ptr + 14;
    tempvar m = m - 1;
    jmp message_loop if m != 0;

    // Handle input state.

    let (local input_state_start: felt*) = alloc();
    tempvar input_state = input_state_start;
    tempvar sha256_ptr = sha256_ptr;
    tempvar range_check_ptr = range_check_ptr;
    tempvar m = SHA256_STATE_SIZE_FELTS;

    input_state_loop:
    tempvar x0 = sha256_ptr[0 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 0] = x0;
    assert [range_check_ptr + 1] = U32_MAX - x0;
    tempvar x1 = sha256_ptr[1 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 2] = x1;
    assert [range_check_ptr + 3] = U32_MAX - x1;
    tempvar x2 = sha256_ptr[2 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 4] = x2;
    assert [range_check_ptr + 5] = U32_MAX - x2;
    tempvar x3 = sha256_ptr[3 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 6] = x3;
    assert [range_check_ptr + 7] = U32_MAX - x3;
    tempvar x4 = sha256_ptr[4 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 8] = x4;
    assert [range_check_ptr + 9] = U32_MAX - x4;
    tempvar x5 = sha256_ptr[5 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 10] = x5;
    assert [range_check_ptr + 11] = U32_MAX - x5;
    tempvar x6 = sha256_ptr[6 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 12] = x6;
    assert [range_check_ptr + 13] = U32_MAX - x6;
    assert input_state[0] = x0 + 2 ** 35 * x1 + 2 ** (35 * 2) * x2 + 2 ** (35 * 3) * x3 + 2 ** (
        35 * 4
    ) * x4 + 2 ** (35 * 5) * x5 + 2 ** (35 * 6) * x6;

    tempvar input_state = input_state + 1;
    tempvar sha256_ptr = sha256_ptr + 1;
    tempvar range_check_ptr = range_check_ptr + 14;
    tempvar m = m - 1;
    jmp input_state_loop if m != 0;

    // Run sha256 on the 7 instances.

    local sha256_ptr: felt* = sha256_ptr;
    local range_check_ptr = range_check_ptr;
    compute_message_schedule(message_start);
    let (outputs) = sha2_compress(input_state_start, message_start, round_constants);
    local bitwise_ptr: BitwiseBuiltin* = bitwise_ptr;

    // Handle outputs.

    tempvar outputs = outputs;
    tempvar sha256_ptr = sha256_ptr;
    tempvar range_check_ptr = range_check_ptr;
    tempvar m = SHA256_STATE_SIZE_FELTS;

    output_loop:
    tempvar x0 = sha256_ptr[0 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr] = x0;
    assert [range_check_ptr + 1] = U32_MAX - x0;
    tempvar x1 = sha256_ptr[1 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 2] = x1;
    assert [range_check_ptr + 3] = U32_MAX - x1;
    tempvar x2 = sha256_ptr[2 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 4] = x2;
    assert [range_check_ptr + 5] = U32_MAX - x2;
    tempvar x3 = sha256_ptr[3 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 6] = x3;
    assert [range_check_ptr + 7] = U32_MAX - x3;
    tempvar x4 = sha256_ptr[4 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 8] = x4;
    assert [range_check_ptr + 9] = U32_MAX - x4;
    tempvar x5 = sha256_ptr[5 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 10] = x5;
    assert [range_check_ptr + 11] = U32_MAX - x5;
    tempvar x6 = sha256_ptr[6 * SHA256_INSTANCE_SIZE];
    assert [range_check_ptr + 12] = x6;
    assert [range_check_ptr + 13] = U32_MAX - x6;

    assert outputs[0] = x0 + 2 ** 35 * x1 + 2 ** (35 * 2) * x2 + 2 ** (35 * 3) * x3 + 2 ** (
        35 * 4
    ) * x4 + 2 ** (35 * 5) * x5 + 2 ** (35 * 6) * x6;

    tempvar outputs = outputs + 1;
    tempvar sha256_ptr = sha256_ptr + 1;
    tempvar range_check_ptr = range_check_ptr + 14;
    tempvar m = m - 1;
    jmp output_loop if m != 0;

    return _finalize_sha256_inner(
        sha256_ptr=sha256_start + SHA256_INSTANCE_SIZE * BATCH_SIZE,
        n=n - 1,
        round_constants=round_constants,
    );
}

// Verifies that [sha256_ptr_start:sha256_ptr_end] is an array of blocks of size 32
// where each block consist of 16 words of message, 8 words for the input state and 8 words
// for the output state.
func finalize_sha256{range_check_ptr, bitwise_ptr: BitwiseBuiltin*}(
    sha256_ptr_start: felt*, sha256_ptr_end: felt*
) {
    alloc_locals;

    tempvar n = (sha256_ptr_end - sha256_ptr_start) / SHA256_INSTANCE_SIZE;
    if (n == 0) {
        return ();
    }

    %{
        # Add dummy pairs of input and output.
        from starkware.cairo.common.cairo_sha256.sha256_utils import (
            IV,
            compute_message_schedule,
            sha2_compress_function,
        )

        number_of_missing_blocks = (-ids.n) % ids.BATCH_SIZE
        assert 0 <= number_of_missing_blocks < 20
        _sha256_input_chunk_size_felts = ids.SHA256_INPUT_CHUNK_SIZE_FELTS
        assert 0 <= _sha256_input_chunk_size_felts < 100

        message = [0] * _sha256_input_chunk_size_felts
        w = compute_message_schedule(message)
        output = sha2_compress_function(IV, w)
        padding = (message + IV + output) * number_of_missing_blocks
        segments.write_arg(ids.sha256_ptr_end, padding)
    %}

    // Compute the amount of blocks (rounded up).
    let (local q, r) = unsigned_div_rem(n + BATCH_SIZE - 1, BATCH_SIZE);
    let round_constants = get_round_constants();
    _finalize_sha256_inner(sha256_ptr_start, n=q, round_constants=round_constants);
    return ();
}
