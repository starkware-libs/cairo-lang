// This module provides a set of functions to compute the (Ethereum compatible) keccak hash
// function using the keccak builtin.
//
// All public functions here get the ``keccak_ptr`` implicit argument, it is expected to be the
// pointer to the keccak builtin segment (not to be confused with the keccak_ptr in the Cairo
// implementation of keccak).
//
// The module uses the same helper functions as in the non-builtin keccak implementation
// (e.g. ``keccak_add_uint256()`` and ``keccak_add_felt()``). To use them, you should allocate a new
// memory segment to a variable named ``inputs`` (this value is an implicit argument to those
// functions). Once the input is ready, you should call ``keccak()`` or ``keccak_bigend()``.

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin, KeccakBuiltin
from starkware.cairo.common.keccak_state import KeccakBuiltinState
from starkware.cairo.common.keccak_utils.keccak_utils import keccak_add_felts, keccak_add_uint256s
from starkware.cairo.common.memcpy import memcpy
from starkware.cairo.common.memset import memset
from starkware.cairo.common.registers import get_label_location
from starkware.cairo.common.uint256 import Uint256, uint256_reverse_endian

const KECCAK_FULL_RATE_IN_BYTES = 136;
const KECCAK_FULL_RATE_IN_WORDS = 17;
const BYTES_IN_WORD = 8;

// Computes the keccak hash of multiple uint256 numbers.
func keccak_uint256s{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, keccak_ptr: KeccakBuiltin*}(
    n_elements: felt, elements: Uint256*
) -> (res: Uint256) {
    alloc_locals;

    let (inputs) = alloc();
    let inputs_start = inputs;

    keccak_add_uint256s{inputs=inputs}(n_elements=n_elements, elements=elements, bigend=0);

    return keccak(inputs=inputs_start, n_bytes=n_elements * 32);
}

// Computes the keccak hash of multiple uint256 numbers (big-endian).
// Note that both the output and the input are in big endian representation.
func keccak_uint256s_bigend{
    range_check_ptr, bitwise_ptr: BitwiseBuiltin*, keccak_ptr: KeccakBuiltin*
}(n_elements: felt, elements: Uint256*) -> (res: Uint256) {
    alloc_locals;

    let (inputs) = alloc();
    let inputs_start = inputs;

    keccak_add_uint256s{inputs=inputs}(n_elements=n_elements, elements=elements, bigend=1);

    return keccak_bigend(inputs=inputs_start, n_bytes=n_elements * 32);
}

// Computes the keccak hash of multiple field elements.
func keccak_felts{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, keccak_ptr: KeccakBuiltin*}(
    n_elements: felt, elements: felt*
) -> (res: Uint256) {
    alloc_locals;

    let (inputs) = alloc();
    let inputs_start = inputs;

    keccak_add_felts{inputs=inputs}(n_elements=n_elements, elements=elements, bigend=0);

    return keccak(inputs=inputs_start, n_bytes=n_elements * 32);
}

// Computes the keccak hash of multiple field elements (big-endian).
// Note that both the output and the input are in big endian representation.
func keccak_felts_bigend{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, keccak_ptr: KeccakBuiltin*}(
    n_elements: felt, elements: felt*
) -> (res: Uint256) {
    alloc_locals;

    let (inputs) = alloc();
    let inputs_start = inputs;

    keccak_add_felts{inputs=inputs}(n_elements=n_elements, elements=elements, bigend=1);

    return keccak_bigend(inputs=inputs_start, n_bytes=n_elements * 32);
}

// Converts a final state of the Keccak builtin to the hash output as `Uint256`.
@known_ap_change
func _keccak_output_to_uint256{range_check_ptr, bitwise_ptr: BitwiseBuiltin*}(
    output: KeccakBuiltinState*
) -> (res: Uint256) {
    tempvar output0 = output.s0;
    tempvar output1 = output.s1;

    // Split output0 into output0_low (16 bytes) and output0_high (9 bytes).
    let output0_low = [range_check_ptr];
    let output0_high = [range_check_ptr + 1];
    %{
        ids.output0_low = ids.output0 & ((1 << 128) - 1)
        ids.output0_high = ids.output0 >> 128
    %}
    assert [range_check_ptr + 2] = output0_high - 256 ** 9 + 2 ** 128;
    assert output0 = output0_low + output0_high * (2 ** 128);

    // Split output1 into output1_low (7 bytes), output1_mid (16 bytes) and output1_high (2 bytes).
    let output1_low = [range_check_ptr + 3];
    let output1_mid = [range_check_ptr + 4];
    let output1_high = [range_check_ptr + 5];
    %{
        tmp, ids.output1_low = divmod(ids.output1, 256 ** 7)
        ids.output1_high, ids.output1_mid = divmod(tmp, 2 ** 128)
    %}
    assert [range_check_ptr + 6] = output1_low - 256 ** 7 + 2 ** 128;
    assert [range_check_ptr + 7] = output1_high - 256 ** 2 + 2 ** 128;
    assert output1 = output1_low + output1_mid * 256 ** 7 + output1_high * 256 ** 23;

    let range_check_ptr = range_check_ptr + 8;
    let res_high = output0_high + output1_low * 256 ** 9;
    return (res=Uint256(low=output0_low, high=res_high));
}

// Computes the keccak of 'input'.
// To use this function, split the input into words of 64 bits (little endian).
// For example, to compute keccak('Hello world!'), use:
//   inputs = [8031924123371070792, 560229490]
// where:
//   8031924123371070792 == int.from_bytes(b'Hello wo', 'little')
//   560229490 == int.from_bytes(b'rld!', 'little')
//
// Returns the hash as a Uint256.
func keccak{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, keccak_ptr: KeccakBuiltin*}(
    inputs: felt*, n_bytes: felt
) -> (res: Uint256) {
    let (output) = keccak_final_state(inputs=inputs, n_bytes=n_bytes);

    let res = _keccak_output_to_uint256(output);
    return res;
}

// Same as keccak, but outputs the hash in big endian representation.
// Note that the input is still treated as little endian.
func keccak_bigend{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, keccak_ptr: KeccakBuiltin*}(
    inputs: felt*, n_bytes: felt
) -> (res: Uint256) {
    let (hash) = keccak(inputs=inputs, n_bytes=n_bytes);
    let (res) = uint256_reverse_endian(num=hash);
    return (res=res);
}

// Same as keccak, but outputs a pointer to the final state instead.
func keccak_final_state{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, keccak_ptr: KeccakBuiltin*}(
    inputs: felt*, n_bytes: felt
) -> (output: KeccakBuiltinState*) {
    alloc_locals;
    tempvar state = new KeccakBuiltinState(s0=0, s1=0, s2=0, s3=0, s4=0, s5=0, s6=0, s7=0);
    return _keccak(inputs=inputs, n_bytes=n_bytes, state=state);
}

// Xors the last keccak state with 'inputs' and stores the result in keccak_ptr.
// Assumes that 'inputs' is 136 bytes long.
//
// inputs: a pointer to 64 bit words.
// state: a pointer to 200 bit elements.
func _prepare_full_block{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, keccak_ptr: KeccakBuiltin*}(
    inputs: felt*, state: KeccakBuiltinState*
) {
    // Assert that inputs[0], inputs[1] and inputs[2] consist of 8 bytes each.
    assert [range_check_ptr] = inputs[0];
    assert [range_check_ptr + 1] = inputs[0] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 2] = inputs[1];
    assert [range_check_ptr + 3] = inputs[1] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 4] = inputs[2];
    assert [range_check_ptr + 5] = inputs[2] - 256 ** 8 + 2 ** 128;

    // Split inputs[3] into low3 (1 byte) and high3 (7 bytes).
    let low3 = [range_check_ptr + 6];
    let high3 = [range_check_ptr + 7];
    %{ ids.high3, ids.low3 = divmod(memory[ids.inputs + 3], 256) %}
    assert [range_check_ptr + 8] = low3 - 256 + 2 ** 128;
    assert [range_check_ptr + 9] = high3 - 256 ** 7 + 2 ** 128;
    assert inputs[3] = low3 + high3 * 256;

    // Xor state.s0 with 25 bytes from inputs and store in keccak_ptr.input.s0.
    let element = inputs[0] + inputs[1] * 256 ** 8 + inputs[2] * 256 ** 16 + low3 * 256 ** 24;
    assert bitwise_ptr.x = element;
    assert bitwise_ptr.y = state.s0;
    assert keccak_ptr.input.s0 = bitwise_ptr.x_xor_y;
    let bitwise_ptr = bitwise_ptr + BitwiseBuiltin.SIZE;

    // Assert that inputs[4] and inputs[5] consist of 8 bytes each.
    assert [range_check_ptr + 10] = inputs[4];
    assert [range_check_ptr + 11] = inputs[4] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 12] = inputs[5];
    assert [range_check_ptr + 13] = inputs[5] - 256 ** 8 + 2 ** 128;

    // Split inputs[6] into low6 (2 byte) and high6 (6 bytes).
    let low6 = [range_check_ptr + 14];
    let high6 = [range_check_ptr + 15];
    %{ ids.high6, ids.low6 = divmod(memory[ids.inputs + 6], 256 ** 2) %}
    assert [range_check_ptr + 16] = low6 - 256 ** 2 + 2 ** 128;
    assert [range_check_ptr + 17] = high6 - 256 ** 6 + 2 ** 128;
    assert inputs[6] = low6 + high6 * 256 ** 2;

    // Xor state.s1 with the next 25 bytes from inputs and store in keccak_ptr.input.s1.
    let element = high3 + inputs[4] * 256 ** 7 + inputs[5] * 256 ** 15 + low6 * 256 ** 23;
    assert bitwise_ptr.x = element;
    assert bitwise_ptr.y = state.s1;
    assert keccak_ptr.input.s1 = bitwise_ptr.x_xor_y;
    let bitwise_ptr = bitwise_ptr + BitwiseBuiltin.SIZE;

    // Assert that inputs[7] and inputs[8] consist of 8 bytes each.
    assert [range_check_ptr + 18] = inputs[7];
    assert [range_check_ptr + 19] = inputs[7] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 20] = inputs[8];
    assert [range_check_ptr + 21] = inputs[8] - 256 ** 8 + 2 ** 128;

    // Split inputs[9] into low9 (3 byte) and high9 (5 bytes).
    let low9 = [range_check_ptr + 22];
    let high9 = [range_check_ptr + 23];
    %{ ids.high9, ids.low9 = divmod(memory[ids.inputs + 9], 256 ** 3) %}
    assert [range_check_ptr + 24] = low9 - 256 ** 3 + 2 ** 128;
    assert [range_check_ptr + 25] = high9 - 256 ** 5 + 2 ** 128;
    assert inputs[9] = low9 + high9 * 256 ** 3;

    // Xor state.s2 with the next 25 bytes from inputs and store in keccak_ptr.input.s2.
    let element = high6 + inputs[7] * 256 ** 6 + inputs[8] * 256 ** 14 + low9 * 256 ** 22;
    assert bitwise_ptr.x = element;
    assert bitwise_ptr.y = state.s2;
    assert keccak_ptr.input.s2 = bitwise_ptr.x_xor_y;
    let bitwise_ptr = bitwise_ptr + BitwiseBuiltin.SIZE;

    // Assert that inputs[10] and inputs[11] consist of 8 bytes each.
    assert [range_check_ptr + 26] = inputs[10];
    assert [range_check_ptr + 27] = inputs[10] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 28] = inputs[11];
    assert [range_check_ptr + 29] = inputs[11] - 256 ** 8 + 2 ** 128;

    // Split inputs[12] into low12 (4 byte) and high12 (4 bytes).
    let low12 = [range_check_ptr + 30];
    let high12 = [range_check_ptr + 31];
    %{ ids.high12, ids.low12 = divmod(memory[ids.inputs + 12], 256 ** 4) %}
    assert [range_check_ptr + 32] = low12 - 256 ** 4 + 2 ** 128;
    assert [range_check_ptr + 33] = high12 - 256 ** 4 + 2 ** 128;
    assert inputs[12] = low12 + high12 * 256 ** 4;

    // Xor state.s3 with the next 25 bytes from inputs and store in keccak_ptr.input.s3.
    let element = high9 + inputs[10] * 256 ** 5 + inputs[11] * 256 ** 13 + low12 * 256 ** 21;
    assert bitwise_ptr.x = element;
    assert bitwise_ptr.y = state.s3;
    assert keccak_ptr.input.s3 = bitwise_ptr.x_xor_y;
    let bitwise_ptr = bitwise_ptr + BitwiseBuiltin.SIZE;

    // Assert that inputs[13] and inputs[14] consist of 8 bytes each.
    assert [range_check_ptr + 34] = inputs[13];
    assert [range_check_ptr + 35] = inputs[13] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 36] = inputs[14];
    assert [range_check_ptr + 37] = inputs[14] - 256 ** 8 + 2 ** 128;

    // Split inputs[15] into low15 (5 byte) and high15 (3 bytes).
    let low15 = [range_check_ptr + 38];
    let high15 = [range_check_ptr + 39];
    %{ ids.high15, ids.low15 = divmod(memory[ids.inputs + 15], 256 ** 5) %}
    assert [range_check_ptr + 40] = low15 - 256 ** 5 + 2 ** 128;
    assert [range_check_ptr + 41] = high15 - 256 ** 3 + 2 ** 128;
    assert inputs[15] = low15 + high15 * 256 ** 5;

    // Xor state.s4 with the next 25 bytes from inputs and store in keccak_ptr.input.s4.
    let element = high12 + inputs[13] * 256 ** 4 + inputs[14] * 256 ** 12 + low15 * 256 ** 20;
    assert bitwise_ptr.x = element;
    assert bitwise_ptr.y = state.s4;
    assert keccak_ptr.input.s4 = bitwise_ptr.x_xor_y;
    let bitwise_ptr = bitwise_ptr + BitwiseBuiltin.SIZE;

    // Assert that inputs[16] consist of 8 bytes.
    assert [range_check_ptr + 42] = inputs[16];
    assert [range_check_ptr + 43] = inputs[16] - 256 ** 8 + 2 ** 128;

    // Xor state.s5 (25-byte element) with the next 11 bytes from inputs (pad with zeros to
    // complete to 25 bytes) and store in keccak_ptr.input.s5.
    let element = high15 + inputs[16] * 256 ** 3;
    assert bitwise_ptr.x = element;
    assert bitwise_ptr.y = state.s5;
    assert keccak_ptr.input.s5 = bitwise_ptr.x_xor_y;
    let bitwise_ptr = bitwise_ptr + BitwiseBuiltin.SIZE;

    // The remaining 50 bytes are copied without xoring.
    assert keccak_ptr.input.s6 = state.s6;
    assert keccak_ptr.input.s7 = state.s7;

    let range_check_ptr = range_check_ptr + 44;

    return ();
}

// Pads the input bytes to a full 136-byte block and calls _prepare_full_block.
func _prepare_last_block{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, keccak_ptr: KeccakBuiltin*}(
    inputs: felt*, n_bytes: felt, state: KeccakBuiltinState*
) {
    alloc_locals;

    let (padded_inputs) = alloc();
    let dst = padded_inputs;

    // Write n_bytes as n_bytes_left + n_words_to_copy * BYTES_IN_WORD.
    let n_words_to_copy = [range_check_ptr];
    let n_bytes_left = [range_check_ptr + 1];
    %{ ids.n_words_to_copy, ids.n_bytes_left = divmod(ids.n_bytes, ids.BYTES_IN_WORD) %}
    tempvar n_words_to_copy = n_words_to_copy;
    tempvar n_bytes_left = n_bytes_left;
    assert [range_check_ptr + 2] = n_bytes_left - BYTES_IN_WORD + 2 ** 128;
    assert [range_check_ptr + 3] = n_words_to_copy - KECCAK_FULL_RATE_IN_WORDS + 2 ** 128;
    assert n_bytes = n_bytes_left + n_words_to_copy * BYTES_IN_WORD;
    let range_check_ptr = range_check_ptr + 4;
    memcpy(dst=dst, src=inputs, len=n_words_to_copy);
    let dst = dst + n_words_to_copy;

    tempvar padding_len = KECCAK_FULL_RATE_IN_WORDS - n_words_to_copy;
    local input_word;
    if (n_bytes_left == 0) {
        input_word = 0;
    } else {
        assert input_word = inputs[n_words_to_copy];
    }

    let first_one = _pow256(n_bytes_left);
    // The beginning of the padding with the last bytes of the input and the first 1.
    let input_word_with_initial_padding = input_word + first_one;

    if (padding_len == 1) {
        assert dst[0] = 2 ** 63 + input_word_with_initial_padding;
    } else {
        // Padding of more than 1 word.
        assert dst[0] = input_word_with_initial_padding;
        memset(dst=dst + 1, value=0, n=padding_len - 2);
        assert dst[padding_len - 1] = 2 ** 63;
    }

    return _prepare_full_block(inputs=padded_inputs, state=state);
}

// Efficiently returns 256**n.
// Assumes 0 <= n < 8.
func _pow256(n: felt) -> felt {
    let (table) = get_label_location(powers);
    return table[n];

    powers:
    dw 256 ** 0;
    dw 256 ** 1;
    dw 256 ** 2;
    dw 256 ** 3;
    dw 256 ** 4;
    dw 256 ** 5;
    dw 256 ** 6;
    dw 256 ** 7;
}

func _keccak{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, keccak_ptr: KeccakBuiltin*}(
    inputs: felt*, n_bytes: felt, state: KeccakBuiltinState*
) -> (output: KeccakBuiltinState*) {
    if (nondet %{ ids.n_bytes >= ids.KECCAK_FULL_RATE_IN_BYTES %} != 0) {
        _prepare_full_block(inputs=inputs, state=state);
        let state = &(keccak_ptr.output);
        let keccak_ptr = keccak_ptr + KeccakBuiltin.SIZE;

        return _keccak(
            inputs=inputs + KECCAK_FULL_RATE_IN_WORDS,
            n_bytes=n_bytes - KECCAK_FULL_RATE_IN_BYTES,
            state=state,
        );
    }

    _prepare_last_block(inputs=inputs, n_bytes=n_bytes, state=state);
    let state = &(keccak_ptr.output);
    let keccak_ptr = keccak_ptr + KeccakBuiltin.SIZE;
    return (output=state);
}

// Same as keccak but assumes that the input was already padded to 1088-bit blocks.
// Namely, the size of the `inputs` should be `n_blocks * KECCAK_FULL_RATE_IN_WORDS`.
func keccak_padded_input{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, keccak_ptr: KeccakBuiltin*}(
    inputs: felt*, n_blocks: felt
) -> (res: Uint256) {
    tempvar state = new KeccakBuiltinState(s0=0, s1=0, s2=0, s3=0, s4=0, s5=0, s6=0, s7=0);
    let output = _keccak_padded_input(inputs, n_blocks, state);
    let res = _keccak_output_to_uint256(output);
    return res;
}

func _keccak_padded_input{
    range_check_ptr, bitwise_ptr: BitwiseBuiltin*, keccak_ptr: KeccakBuiltin*
}(inputs: felt*, n_blocks: felt, state: KeccakBuiltinState*) -> KeccakBuiltinState* {
    if (n_blocks == 0) {
        return state;
    }

    _prepare_full_block(inputs=inputs, state=state);
    let state = &(keccak_ptr.output);
    let keccak_ptr = keccak_ptr + KeccakBuiltin.SIZE;

    return _keccak_padded_input(
        inputs=&inputs[KECCAK_FULL_RATE_IN_WORDS], n_blocks=n_blocks - 1, state=state
    );
}
