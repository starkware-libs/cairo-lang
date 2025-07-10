// This module provides a set of functions to compute the blake2s hash function.
//
// This module is similar to the keccak.cairo module. See more info there.

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_blake2s.packed_blake2s import N_PACKED_INSTANCES, blake2s_compress
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.math import assert_nn_le, split_felt, unsigned_div_rem
from starkware.cairo.common.math_cmp import is_le
from starkware.cairo.common.memcpy import memcpy
from starkware.cairo.common.memset import memset
from starkware.cairo.common.pow import pow
from starkware.cairo.common.registers import get_fp_and_pc, get_label_location
from starkware.cairo.common.uint256 import Uint256

const INPUT_BLOCK_FELTS = 16;
const INPUT_BLOCK_BYTES = 64;
const STATE_SIZE_FELTS = 8;
// Each instance consists of 8 words for the input state, 16 words of message,
// 2 words for t0 and f0, and 8 words for the output state.
const INSTANCE_SIZE = STATE_SIZE_FELTS + INPUT_BLOCK_FELTS + 2 + STATE_SIZE_FELTS;

// Computes blake2s of 'input'.
// To use this function, split the input into words of 32 bits (little endian).
// For example, to compute blake2s('Hello world'), use:
//   input = [1819043144, 1870078063, 6581362]
// where:
//   1819043144 == int.from_bytes(b'Hell', 'little')
//   1870078063 == int.from_bytes(b'o wo', 'little')
//   6581362 == int.from_bytes(b'rld', 'little')
//
// Returns the hash as a Uint256.
//
// Note: You must call finalize_blake2s() at the end of the program. Otherwise, this function
// is not sound and a malicious prover may return a wrong result.
// Note: the interface of this function may change in the future.
// Note: Each input word is verified to be in the range [0, 2 ** 32) by this function.
func blake2s{range_check_ptr, blake2s_ptr: felt*}(data: felt*, n_bytes: felt) -> (res: Uint256) {
    let (output) = blake2s_as_words(data=data, n_bytes=n_bytes);
    let res_low = output[3] * 2 ** 96 + output[2] * 2 ** 64 + output[1] * 2 ** 32 + output[0];
    let res_high = output[7] * 2 ** 96 + output[6] * 2 ** 64 + output[5] * 2 ** 32 + output[4];
    return (res=Uint256(low=res_low, high=res_high));
}

// Computes blake2s of 'input', and returns the hash in big endian representation.
// See blake2s().
// Note that the input is still treated as little endian.
func blake2s_bigend{bitwise_ptr: BitwiseBuiltin*, range_check_ptr, blake2s_ptr: felt*}(
    data: felt*, n_bytes: felt
) -> (res: Uint256) {
    let (num) = blake2s(data=data, n_bytes=n_bytes);

    // Reverse byte endianness of 128-bit words.
    tempvar value = num.high;
    assert bitwise_ptr[0].x = value;
    assert bitwise_ptr[0].y = 0x00ff00ff00ff00ff00ff00ff00ff00ff;
    tempvar value = value + (2 ** 16 - 1) * bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].x = value;
    assert bitwise_ptr[1].y = 0x00ffff0000ffff0000ffff0000ffff00;
    tempvar value = value + (2 ** 32 - 1) * bitwise_ptr[1].x_and_y;
    assert bitwise_ptr[2].x = value;
    assert bitwise_ptr[2].y = 0x00ffffffff00000000ffffffff000000;
    tempvar value = value + (2 ** 64 - 1) * bitwise_ptr[2].x_and_y;
    assert bitwise_ptr[3].x = value;
    assert bitwise_ptr[3].y = 0x00ffffffffffffffff00000000000000;
    tempvar value = value + (2 ** 128 - 1) * bitwise_ptr[3].x_and_y;
    tempvar high = value / 2 ** (8 + 16 + 32 + 64);
    let bitwise_ptr = bitwise_ptr + 4 * BitwiseBuiltin.SIZE;

    tempvar value = num.low;
    assert bitwise_ptr[0].x = value;
    assert bitwise_ptr[0].y = 0x00ff00ff00ff00ff00ff00ff00ff00ff;
    tempvar value = value + (2 ** 16 - 1) * bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].x = value;
    assert bitwise_ptr[1].y = 0x00ffff0000ffff0000ffff0000ffff00;
    tempvar value = value + (2 ** 32 - 1) * bitwise_ptr[1].x_and_y;
    assert bitwise_ptr[2].x = value;
    assert bitwise_ptr[2].y = 0x00ffffffff00000000ffffffff000000;
    tempvar value = value + (2 ** 64 - 1) * bitwise_ptr[2].x_and_y;
    assert bitwise_ptr[3].x = value;
    assert bitwise_ptr[3].y = 0x00ffffffffffffffff00000000000000;
    tempvar value = value + (2 ** 128 - 1) * bitwise_ptr[3].x_and_y;
    tempvar low = value / 2 ** (8 + 16 + 32 + 64);
    let bitwise_ptr = bitwise_ptr + 4 * BitwiseBuiltin.SIZE;

    return (res=Uint256(low=high, high=low));
}

// Same as blake2s, but outputs a pointer to 8 32-bit little endian words instead.
func blake2s_as_words{range_check_ptr, blake2s_ptr: felt*}(data: felt*, n_bytes: felt) -> (
    output: felt*
) {
    // Set the initial state to IV (IV[0] is modified).
    assert blake2s_ptr[0] = 0x6B08E647;  // IV[0] ^ 0x01010020 (config: no key, 32 bytes output).
    assert blake2s_ptr[1] = 0xBB67AE85;
    assert blake2s_ptr[2] = 0x3C6EF372;
    assert blake2s_ptr[3] = 0xA54FF53A;
    assert blake2s_ptr[4] = 0x510E527F;
    assert blake2s_ptr[5] = 0x9B05688C;
    assert blake2s_ptr[6] = 0x1F83D9AB;
    assert blake2s_ptr[7] = 0x5BE0CD19;
    static_assert STATE_SIZE_FELTS == 8;
    let blake2s_ptr = blake2s_ptr + STATE_SIZE_FELTS;

    let (output) = blake2s_inner(data=data, n_bytes=n_bytes, counter=0);
    return (output=output);
}

// Inner loop for blake2s. blake2s_ptr points to the middle of an instance: after the initial state,
// before the message.
func blake2s_inner{range_check_ptr, blake2s_ptr: felt*}(
    data: felt*, n_bytes: felt, counter: felt
) -> (output: felt*) {
    alloc_locals;
    let is_last_block = is_le(n_bytes, INPUT_BLOCK_BYTES);
    if (is_last_block != 0) {
        return blake2s_last_block(data=data, n_bytes=n_bytes, counter=counter);
    }

    memcpy(blake2s_ptr, data, INPUT_BLOCK_FELTS);
    let blake2s_ptr = blake2s_ptr + INPUT_BLOCK_FELTS;

    assert blake2s_ptr[0] = counter + INPUT_BLOCK_BYTES;  // n_bytes.
    assert blake2s_ptr[1] = 0;  // Is last byte = False.
    let blake2s_ptr = blake2s_ptr + 2;

    // Write output.
    let output = blake2s_ptr;
    %{
        from starkware.cairo.common.cairo_blake2s.blake2s_utils import compute_blake2s_func
        compute_blake2s_func(segments=segments, output_ptr=ids.output)
    %}
    let blake2s_ptr = blake2s_ptr + STATE_SIZE_FELTS;

    // Write the current output to the input state for the next instance.
    memcpy(blake2s_ptr, output, STATE_SIZE_FELTS);
    let blake2s_ptr = blake2s_ptr + STATE_SIZE_FELTS;
    return blake2s_inner(
        data=data + INPUT_BLOCK_FELTS,
        n_bytes=n_bytes - INPUT_BLOCK_BYTES,
        counter=counter + INPUT_BLOCK_BYTES,
    );
}

func blake2s_last_block{range_check_ptr, blake2s_ptr: felt*}(
    data: felt*, n_bytes: felt, counter: felt
) -> (output: felt*) {
    alloc_locals;
    let (n_felts, _) = unsigned_div_rem(n_bytes + 3, 4);
    memcpy(blake2s_ptr, data, n_felts);
    memset(blake2s_ptr + n_felts, 0, INPUT_BLOCK_FELTS - n_felts);
    let blake2s_ptr = blake2s_ptr + INPUT_BLOCK_FELTS;

    assert blake2s_ptr[0] = counter + n_bytes;  // n_bytes.
    assert blake2s_ptr[1] = 0xffffffff;  // Is last byte = True.
    let blake2s_ptr = blake2s_ptr + 2;

    // Write output.
    let output = blake2s_ptr;
    %{
        from starkware.cairo.common.cairo_blake2s.blake2s_utils import compute_blake2s_func
        compute_blake2s_func(segments=segments, output_ptr=ids.output)
    %}
    let blake2s_ptr = blake2s_ptr + STATE_SIZE_FELTS;

    return (output=output);
}

// Verifies that the results of blake2s() are valid.
func finalize_blake2s{range_check_ptr, bitwise_ptr: BitwiseBuiltin*}(
    blake2s_ptr_start: felt*, blake2s_ptr_end: felt*
) {
    alloc_locals;

    let (__fp__, _) = get_fp_and_pc();

    let (sigma) = _get_sigma();

    tempvar n = (blake2s_ptr_end - blake2s_ptr_start) / INSTANCE_SIZE;
    if (n == 0) {
        return ();
    }

    %{
        # Add dummy pairs of input and output.
        from starkware.cairo.common.cairo_blake2s.blake2s_utils import IV, blake2s_compress

        _n_packed_instances = int(ids.N_PACKED_INSTANCES)
        assert 0 <= _n_packed_instances < 20
        _blake2s_input_chunk_size_felts = int(ids.INPUT_BLOCK_FELTS)
        assert 0 <= _blake2s_input_chunk_size_felts < 100

        message = [0] * _blake2s_input_chunk_size_felts
        modified_iv = [IV[0] ^ 0x01010020] + IV[1:]
        output = blake2s_compress(
            message=message,
            h=modified_iv,
            t0=0,
            t1=0,
            f0=0xffffffff,
            f1=0,
        )
        padding = (modified_iv + message + [0, 0xffffffff] + output) * (_n_packed_instances - 1)
        segments.write_arg(ids.blake2s_ptr_end, padding)
    %}

    // Compute the amount of chunks (rounded up).
    let (local n_chunks, _) = unsigned_div_rem(n + N_PACKED_INSTANCES - 1, N_PACKED_INSTANCES);
    let blake2s_ptr = blake2s_ptr_start;
    _finalize_blake2s_inner{blake2s_ptr=blake2s_ptr}(n=n_chunks, sigma=sigma);
    return ();
}

func _get_sigma() -> (sigma: felt*) {
    alloc_locals;
    let (sigma_address) = get_label_location(data);
    return (sigma=cast(sigma_address, felt*));

    data:
    dw 0;
    dw 1;
    dw 2;
    dw 3;
    dw 4;
    dw 5;
    dw 6;
    dw 7;
    dw 8;
    dw 9;
    dw 10;
    dw 11;
    dw 12;
    dw 13;
    dw 14;
    dw 15;
    dw 14;
    dw 10;
    dw 4;
    dw 8;
    dw 9;
    dw 15;
    dw 13;
    dw 6;
    dw 1;
    dw 12;
    dw 0;
    dw 2;
    dw 11;
    dw 7;
    dw 5;
    dw 3;
    dw 11;
    dw 8;
    dw 12;
    dw 0;
    dw 5;
    dw 2;
    dw 15;
    dw 13;
    dw 10;
    dw 14;
    dw 3;
    dw 6;
    dw 7;
    dw 1;
    dw 9;
    dw 4;
    dw 7;
    dw 9;
    dw 3;
    dw 1;
    dw 13;
    dw 12;
    dw 11;
    dw 14;
    dw 2;
    dw 6;
    dw 5;
    dw 10;
    dw 4;
    dw 0;
    dw 15;
    dw 8;
    dw 9;
    dw 0;
    dw 5;
    dw 7;
    dw 2;
    dw 4;
    dw 10;
    dw 15;
    dw 14;
    dw 1;
    dw 11;
    dw 12;
    dw 6;
    dw 8;
    dw 3;
    dw 13;
    dw 2;
    dw 12;
    dw 6;
    dw 10;
    dw 0;
    dw 11;
    dw 8;
    dw 3;
    dw 4;
    dw 13;
    dw 7;
    dw 5;
    dw 15;
    dw 14;
    dw 1;
    dw 9;
    dw 12;
    dw 5;
    dw 1;
    dw 15;
    dw 14;
    dw 13;
    dw 4;
    dw 10;
    dw 0;
    dw 7;
    dw 6;
    dw 3;
    dw 9;
    dw 2;
    dw 8;
    dw 11;
    dw 13;
    dw 11;
    dw 7;
    dw 14;
    dw 12;
    dw 1;
    dw 3;
    dw 9;
    dw 5;
    dw 0;
    dw 15;
    dw 4;
    dw 8;
    dw 6;
    dw 2;
    dw 10;
    dw 6;
    dw 15;
    dw 14;
    dw 9;
    dw 11;
    dw 3;
    dw 0;
    dw 8;
    dw 12;
    dw 2;
    dw 13;
    dw 7;
    dw 1;
    dw 4;
    dw 10;
    dw 5;
    dw 10;
    dw 2;
    dw 8;
    dw 4;
    dw 7;
    dw 6;
    dw 1;
    dw 5;
    dw 15;
    dw 11;
    dw 9;
    dw 14;
    dw 3;
    dw 12;
    dw 13;
    dw 0;
}

// Handles n chunks of N_PACKED_INSTANCES blake2s instances.
func _finalize_blake2s_inner{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, blake2s_ptr: felt*}(
    n: felt, sigma: felt*
) {
    if (n == 0) {
        return ();
    }

    alloc_locals;
    let blake2s_start = blake2s_ptr;

    // Load instance data.
    let (local data: felt*) = alloc();
    _pack_ints(INSTANCE_SIZE, data);

    let input_state: felt* = data;
    let message: felt* = input_state + STATE_SIZE_FELTS;
    let t0_and_f0: felt* = message + INPUT_BLOCK_FELTS;
    let output_state: felt* = t0_and_f0 + 2;

    // Run blake2s on N_PACKED_INSTANCES instances.
    blake2s_compress(
        h=input_state,
        message=message,
        t0=t0_and_f0[0],
        f0=t0_and_f0[1],
        sigma=sigma,
        output=output_state,
    );
    let blake2s_ptr = blake2s_start + INSTANCE_SIZE * N_PACKED_INSTANCES;

    return _finalize_blake2s_inner(n=n - 1, sigma=sigma);
}

// Given N_PACKED_INSTANCES sets of m (32-bit) integers in the blake2s implicit argument,
// where each set starts at offset INSTANCE_SIZE from the previous set,
// computes m packed integers.
// blake2s_ptr is advanced m steps (just after the first set).
func _pack_ints{range_check_ptr, blake2s_ptr: felt*}(m, packed_values: felt*) {
    static_assert N_PACKED_INSTANCES == 7;
    alloc_locals;

    local MAX_VALUE = 2 ** 32 - 1;

    tempvar packed_values = packed_values;
    tempvar blake2s_ptr = blake2s_ptr;
    tempvar range_check_ptr = range_check_ptr;
    tempvar m = m;

    loop:
    tempvar x0 = blake2s_ptr[0 * INSTANCE_SIZE];
    assert [range_check_ptr + 0] = x0;
    assert [range_check_ptr + 1] = MAX_VALUE - x0;
    tempvar x1 = blake2s_ptr[1 * INSTANCE_SIZE];
    assert [range_check_ptr + 2] = x1;
    assert [range_check_ptr + 3] = MAX_VALUE - x1;
    tempvar x2 = blake2s_ptr[2 * INSTANCE_SIZE];
    assert [range_check_ptr + 4] = x2;
    assert [range_check_ptr + 5] = MAX_VALUE - x2;
    tempvar x3 = blake2s_ptr[3 * INSTANCE_SIZE];
    assert [range_check_ptr + 6] = x3;
    assert [range_check_ptr + 7] = MAX_VALUE - x3;
    tempvar x4 = blake2s_ptr[4 * INSTANCE_SIZE];
    assert [range_check_ptr + 8] = x4;
    assert [range_check_ptr + 9] = MAX_VALUE - x4;
    tempvar x5 = blake2s_ptr[5 * INSTANCE_SIZE];
    assert [range_check_ptr + 10] = x5;
    assert [range_check_ptr + 11] = MAX_VALUE - x5;
    tempvar x6 = blake2s_ptr[6 * INSTANCE_SIZE];
    assert [range_check_ptr + 12] = x6;
    assert [range_check_ptr + 13] = MAX_VALUE - x6;
    assert packed_values[0] = (
        x0 +
        2 ** 35 * x1 +
        2 ** (35 * 2) * x2 +
        2 ** (35 * 3) * x3 +
        2 ** (35 * 4) * x4 +
        2 ** (35 * 5) * x5 +
        2 ** (35 * 6) * x6
    );

    tempvar packed_values = packed_values + 1;
    tempvar blake2s_ptr = blake2s_ptr + 1;
    tempvar range_check_ptr = range_check_ptr + 14;
    tempvar m = m - 1;
    jmp loop if m != 0;

    return ();
}

// Helper functions.
// These functions serialize data to a data array to be used with blake2s().
// They use the property that each data word is verified by blake2s() to be in range [0, 2 ** 32).

// Serializes a uint256 number in a blake2s compatible way (little-endian).
func blake2s_add_uint256{data: felt*}(num: Uint256) {
    let high = num.high;
    let low = num.low;
    %{
        B = 32
        MASK = 2 ** 32 - 1
        segments.write_arg(ids.data, [(ids.low >> (B * i)) & MASK for i in range(4)])
        segments.write_arg(ids.data + 4, [(ids.high >> (B * i)) & MASK for i in range(4)])
    %}
    assert data[3] * 2 ** 96 + data[2] * 2 ** 64 + data[1] * 2 ** 32 + data[0] = low;
    assert data[7] * 2 ** 96 + data[6] * 2 ** 64 + data[5] * 2 ** 32 + data[4] = high;
    let data = data + 8;
    return ();
}

// Serializes a uint256 number in a blake2s compatible way (big-endian).
func blake2s_add_uint256_bigend{bitwise_ptr: BitwiseBuiltin*, data: felt*}(num: Uint256) {
    // Reverse byte endianness of 32-bit chunks.
    tempvar value = num.high;
    assert bitwise_ptr[0].x = value;
    assert bitwise_ptr[0].y = 0x00ff00ff00ff00ff00ff00ff00ff00ff;
    tempvar value = value + (2 ** 16 - 1) * bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].x = value;
    assert bitwise_ptr[1].y = 0x00ffff0000ffff0000ffff0000ffff00;
    tempvar value = value + (2 ** 32 - 1) * bitwise_ptr[1].x_and_y;
    tempvar high = value / 2 ** (8 + 16);

    tempvar value = num.low;
    assert bitwise_ptr[2].x = value;
    assert bitwise_ptr[2].y = 0x00ff00ff00ff00ff00ff00ff00ff00ff;
    tempvar value = value + (2 ** 16 - 1) * bitwise_ptr[2].x_and_y;
    assert bitwise_ptr[3].x = value;
    assert bitwise_ptr[3].y = 0x00ffff0000ffff0000ffff0000ffff00;
    tempvar value = value + (2 ** 32 - 1) * bitwise_ptr[3].x_and_y;
    tempvar low = value / 2 ** (8 + 16);

    let bitwise_ptr = bitwise_ptr + 4 * BitwiseBuiltin.SIZE;

    %{
        B = 32
        MASK = 2 ** 32 - 1
        segments.write_arg(ids.data, [(ids.high >> (B * (3 - i))) & MASK for i in range(4)])
        segments.write_arg(ids.data + 4, [(ids.low >> (B * (3 - i))) & MASK for i in range(4)])
    %}

    assert data[0] * 2 ** 96 + data[1] * 2 ** 64 + data[2] * 2 ** 32 + data[3] = high;
    assert data[4] * 2 ** 96 + data[5] * 2 ** 64 + data[6] * 2 ** 32 + data[7] = low;
    let data = data + 8;
    return ();
}

// Serializes a field element in a blake2s compatible way.
func blake2s_add_felt{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, data: felt*}(
    num: felt, bigend: felt
) {
    let (high, low) = split_felt(num);
    if (bigend != 0) {
        blake2s_add_uint256_bigend(Uint256(low=low, high=high));
        return ();
    } else {
        blake2s_add_uint256(Uint256(low=low, high=high));
        return ();
    }
}

// Serializes multiple field elements in a blake2s compatible way.
// Note: This function does not serialize the number of elements. If desired, this is the caller's
// responsibility.
func blake2s_add_felts{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, data: felt*}(
    n_elements: felt, elements: felt*, bigend: felt
) -> () {
    if (n_elements == 0) {
        return ();
    }
    blake2s_add_felt(num=elements[0], bigend=bigend);
    return blake2s_add_felts(n_elements=n_elements - 1, elements=&elements[1], bigend=bigend);
}

// Computes the blake2s hash for multiple field elements.
func blake2s_felts{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, blake2s_ptr: felt*}(
    n_elements: felt, elements: felt*, bigend: felt
) -> (res: Uint256) {
    alloc_locals;
    let (data) = alloc();
    let data_start = data;
    with data {
        blake2s_add_felts(n_elements=n_elements, elements=elements, bigend=bigend);
    }
    let (res) = blake2s(data=data_start, n_bytes=n_elements * 32);
    return (res=res);
}

// Takes an array of `packed_values_len` felt252s at `packed_values` and encodes them into an array
// of u32s at `unpacked_u32s` in the following way:
//  * If a felt is less than 2^63, it's unpacked to 2 felts, each representing 32 bits.
//  * Otherwise, it's unpacked into 8 felts, each under 2^32, where the most significant
//    limb has its MSB set (Note that the prime is less than 2^255 so the MSB could not be
//    set prior to this intervention).
// All 32-bit limbs are arranged in big-endian order.
// Returns the size of the unpacked array in felts.
// Assumes:
//  * All output felts in `upnacked_u32s` are extrenally verified to be in [0, 2^32).
// Note: This function can nondeterministically choose between several encodings of felts,
//      x < PRIME can be encoded as x + PRIME, x + 2 * PRIME, etc. The canonical encoding is
//      given when x < PRIME.
func encode_felt252_to_u32s{range_check_ptr: felt}(
    packed_values_len: felt, packed_values: felt*, unpacked_u32s: felt*
) -> felt {
    alloc_locals;

    local U63_MAX = 2 ** 63 - 1;
    local EXP31 = 2 ** 31;
    local end = cast(packed_values, felt) + packed_values_len;

    %{
        offset = 0
        for i in range(ids.packed_values_len):
            val = (memory[ids.packed_values + i] % PRIME)
            val_len = 2 if val < 2**63 else 8
            if val_len == 8:
                val += 2**255
            for i in range(val_len - 1, -1, -1):
                val, memory[ids.unpacked_u32s + offset + i] = divmod(val, 2**32)
            assert val == 0
            offset += val_len
    %}
    tempvar out = unpacked_u32s;
    tempvar packed_values = packed_values;
    tempvar range_check_ptr = range_check_ptr;

    loop:
    // Guess if number is small or big.
    if (nondet %{ (ids.end != ids.packed_values) and (memory[ids.packed_values] < 2**63) %} != 0) {
        // Unpack small felt.

        tempvar current_val = packed_values[0];
        // Assert that the value is in [0, 2^63).
        assert [range_check_ptr] = U63_MAX - current_val;
        // Assert that the limbs represent the number.
        assert current_val = out[1] + 2 ** 32 * out[0];

        tempvar out = &out[2];
        tempvar packed_values = &packed_values[1];
        tempvar range_check_ptr = range_check_ptr + 1;
        jmp loop;
    }

    if (end - cast(packed_values, felt) == 0) {
        return out - unpacked_u32s;
    }

    // Handle big felt.
    // Assert that the top limb is over 2^31, as its MSB is artificially set for encoding.
    tempvar raw_out_0 = out[0] - EXP31;
    assert [range_check_ptr] = raw_out_0;
    // Assert that the limbs represent the number. Set the MSB of the most significant limb.
    assert packed_values[0] = (
        (out[7] + (2 ** 32 * out[6])) +
        2 ** (32 * 2) * (out[5] + 2 ** 32 * out[4]) +
        2 ** (32 * 4) * (out[3] + 2 ** 32 * out[2]) +
        2 ** (32 * 6) * (out[1] + 2 ** 32 * raw_out_0)
    );

    tempvar out = &out[8];
    tempvar packed_values = &packed_values[1];
    tempvar range_check_ptr = range_check_ptr + 1;
    jmp loop;
}

const OP1_AP = 4;
const BLAKE2S_OPCODE_EXT = 1;
const BLAKE2S_FINALIZE_OPCODE_EXT = 2;
const BLAKE2S_AP_FLAGS = OP1_AP * (2 ** 2);

const OFF_MINUS_1 = 2 ** 15 - 1;
const OFF_MINUS_2 = 2 ** 15 - 2;
const OFF_MINUS_3 = 2 ** 15 - 3;
const OFF_MINUS_4 = 2 ** 15 - 4;

const COUNTER_OFFSET = 1;
const STATE_OFFSET = 2 ** 16;
const MESSAGE_OFFSET = 2 ** 32;
const FLAGS_OFFSET = 2 ** 48;
const OPCODE_EXT_OFFSET = 2 ** 63;

const BLAKE2S_INSTRUCTION = OFF_MINUS_1 * COUNTER_OFFSET + OFF_MINUS_4 * STATE_OFFSET +
    OFF_MINUS_3 * MESSAGE_OFFSET + BLAKE2S_AP_FLAGS * FLAGS_OFFSET + BLAKE2S_OPCODE_EXT *
    OPCODE_EXT_OFFSET;
const BLAKE2S_FINALIZE_INSTRUCTION = OFF_MINUS_1 * COUNTER_OFFSET + OFF_MINUS_3 * STATE_OFFSET +
    OFF_MINUS_2 * MESSAGE_OFFSET + BLAKE2S_AP_FLAGS * FLAGS_OFFSET + BLAKE2S_FINALIZE_OPCODE_EXT *
    OPCODE_EXT_OFFSET;

// Computes blake2s of `input` of size `len` felts, representing 32 bits each.
// Note: this function guarantees that len > 0.
func blake_with_opcode{range_check_ptr}(len: felt, data: felt*, out: felt*) {
    alloc_locals;

    let (local state: felt*) = alloc();
    assert state[0] = 0x6B08E647;  // IV[0] ^ 0x01010020 (config: no key, 32 bytes output).
    assert state[1] = 0xBB67AE85;
    assert state[2] = 0x3C6EF372;
    assert state[3] = 0xA54FF53A;
    assert state[4] = 0x510E527F;
    assert state[5] = 0x9B05688C;
    assert state[6] = 0x1F83D9AB;
    assert state[7] = 0x5BE0CD19;

    // Express the length in bytes, subtract the remainder for finalize.
    let (_, rem) = unsigned_div_rem(len - 1, 16);
    local rem = rem + 1;
    local len_in_bytes = (len - rem) * 4;

    local range_check_ptr = range_check_ptr;

    // Copy remaining data and pad with zeroes.
    let (local final_data: felt*) = alloc();
    memcpy(final_data, &data[len - rem], rem);
    memset(&final_data[rem], 0, 16 - rem);

    tempvar counter = 0;
    tempvar state = state;
    tempvar data = data;

    loop:
    if (counter - len_in_bytes == 0) {
        // Add remainder bytes to counter.
        tempvar counter = counter + (rem * 4);
        [ap] = state, ap++;
        [ap] = final_data, ap++;
        [ap] = counter, ap++;
        [ap] = out;
        dw BLAKE2S_FINALIZE_INSTRUCTION;
        // Increment AP after blake opcode.
        ap += 1;

        let range_check_ptr = [fp + 3];
        return ();
    }

    tempvar counter = counter + 64;

    // Blake output pointer / the next state.
    [ap] = &state[8];
    dw BLAKE2S_INSTRUCTION;

    let state = cast([ap - 4], felt*);
    let data = cast([ap - 3], felt*);

    // Increment AP after blake opcode.
    ap += 1;

    tempvar data = data + 16;
    jmp loop;
}

// Given `data_len` felt252s at `data`, encodes them as u32s as defined in `encode_felt252_to_u32s`
// and computes the blake2s hash of the result using the dedicated opcodes.
// The 256 bit result is then returned as a felt252 (i.e. modulo PRIME).
func encode_felt252_data_and_calc_blake_hash{range_check_ptr: felt}(
    data_len: felt, data: felt*
) -> (hash: felt) {
    alloc_locals;
    let (local encoded_data: felt*) = alloc();
    let encoded_data_len = encode_felt252_to_u32s(
        packed_values_len=data_len, packed_values=data, unpacked_u32s=encoded_data
    );
    let (local blake_output: felt*) = alloc();
    blake_with_opcode(len=encoded_data_len, data=encoded_data, out=blake_output);
    return (
        hash=blake_output[7] * 2 ** 224 + blake_output[6] * 2 ** 192 + blake_output[5] * 2 ** 160 +
        blake_output[4] * 2 ** 128 + blake_output[3] * 2 ** 96 + blake_output[2] * 2 ** 64 +
        blake_output[1] * 2 ** 32 + blake_output[0],
    );
}
