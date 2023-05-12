// These functions serialize input to an array of 64-bit little endian words to be used with
// keccak() or keccak_as_words().
// Note: These functions assume that 'inputs' points to a sequence of elements that are guaranteed
// to be 8 bytes each, otherwise they are not sound.

from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.math import split_felt
from starkware.cairo.common.uint256 import Uint256, uint256_reverse_endian

// Serializes a uint256 number in a keccak compatible way.
// The argument 'bigend' is either 0 or 1, representing the endianness of the given number.
func keccak_add_uint256{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, inputs: felt*}(
    num: Uint256, bigend: felt
) {
    if (bigend != 0) {
        let (num_reversed) = uint256_reverse_endian(num=num);
        tempvar bitwise_ptr = bitwise_ptr;
        tempvar high = num_reversed.high;
        tempvar low = num_reversed.low;
    } else {
        tempvar bitwise_ptr = bitwise_ptr;
        tempvar high = num.high;
        tempvar low = num.low;
    }

    %{
        segments.write_arg(ids.inputs, [ids.low % 2 ** 64, ids.low // 2 ** 64])
        segments.write_arg(ids.inputs + 2, [ids.high % 2 ** 64, ids.high // 2 ** 64])
    %}

    assert inputs[1] * 2 ** 64 + inputs[0] = low;
    assert inputs[3] * 2 ** 64 + inputs[2] = high;

    let inputs = inputs + 4;
    return ();
}

// Serializes multiple uint256 numbers in a keccak compatible way.
// The argument 'bigend' is either 0 or 1, representing the endianness of the given numbers.
// Note: This function does not serialize the number of elements. If desired, this is the caller's
// responsibility.
func keccak_add_uint256s{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, inputs: felt*}(
    n_elements: felt, elements: Uint256*, bigend: felt
) {
    if (n_elements == 0) {
        return ();
    }

    keccak_add_uint256(num=elements[0], bigend=bigend);
    return keccak_add_uint256s(n_elements=n_elements - 1, elements=&elements[1], bigend=bigend);
}

// Serializes a field element in a keccak compatible way.
// The argument 'bigend' is either 0 or 1, representing the endianness of the given element.
func keccak_add_felt{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, inputs: felt*}(
    num: felt, bigend: felt
) {
    let (high, low) = split_felt(value=num);
    keccak_add_uint256(num=Uint256(low=low, high=high), bigend=bigend);

    return ();
}

// Serializes multiple field elements in a keccak compatible way.
// The argument 'bigend' is either 0 or 1, representing the endianness of the given elements.
// Note: This function does not serialize the number of elements. If desired, this is the caller's
// responsibility.
func keccak_add_felts{range_check_ptr, bitwise_ptr: BitwiseBuiltin*, inputs: felt*}(
    n_elements: felt, elements: felt*, bigend: felt
) {
    if (n_elements == 0) {
        return ();
    }

    keccak_add_felt(num=elements[0], bigend=bigend);
    return keccak_add_felts(n_elements=n_elements - 1, elements=&elements[1], bigend=bigend);
}
