from starkware.cairo.common.bitwise import bitwise_and
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.registers import get_label_location

const FIELD_GENERATOR = 3;

// Bit reverses a uint64 number. Assumes the input is known to be in [0, 2**64).
func bit_reverse_u64{bitwise_ptr: BitwiseBuiltin*}(num: felt) -> (res: felt) {
    alloc_locals;

    // Swap 1 bit chunks, and shift left by 1.
    let (masked) = bitwise_and(num, 0x5555555555555555);
    let num = masked * (2 ** 2 - 1) + num;
    // Swap 2 bit chunks, and shift left by 2.
    let (masked) = bitwise_and(num, 0x6666666666666666);
    let num = masked * (2 ** 4 - 1) + num;
    // Swap 4 bit chunks, and shift left by 4.
    let (masked) = bitwise_and(num, 0x7878787878787878);
    let num = masked * (2 ** 8 - 1) + num;
    // Swap 8 bit chunks, and shift left by 8.
    let (masked) = bitwise_and(num, 0x7f807f807f807f80);
    let num = masked * (2 ** 16 - 1) + num;
    // Swap 16 bit chunks, and shift left by 16.
    let (masked) = bitwise_and(num, 0x7fff80007fff8000);
    let num = masked * (2 ** 32 - 1) + num;
    // Swap 16 bit chunks, and shift left by 32.
    let (masked) = bitwise_and(num, 0x7fffffff80000000);
    let num = masked * (2 ** 64 - 1) + num;

    // Combine in reverse.
    return (res=num / 2 ** 63);
}
