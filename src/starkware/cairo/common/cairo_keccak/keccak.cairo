from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.bitwise import bitwise_and, bitwise_or, bitwise_xor
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.cairo_keccak.packed_keccak import BLOCK_SIZE, packed_keccak_func
from starkware.cairo.common.math import (
    assert_lt,
    assert_nn,
    assert_nn_le,
    assert_not_zero,
    split_felt,
    unsigned_div_rem,
)
from starkware.cairo.common.memcpy import memcpy
from starkware.cairo.common.memset import memset
from starkware.cairo.common.pow import pow
from starkware.cairo.common.uint256 import Uint256, uint256_reverse_endian

const KECCAK_STATE_SIZE_FELTS = 25
const KECCAK_FULL_RATE_IN_BYTES = 136
const KECCAK_FULL_RATE_IN_WORDS = 17
const KECCAK_CAPACITY_IN_WORDS = 8
const BYTES_IN_WORD = 8

# Computes the keccak hash of multiple uint256 numbers.
func keccak_uint256s{range_check_ptr, bitwise_ptr : BitwiseBuiltin*, keccak_ptr : felt*}(
    n_elements : felt, elements : Uint256*
) -> (res : Uint256):
    alloc_locals

    let (inputs) = alloc()
    let inputs_start = inputs

    keccak_add_uint256s{inputs=inputs}(n_elements=n_elements, elements=elements, bigend=0)

    return keccak(inputs=inputs_start, n_bytes=n_elements * 32)
end

# Computes the keccak hash of multiple uint256 numbers (big-endian).
# Note that both the output and the input are in big endian representation.
func keccak_uint256s_bigend{range_check_ptr, bitwise_ptr : BitwiseBuiltin*, keccak_ptr : felt*}(
    n_elements : felt, elements : Uint256*
) -> (res : Uint256):
    alloc_locals

    let (inputs) = alloc()
    let inputs_start = inputs

    keccak_add_uint256s{inputs=inputs}(n_elements=n_elements, elements=elements, bigend=1)

    return keccak_bigend(inputs=inputs_start, n_bytes=n_elements * 32)
end

# Computes the keccak hash of multiple field elements.
func keccak_felts{range_check_ptr, bitwise_ptr : BitwiseBuiltin*, keccak_ptr : felt*}(
    n_elements : felt, elements : felt*
) -> (res : Uint256):
    alloc_locals

    let (inputs) = alloc()
    let inputs_start = inputs

    keccak_add_felts{inputs=inputs}(n_elements=n_elements, elements=elements, bigend=0)

    return keccak(inputs=inputs_start, n_bytes=n_elements * 32)
end

# Computes the keccak hash of multiple field elements (big-endian).
# Note that both the output and the input are in big endian representation.
func keccak_felts_bigend{range_check_ptr, bitwise_ptr : BitwiseBuiltin*, keccak_ptr : felt*}(
    n_elements : felt, elements : felt*
) -> (res : Uint256):
    alloc_locals

    let (inputs) = alloc()
    let inputs_start = inputs

    keccak_add_felts{inputs=inputs}(n_elements=n_elements, elements=elements, bigend=1)

    return keccak_bigend(inputs=inputs_start, n_bytes=n_elements * 32)
end

# Helper functions.
# These functions serialize input to an array of 64-bit little endian words
# to be used with keccak() or keccak_as_words().
# Note: You must call finalize_keccak() at the end of the program, where the range of the input
# is checked. Otherwise, these functions are not sound.

# Serializes a uint256 number in a keccak compatible way.
# The argument 'bigend' is either 0 or 1, representing the endianness of the given number.
func keccak_add_uint256{range_check_ptr, bitwise_ptr : BitwiseBuiltin*, inputs : felt*}(
    num : Uint256, bigend : felt
):
    if bigend != 0:
        let (num_reversed) = uint256_reverse_endian(num=num)
        tempvar bitwise_ptr = bitwise_ptr
        tempvar high = num_reversed.high
        tempvar low = num_reversed.low
    else:
        tempvar bitwise_ptr = bitwise_ptr
        tempvar high = num.high
        tempvar low = num.low
    end

    %{
        segments.write_arg(ids.inputs, [ids.low % 2 ** 64, ids.low // 2 ** 64])
        segments.write_arg(ids.inputs + 2, [ids.high % 2 ** 64, ids.high // 2 ** 64])
    %}

    assert inputs[1] * 2 ** 64 + inputs[0] = low
    assert inputs[3] * 2 ** 64 + inputs[2] = high

    let inputs = inputs + 4
    return ()
end

# Serializes multiple uint256 numbers in a keccak compatible way.
# The argument 'bigend' is either 0 or 1, representing the endianness of the given numbers.
# Note: This function does not serialize the number of elements. If desired, this is the caller's
# responsibility.
func keccak_add_uint256s{range_check_ptr, bitwise_ptr : BitwiseBuiltin*, inputs : felt*}(
    n_elements : felt, elements : Uint256*, bigend : felt
):
    if n_elements == 0:
        return ()
    end

    keccak_add_uint256(num=elements[0], bigend=bigend)
    return keccak_add_uint256s(n_elements=n_elements - 1, elements=&elements[1], bigend=bigend)
end

# Serializes a field element in a keccak compatible way.
# The argument 'bigend' is either 0 or 1, representing the endianness of the given element.
func keccak_add_felt{range_check_ptr, bitwise_ptr : BitwiseBuiltin*, inputs : felt*}(
    num : felt, bigend : felt
):
    let (high, low) = split_felt(value=num)
    keccak_add_uint256(num=Uint256(low=low, high=high), bigend=bigend)

    return ()
end

# Serializes multiple field elements in a keccak compatible way.
# The argument 'bigend' is either 0 or 1, representing the endianness of the given elements.
# Note: This function does not serialize the number of elements. If desired, this is the caller's
# responsibility.
func keccak_add_felts{range_check_ptr, bitwise_ptr : BitwiseBuiltin*, inputs : felt*}(
    n_elements : felt, elements : felt*, bigend : felt
):
    if n_elements == 0:
        return ()
    end

    keccak_add_felt(num=elements[0], bigend=bigend)
    return keccak_add_felts(n_elements=n_elements - 1, elements=&elements[1], bigend=bigend)
end

# Computes the keccak of 'input'.
# To use this function, split the input into words of 64 bits (little endian).
# For example, to compute keccak('Hello world!'), use:
#   inputs = [8031924123371070792, 560229490]
# where:
#   8031924123371070792 == int.from_bytes(b'Hello wo', 'little')
#   560229490 == int.from_bytes(b'rld!', 'little')
#
# Returns the hash as a Uint256.
#
# Note: You must call finalize_keccak() at the end of the program. Otherwise, this function
# is not sound and a malicious prover may return a wrong result.
func keccak{range_check_ptr, bitwise_ptr : BitwiseBuiltin*, keccak_ptr : felt*}(
    inputs : felt*, n_bytes : felt
) -> (res : Uint256):
    let (output) = keccak_as_words(inputs=inputs, n_bytes=n_bytes)

    let res_low = output[1] * 2 ** 64 + output[0]
    let res_high = output[3] * 2 ** 64 + output[2]

    return (res=Uint256(low=res_low, high=res_high))
end

# Same as keccak, but outputs the hash in big endian representation.
# Note that the input is still treated as little endian.
func keccak_bigend{range_check_ptr, bitwise_ptr : BitwiseBuiltin*, keccak_ptr : felt*}(
    inputs : felt*, n_bytes : felt
) -> (res : Uint256):
    let (hash) = keccak(inputs=inputs, n_bytes=n_bytes)
    let (res) = uint256_reverse_endian(num=hash)
    return (res=res)
end

# Same as keccak, but outputs a pointer to 4 64-bit little endian words instead.
func keccak_as_words{range_check_ptr, bitwise_ptr : BitwiseBuiltin*, keccak_ptr : felt*}(
    inputs : felt*, n_bytes : felt
) -> (output : felt*):
    alloc_locals

    let (local state) = alloc()
    memset(dst=state, value=0, n=KECCAK_STATE_SIZE_FELTS)

    return _keccak(inputs=inputs, n_bytes=n_bytes, state=state)
end

# Prepares a block for the block permutation: adds padding (of the form 100...001, see the
# _padding function) and capacity (8 64-bits words of zeros) to the input, xors the result
# with the previous block permutation's output, and writes it to keccak_ptr.
#
# This function is called for every block that is sent to the _block_permutation
# function. Each time it is called with a chunk of the input of at
# most 17 64-bit words. That is, with n_bytes <= 136. When it is called with exactly 136
# bytes, no padding is added. Only the last block is padded.
#
# Arguments:
#   inputs - chunk of the input, in little endian.
#   n_bytes - the length of inputs in bytes. Must be in the range [0, 136].
#   state - the output of the previous block permutation that contains 25 64-bits words.
func _prepare_block{range_check_ptr, bitwise_ptr : BitwiseBuiltin*, keccak_ptr : felt*}(
    inputs : felt*, n_bytes : felt, state : felt*
):
    alloc_locals

    let inputs_start = inputs
    _copy_inputs{inputs=inputs, n_bytes=n_bytes, state=state}()
    # n_words_written is the number of words written to keccak_ptr.
    let n_words_written = inputs - inputs_start

    tempvar padding_len = (KECCAK_FULL_RATE_IN_WORDS - n_words_written)
    local input_word
    if n_bytes == 0:
        input_word = 0
    else:
        input_word = inputs[0]
    end

    _padding(input_word=input_word, n_bytes=n_bytes, state=state, padding_len=padding_len)
    let state = state + padding_len

    # Since the capacity part consists of zeros, we simply copy the state.
    memcpy(dst=keccak_ptr, src=state, len=KECCAK_CAPACITY_IN_WORDS)
    let keccak_ptr = keccak_ptr + KECCAK_CAPACITY_IN_WORDS

    return ()
end

# Xors full words from the input with the corresponding words from the output of the
# previous block permutation, and writes the restult to keccak_ptr.
func _copy_inputs{
    range_check_ptr,
    bitwise_ptr : BitwiseBuiltin*,
    keccak_ptr : felt*,
    inputs : felt*,
    n_bytes : felt,
    state : felt*,
}():
    if nondet %{ ids.n_bytes < ids.BYTES_IN_WORD %} != 0:
        assert_nn_le(n_bytes, BYTES_IN_WORD - 1)
        return ()
    end

    let (next_word) = bitwise_xor(inputs[0], state[0])
    assert keccak_ptr[0] = next_word

    let inputs = &inputs[1]
    let state = &state[1]
    let keccak_ptr = &keccak_ptr[1]
    let n_bytes = n_bytes - BYTES_IN_WORD

    return _copy_inputs()
end

# Adds padding of the form 100...001 to the last bytes of the input, to a total of
# padding_len words, xors the result with the output of the last block permutation,
# from the corresponding offset, and writes it to keccak_ptr.
#
# Arguments:
#   input_word - the last word of the input to keccak (given in little endian)
#       if it has less than 8 bytes, otherwise 0.
#   n_bytes - the number of bytes in input_word. Must be in the range [0, 8).
#   state - the output of the last block permutation, from the word that corresponds
#       to the input_word. (i.e., if input_word is the i-th word in the current block,
#       then state points to the i-th word of the last block permutation's output).
#   padding_len - the length of the required padding (in words). Must be in the range [0, 17].
func _padding{range_check_ptr, bitwise_ptr : BitwiseBuiltin*, keccak_ptr : felt*}(
    input_word : felt, n_bytes : felt, state : felt*, padding_len : felt
):
    if padding_len == 0:
        return ()
    end

    let (first_one) = pow(256, n_bytes)
    # The beginning of the padding with the last bytes of the input and the first 1.
    let input_word_with_initial_padding = input_word + first_one

    if padding_len == 1:
        let both_ones = 2 ** 63 + input_word_with_initial_padding
        let (word) = bitwise_xor(both_ones, state[0])

        assert keccak_ptr[0] = word
        let keccak_ptr = &keccak_ptr[1]

        return ()
    end

    return _long_padding(
        input_word_with_initial_padding=input_word_with_initial_padding,
        state=state,
        padding_len=padding_len,
    )
end

# Padding of more than 1 word.
func _long_padding{range_check_ptr, bitwise_ptr : BitwiseBuiltin*, keccak_ptr : felt*}(
    input_word_with_initial_padding : felt, state : felt*, padding_len : felt
):
    alloc_locals

    # First word.
    let (first_one) = bitwise_xor(input_word_with_initial_padding, state[0])
    assert keccak_ptr[0] = first_one
    let keccak_ptr = &keccak_ptr[1]
    let state = state + 1

    # The padding of the inner words is zero, so we should simply copy them.
    memcpy(dst=keccak_ptr, src=state, len=padding_len - 2)
    let keccak_ptr = keccak_ptr + padding_len - 2
    let state = state + padding_len - 2

    # Last word.
    let (second_one) = bitwise_xor(2 ** 63, state[0])
    assert keccak_ptr[0] = second_one
    let keccak_ptr = &keccak_ptr[1]

    return ()
end

func _block_permutation{keccak_ptr : felt*}():
    %{
        from starkware.cairo.common.cairo_keccak.keccak_utils import keccak_func
        _keccak_state_size_felts = int(ids.KECCAK_STATE_SIZE_FELTS)
        assert 0 <= _keccak_state_size_felts < 100

        output_values = keccak_func(memory.get_range(
            ids.keccak_ptr - _keccak_state_size_felts, _keccak_state_size_felts))
        segments.write_arg(ids.keccak_ptr, output_values)
    %}
    let keccak_ptr = keccak_ptr + KECCAK_STATE_SIZE_FELTS

    return ()
end

func _keccak{range_check_ptr, bitwise_ptr : BitwiseBuiltin*, keccak_ptr : felt*}(
    inputs : felt*, n_bytes : felt, state : felt*
) -> (output : felt*):
    if nondet %{ ids.n_bytes >= ids.KECCAK_FULL_RATE_IN_BYTES %} != 0:
        _prepare_block(inputs=inputs, n_bytes=KECCAK_FULL_RATE_IN_BYTES, state=state)
        _block_permutation()

        return _keccak(
            inputs=inputs + KECCAK_FULL_RATE_IN_WORDS,
            n_bytes=n_bytes - KECCAK_FULL_RATE_IN_BYTES,
            state=keccak_ptr - KECCAK_STATE_SIZE_FELTS,
        )
    end

    assert_nn_le(n_bytes, KECCAK_FULL_RATE_IN_BYTES - 1)

    _prepare_block(inputs=inputs, n_bytes=n_bytes, state=state)
    _block_permutation()

    return (keccak_ptr - KECCAK_STATE_SIZE_FELTS)
end

# Verifies that the results of keccak() are valid.
func finalize_keccak{range_check_ptr, bitwise_ptr : BitwiseBuiltin*}(
    keccak_ptr_start : felt*, keccak_ptr_end : felt*
):
    alloc_locals

    tempvar n = (keccak_ptr_end - keccak_ptr_start) / (2 * KECCAK_STATE_SIZE_FELTS)
    if n == 0:
        return ()
    end

    %{
        # Add dummy pairs of input and output.
        _keccak_state_size_felts = int(ids.KECCAK_STATE_SIZE_FELTS)
        _block_size = int(ids.BLOCK_SIZE)
        assert 0 <= _keccak_state_size_felts < 100
        assert 0 <= _block_size < 10
        inp = [0] * _keccak_state_size_felts
        padding = (inp + keccak_func(inp)) * _block_size
        segments.write_arg(ids.keccak_ptr_end, padding)
    %}

    # Compute the amount of blocks (rounded up).
    let (local q, r) = unsigned_div_rem(n + BLOCK_SIZE - 1, BLOCK_SIZE)
    _finalize_keccak_inner(keccak_ptr_start, n=q)
    return ()
end

# Handles n blocks of BLOCK_SIZE keccak instances.
func _finalize_keccak_inner{range_check_ptr, bitwise_ptr : BitwiseBuiltin*}(
    keccak_ptr : felt*, n : felt
):
    if n == 0:
        return ()
    end

    ap += SIZEOF_LOCALS

    local MAX_VALUE = 2 ** 64 - 1

    let keccak_ptr_start = keccak_ptr

    let (local inputs_start : felt*) = alloc()

    # Handle inputs.

    tempvar inputs = inputs_start
    tempvar keccak_ptr = keccak_ptr
    tempvar range_check_ptr = range_check_ptr
    tempvar m = 25

    input_loop:
    tempvar x0 = keccak_ptr[0]
    assert [range_check_ptr] = x0
    assert [range_check_ptr + 1] = MAX_VALUE - x0
    tempvar x1 = keccak_ptr[50]
    assert [range_check_ptr + 2] = x1
    assert [range_check_ptr + 3] = MAX_VALUE - x1
    tempvar x2 = keccak_ptr[100]
    assert [range_check_ptr + 4] = x2
    assert [range_check_ptr + 5] = MAX_VALUE - x2
    assert inputs[0] = x0 + 2 ** 64 * x1 + 2 ** 128 * x2

    tempvar inputs = inputs + 1
    tempvar keccak_ptr = keccak_ptr + 1
    tempvar range_check_ptr = range_check_ptr + 6
    tempvar m = m - 1
    jmp input_loop if m != 0

    # Run keccak on the 3 instances.

    let (outputs) = packed_keccak_func(inputs_start)
    local bitwise_ptr : BitwiseBuiltin* = bitwise_ptr

    # Handle outputs.

    tempvar outputs = outputs
    tempvar keccak_ptr = keccak_ptr
    tempvar range_check_ptr = range_check_ptr
    tempvar m = 25

    output_loop:
    tempvar x0 = keccak_ptr[0]
    assert [range_check_ptr] = x0
    assert [range_check_ptr + 1] = MAX_VALUE - x0
    tempvar x1 = keccak_ptr[50]
    assert [range_check_ptr + 2] = x1
    assert [range_check_ptr + 3] = MAX_VALUE - x1
    tempvar x2 = keccak_ptr[100]
    assert [range_check_ptr + 4] = x2
    assert [range_check_ptr + 5] = MAX_VALUE - x2
    assert outputs[0] = x0 + 2 ** 64 * x1 + 2 ** 128 * x2

    tempvar outputs = outputs + 1
    tempvar keccak_ptr = keccak_ptr + 1
    tempvar range_check_ptr = range_check_ptr + 6
    tempvar m = m - 1
    jmp output_loop if m != 0

    return _finalize_keccak_inner(keccak_ptr=keccak_ptr_start + 150, n=n - 1)
end
