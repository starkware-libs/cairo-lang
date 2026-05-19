from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.math import assert_nn_le, unsigned_div_rem
from starkware.cairo.common.registers import get_fp_and_pc, get_label_location

const BATCH_SIZE = 3;
const ALL_ONES = 2 ** 251 - 1;
// Pack the 3 different instances (64-bit words) with offsets of 67 bits. This allows space for
// carry bits in integer addition operations (up to 8 summands).
const SHIFTS = 1 + 2 ** 67 + 2 ** (67 * 2);

// Given an array of size 16, extends it to the message schedule array (of size 80) by writing
// 64 more values.
// Each element represents 3 64-bit words from 3 different instances, starting at bits
// 0, 67, 67 * 2.
func compute_message_schedule{bitwise_ptr: BitwiseBuiltin*}(message: felt*) {
    alloc_locals;

    // Defining the following constants as local variables saves some instructions.
    local shift_mask1 = SHIFTS * (2 ** 64 - 2 ** 1);
    local shift_mask6 = SHIFTS * (2 ** 64 - 2 ** 6);
    local shift_mask7 = SHIFTS * (2 ** 64 - 2 ** 7);
    local shift_mask8 = SHIFTS * (2 ** 64 - 2 ** 8);
    local shift_mask19 = SHIFTS * (2 ** 64 - 2 ** 19);
    local shift_mask61 = SHIFTS * (2 ** 64 - 2 ** 61);
    local mask64ones = SHIFTS * (2 ** 64 - 1);

    // Loop variables.
    tempvar bitwise_ptr = bitwise_ptr;
    tempvar message = message + 16;
    tempvar n = 80 - 16;

    loop:
    // Implementing a right rotation by k:
    // Let `x = upper + lower`,
    // where `upper` represents the upper 64-k bits of x and `lower` represents the lower k bits.
    // `upper` can be expressed as `x & (2 ** 64 - 2 ** k)` and `lower` as `x & (2 ** k - 1)`.
    // Consequently, right_rot(x, k) equals `lower * 2 ** (64 - k) + upper / 2 ** k`,
    // which simplifies to:
    // `(2 ** (64 - k)) * (lower + upper) + (1 / 2 ** k - 2 ** (64 - k)) * upper`.
    tempvar w0 = message[-15];
    assert bitwise_ptr[0].x = w0;
    assert bitwise_ptr[0].y = shift_mask1;
    let w0_rot1 = (2 ** (64 - 1)) * w0 + (1 / 2 ** 1 - 2 ** (64 - 1)) * bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].x = w0;
    assert bitwise_ptr[1].y = shift_mask8;
    let w0_rot8 = (2 ** (64 - 8)) * w0 + (1 / 2 ** 8 - 2 ** (64 - 8)) * bitwise_ptr[1].x_and_y;
    assert bitwise_ptr[2].x = w0;
    assert bitwise_ptr[2].y = shift_mask7;
    let w0_shift7 = (1 / 2 ** 7) * bitwise_ptr[2].x_and_y;
    assert bitwise_ptr[3].x = w0_rot1;
    assert bitwise_ptr[3].y = w0_rot8;
    assert bitwise_ptr[4].x = bitwise_ptr[3].x_xor_y;
    assert bitwise_ptr[4].y = w0_shift7;
    let s0 = bitwise_ptr[4].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 5 * BitwiseBuiltin.SIZE;

    // Compute s1 = right_rot(w[i - 2], 19) ^ right_rot(w[i - 2], 61) ^ (w[i - 2] >> 6).
    tempvar w1 = message[-2];
    assert bitwise_ptr[0].x = w1;
    assert bitwise_ptr[0].y = shift_mask19;
    let w1_rot19 = (2 ** (64 - 19)) * w1 + (1 / 2 ** 19 - 2 ** (64 - 19)) * bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].x = w1;
    assert bitwise_ptr[1].y = shift_mask61;
    let w1_rot61 = (2 ** (64 - 61)) * w1 + (1 / 2 ** 61 - 2 ** (64 - 61)) * bitwise_ptr[1].x_and_y;
    assert bitwise_ptr[2].x = w1;
    assert bitwise_ptr[2].y = shift_mask6;
    let w1_shift6 = (1 / 2 ** 6) * bitwise_ptr[2].x_and_y;
    assert bitwise_ptr[3].x = w1_rot19;
    assert bitwise_ptr[3].y = w1_rot61;
    assert bitwise_ptr[4].x = bitwise_ptr[3].x_xor_y;
    assert bitwise_ptr[4].y = w1_shift6;
    let s1 = bitwise_ptr[4].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 5 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = message[-16] + s0 + message[-7] + s1;
    assert bitwise_ptr[0].y = mask64ones;
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
    local shift_mask28 = SHIFTS * (2 ** 64 - 2 ** 28);
    local shift_mask34 = SHIFTS * (2 ** 64 - 2 ** 34);
    local shift_mask39 = SHIFTS * (2 ** 64 - 2 ** 39);
    local shift_mask14 = SHIFTS * (2 ** 64 - 2 ** 14);
    local shift_mask18 = SHIFTS * (2 ** 64 - 2 ** 18);
    local shift_mask41 = SHIFTS * (2 ** 64 - 2 ** 41);
    local mask64ones = SHIFTS * (2 ** 64 - 1);

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
    tempvar n = 80;

    loop:
    // Compute s0 = right_rot(a, 28) ^ right_rot(a, 34) ^ right_rot(a, 39).
    assert bitwise_ptr[0].x = a;
    assert bitwise_ptr[0].y = shift_mask28;
    let a_rot28 = (2 ** (64 - 28)) * a + (1 / 2 ** 28 - 2 ** (64 - 28)) * bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].x = a;
    assert bitwise_ptr[1].y = shift_mask34;
    let a_rot34 = (2 ** (64 - 34)) * a + (1 / 2 ** 34 - 2 ** (64 - 34)) * bitwise_ptr[1].x_and_y;
    assert bitwise_ptr[2].x = a;
    assert bitwise_ptr[2].y = shift_mask39;
    let a_rot39 = (2 ** (64 - 39)) * a + (1 / 2 ** 39 - 2 ** (64 - 39)) * bitwise_ptr[2].x_and_y;
    assert bitwise_ptr[3].x = a_rot28;
    assert bitwise_ptr[3].y = a_rot34;
    assert bitwise_ptr[4].x = bitwise_ptr[3].x_xor_y;
    assert bitwise_ptr[4].y = a_rot39;
    let s0 = bitwise_ptr[4].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 5 * BitwiseBuiltin.SIZE;

    // Compute s1 = right_rot(e, 14) ^ right_rot(e, 18) ^ right_rot(e, 41).
    assert bitwise_ptr[0].x = e;
    assert bitwise_ptr[0].y = shift_mask14;
    let e_rot14 = (2 ** (64 - 14)) * e + (1 / 2 ** 14 - 2 ** (64 - 14)) * bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].x = e;
    assert bitwise_ptr[1].y = shift_mask18;
    let e_rot18 = (2 ** (64 - 18)) * e + (1 / 2 ** 18 - 2 ** (64 - 18)) * bitwise_ptr[1].x_and_y;
    assert bitwise_ptr[2].x = e;
    assert bitwise_ptr[2].y = shift_mask41;
    let e_rot41 = (2 ** (64 - 41)) * e + (1 / 2 ** 41 - 2 ** (64 - 41)) * bitwise_ptr[2].x_and_y;
    assert bitwise_ptr[3].x = e_rot14;
    assert bitwise_ptr[3].y = e_rot18;
    assert bitwise_ptr[4].x = bitwise_ptr[3].x_xor_y;
    assert bitwise_ptr[4].y = e_rot41;
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
    assert bitwise_ptr[0].y = mask64ones;
    let new_a = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].x = d + temp1;
    assert bitwise_ptr[1].y = mask64ones;
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
    assert bitwise_ptr[0].y = mask64ones;
    assert res[0] = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].x = state[1] + new_b;
    assert bitwise_ptr[1].y = mask64ones;
    assert res[1] = bitwise_ptr[1].x_and_y;
    assert bitwise_ptr[2].x = state[2] + new_c;
    assert bitwise_ptr[2].y = mask64ones;
    assert res[2] = bitwise_ptr[2].x_and_y;
    assert bitwise_ptr[3].x = state[3] + new_d;
    assert bitwise_ptr[3].y = mask64ones;
    assert res[3] = bitwise_ptr[3].x_and_y;
    assert bitwise_ptr[4].x = state[4] + new_e;
    assert bitwise_ptr[4].y = mask64ones;
    assert res[4] = bitwise_ptr[4].x_and_y;
    assert bitwise_ptr[5].x = state[5] + new_f;
    assert bitwise_ptr[5].y = mask64ones;
    assert res[5] = bitwise_ptr[5].x_and_y;
    assert bitwise_ptr[6].x = state[6] + new_g;
    assert bitwise_ptr[6].y = mask64ones;
    assert res[6] = bitwise_ptr[6].x_and_y;
    assert bitwise_ptr[7].x = state[7] + new_h;
    assert bitwise_ptr[7].y = mask64ones;
    assert res[7] = bitwise_ptr[7].x_and_y;
    let bitwise_ptr = bitwise_ptr + 8 * BitwiseBuiltin.SIZE;

    return (res,);
}

// Returns the 80 round constants of SHA512.
func get_round_constants() -> felt* {
    alloc_locals;
    let (round_constants) = get_label_location(data);
    return round_constants;

    data:
    dw 0x428A2F98D728AE22 * SHIFTS;
    dw 0x7137449123EF65CD * SHIFTS;
    dw 0xB5C0FBCFEC4D3B2F * SHIFTS;
    dw 0xE9B5DBA58189DBBC * SHIFTS;
    dw 0x3956C25BF348B538 * SHIFTS;
    dw 0x59F111F1B605D019 * SHIFTS;
    dw 0x923F82A4AF194F9B * SHIFTS;
    dw 0xAB1C5ED5DA6D8118 * SHIFTS;
    dw 0xD807AA98A3030242 * SHIFTS;
    dw 0x12835B0145706FBE * SHIFTS;
    dw 0x243185BE4EE4B28C * SHIFTS;
    dw 0x550C7DC3D5FFB4E2 * SHIFTS;
    dw 0x72BE5D74F27B896F * SHIFTS;
    dw 0x80DEB1FE3B1696B1 * SHIFTS;
    dw 0x9BDC06A725C71235 * SHIFTS;
    dw 0xC19BF174CF692694 * SHIFTS;
    dw 0xE49B69C19EF14AD2 * SHIFTS;
    dw 0xEFBE4786384F25E3 * SHIFTS;
    dw 0x0FC19DC68B8CD5B5 * SHIFTS;
    dw 0x240CA1CC77AC9C65 * SHIFTS;
    dw 0x2DE92C6F592B0275 * SHIFTS;
    dw 0x4A7484AA6EA6E483 * SHIFTS;
    dw 0x5CB0A9DCBD41FBD4 * SHIFTS;
    dw 0x76F988DA831153B5 * SHIFTS;
    dw 0x983E5152EE66DFAB * SHIFTS;
    dw 0xA831C66D2DB43210 * SHIFTS;
    dw 0xB00327C898FB213F * SHIFTS;
    dw 0xBF597FC7BEEF0EE4 * SHIFTS;
    dw 0xC6E00BF33DA88FC2 * SHIFTS;
    dw 0xD5A79147930AA725 * SHIFTS;
    dw 0x06CA6351E003826F * SHIFTS;
    dw 0x142929670A0E6E70 * SHIFTS;
    dw 0x27B70A8546D22FFC * SHIFTS;
    dw 0x2E1B21385C26C926 * SHIFTS;
    dw 0x4D2C6DFC5AC42AED * SHIFTS;
    dw 0x53380D139D95B3DF * SHIFTS;
    dw 0x650A73548BAF63DE * SHIFTS;
    dw 0x766A0ABB3C77B2A8 * SHIFTS;
    dw 0x81C2C92E47EDAEE6 * SHIFTS;
    dw 0x92722C851482353B * SHIFTS;
    dw 0xA2BFE8A14CF10364 * SHIFTS;
    dw 0xA81A664BBC423001 * SHIFTS;
    dw 0xC24B8B70D0F89791 * SHIFTS;
    dw 0xC76C51A30654BE30 * SHIFTS;
    dw 0xD192E819D6EF5218 * SHIFTS;
    dw 0xD69906245565A910 * SHIFTS;
    dw 0xF40E35855771202A * SHIFTS;
    dw 0x106AA07032BBD1B8 * SHIFTS;
    dw 0x19A4C116B8D2D0C8 * SHIFTS;
    dw 0x1E376C085141AB53 * SHIFTS;
    dw 0x2748774CDF8EEB99 * SHIFTS;
    dw 0x34B0BCB5E19B48A8 * SHIFTS;
    dw 0x391C0CB3C5C95A63 * SHIFTS;
    dw 0x4ED8AA4AE3418ACB * SHIFTS;
    dw 0x5B9CCA4F7763E373 * SHIFTS;
    dw 0x682E6FF3D6B2B8A3 * SHIFTS;
    dw 0x748F82EE5DEFB2FC * SHIFTS;
    dw 0x78A5636F43172F60 * SHIFTS;
    dw 0x84C87814A1F0AB72 * SHIFTS;
    dw 0x8CC702081A6439EC * SHIFTS;
    dw 0x90BEFFFA23631E28 * SHIFTS;
    dw 0xA4506CEBDE82BDE9 * SHIFTS;
    dw 0xBEF9A3F7B2C67915 * SHIFTS;
    dw 0xC67178F2E372532B * SHIFTS;
    dw 0xCA273ECEEA26619C * SHIFTS;
    dw 0xD186B8C721C0C207 * SHIFTS;
    dw 0xEADA7DD6CDE0EB1E * SHIFTS;
    dw 0xF57D4F7FEE6ED178 * SHIFTS;
    dw 0x06F067AA72176FBA * SHIFTS;
    dw 0x0A637DC5A2C898A6 * SHIFTS;
    dw 0x113F9804BEF90DAE * SHIFTS;
    dw 0x1B710B35131C471B * SHIFTS;
    dw 0x28DB77F523047D84 * SHIFTS;
    dw 0x32CAAB7B40C72493 * SHIFTS;
    dw 0x3C9EBE0A15C9BEBC * SHIFTS;
    dw 0x431D67C49C100D4C * SHIFTS;
    dw 0x4CC5D4BECB3E42B6 * SHIFTS;
    dw 0x597F299CFC657E2A * SHIFTS;
    dw 0x5FCB6FAB3AD6FAEC * SHIFTS;
    dw 0x6C44198C4A475817 * SHIFTS;
}

const SHA512_INPUT_CHUNK_SIZE_FELTS = 16;
const SHA512_STATE_SIZE_FELTS = 8;
// Each instance consists of a message (16 words), an input state (8 words),
// and an output state (8 words).
const SHA512_INSTANCE_SIZE = SHA512_INPUT_CHUNK_SIZE_FELTS + 2 * SHA512_STATE_SIZE_FELTS;

func _finalize_sha512_inner{range_check_ptr, bitwise_ptr: BitwiseBuiltin*}(
    sha512_ptr: felt*, n: felt, round_constants: felt*
) {
    if (n == 0) {
        return ();
    }

    alloc_locals;

    local U64_MAX = 2 ** 64 - 1;

    let sha512_start = sha512_ptr;

    let (local message_start: felt*) = alloc();

    // Handle message.

    tempvar message = message_start;
    tempvar sha512_ptr = sha512_ptr;
    tempvar range_check_ptr = range_check_ptr;
    tempvar m = SHA512_INPUT_CHUNK_SIZE_FELTS;

    message_loop:
    tempvar x0 = sha512_ptr[0 * SHA512_INSTANCE_SIZE];
    assert [range_check_ptr + 0] = x0;
    assert [range_check_ptr + 1] = U64_MAX - x0;
    tempvar x1 = sha512_ptr[1 * SHA512_INSTANCE_SIZE];
    assert [range_check_ptr + 2] = x1;
    assert [range_check_ptr + 3] = U64_MAX - x1;
    tempvar x2 = sha512_ptr[2 * SHA512_INSTANCE_SIZE];
    assert [range_check_ptr + 4] = x2;
    assert [range_check_ptr + 5] = U64_MAX - x2;
    assert message[0] = x0 + 2 ** 67 * x1 + 2 ** (67 * 2) * x2;

    tempvar message = message + 1;
    tempvar sha512_ptr = sha512_ptr + 1;
    tempvar range_check_ptr = range_check_ptr + 6;
    tempvar m = m - 1;
    jmp message_loop if m != 0;

    // Handle input state.

    let (local input_state_start: felt*) = alloc();
    tempvar input_state = input_state_start;
    tempvar sha512_ptr = sha512_ptr;
    tempvar range_check_ptr = range_check_ptr;
    tempvar m = SHA512_STATE_SIZE_FELTS;

    input_state_loop:
    tempvar x0 = sha512_ptr[0 * SHA512_INSTANCE_SIZE];
    assert [range_check_ptr + 0] = x0;
    assert [range_check_ptr + 1] = U64_MAX - x0;
    tempvar x1 = sha512_ptr[1 * SHA512_INSTANCE_SIZE];
    assert [range_check_ptr + 2] = x1;
    assert [range_check_ptr + 3] = U64_MAX - x1;
    tempvar x2 = sha512_ptr[2 * SHA512_INSTANCE_SIZE];
    assert [range_check_ptr + 4] = x2;
    assert [range_check_ptr + 5] = U64_MAX - x2;
    assert input_state[0] = x0 + 2 ** 67 * x1 + 2 ** (67 * 2) * x2;

    tempvar input_state = input_state + 1;
    tempvar sha512_ptr = sha512_ptr + 1;
    tempvar range_check_ptr = range_check_ptr + 6;
    tempvar m = m - 1;
    jmp input_state_loop if m != 0;

    // Run sha512 on the 3 instances.

    local sha512_ptr: felt* = sha512_ptr;
    local range_check_ptr = range_check_ptr;
    compute_message_schedule(message_start);
    let (outputs) = sha2_compress(input_state_start, message_start, round_constants);
    local bitwise_ptr: BitwiseBuiltin* = bitwise_ptr;

    // Handle outputs.

    tempvar outputs = outputs;
    tempvar sha512_ptr = sha512_ptr;
    tempvar range_check_ptr = range_check_ptr;
    tempvar m = SHA512_STATE_SIZE_FELTS;

    output_loop:
    tempvar x0 = sha512_ptr[0 * SHA512_INSTANCE_SIZE];
    assert [range_check_ptr] = x0;
    assert [range_check_ptr + 1] = U64_MAX - x0;
    tempvar x1 = sha512_ptr[1 * SHA512_INSTANCE_SIZE];
    assert [range_check_ptr + 2] = x1;
    assert [range_check_ptr + 3] = U64_MAX - x1;
    tempvar x2 = sha512_ptr[2 * SHA512_INSTANCE_SIZE];
    assert [range_check_ptr + 4] = x2;
    assert [range_check_ptr + 5] = U64_MAX - x2;

    assert outputs[0] = x0 + 2 ** 67 * x1 + 2 ** (67 * 2) * x2;

    tempvar outputs = outputs + 1;
    tempvar sha512_ptr = sha512_ptr + 1;
    tempvar range_check_ptr = range_check_ptr + 6;
    tempvar m = m - 1;
    jmp output_loop if m != 0;

    return _finalize_sha512_inner(
        sha512_ptr=sha512_start + SHA512_INSTANCE_SIZE * BATCH_SIZE,
        n=n - 1,
        round_constants=round_constants,
    );
}

// Verifies that [sha512_ptr_start:sha512_ptr_end] is an array of blocks of size 32
// where each block consist of 16 words of message, 8 words for the input state and 8 words
// for the output state.
func finalize_sha512{range_check_ptr, bitwise_ptr: BitwiseBuiltin*}(
    sha512_ptr_start: felt*, sha512_ptr_end: felt*
) {
    alloc_locals;

    tempvar n = (sha512_ptr_end - sha512_ptr_start) / SHA512_INSTANCE_SIZE;
    if (n == 0) {
        return ();
    }

    %{
        # Add dummy pairs of input and output.
        from starkware.cairo.common.cairo_sha512.sha512_utils import (
            SHA512_IV,
            compute_message_schedule,
            sha2_compress_function,
        )

        number_of_missing_blocks = (-ids.n) % ids.BATCH_SIZE
        assert 0 <= number_of_missing_blocks < 20
        _sha512_input_chunk_size_felts = ids.SHA512_INPUT_CHUNK_SIZE_FELTS
        assert 0 <= _sha512_input_chunk_size_felts < 100

        message = [0] * _sha512_input_chunk_size_felts
        w = compute_message_schedule(message)
        output = sha2_compress_function(SHA512_IV, w)
        padding = (message + SHA512_IV + output) * number_of_missing_blocks
        segments.write_arg(ids.sha512_ptr_end, padding)
    %}

    // Compute the amount of blocks (rounded up).
    let (local q, r) = unsigned_div_rem(n + BATCH_SIZE - 1, BATCH_SIZE);
    let round_constants = get_round_constants();
    _finalize_sha512_inner(sha512_ptr_start, n=q, round_constants=round_constants);
    return ();
}
