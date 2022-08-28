from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.registers import get_fp_and_pc

const ALL_ONES = 2 ** 251 - 1;
const BLOCK_SIZE = 3;
const SHIFTS = 1 + 2 ** 64 + 2 ** 128;

func keccak_round{bitwise_ptr: BitwiseBuiltin*}(values: felt*, rc: felt) -> (values_b: felt*) {
    ap += SIZEOF_LOCALS;

    // ***************************************************************************************.
    // Compute: c[x] = a[0][x] ^ a[1][x] ^ a[2][x] ^ a[3][x] ^ a[4][x].                       .
    // ***************************************************************************************.

    let values_start = values;

    assert bitwise_ptr[0].x = values[0];
    assert bitwise_ptr[0].y = values[5];
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].y = values[10];
    assert bitwise_ptr[2].x = bitwise_ptr[1].x_xor_y;
    assert bitwise_ptr[2].y = values[15];
    assert bitwise_ptr[3].x = bitwise_ptr[2].x_xor_y;
    assert bitwise_ptr[3].y = values[20];
    tempvar c0 = bitwise_ptr[3].x_xor_y;
    let values = values + 1;
    let bitwise_ptr = bitwise_ptr + 4 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[0];
    assert bitwise_ptr[0].y = values[5];
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].y = values[10];
    assert bitwise_ptr[2].x = bitwise_ptr[1].x_xor_y;
    assert bitwise_ptr[2].y = values[15];
    assert bitwise_ptr[3].x = bitwise_ptr[2].x_xor_y;
    assert bitwise_ptr[3].y = values[20];
    tempvar c1 = bitwise_ptr[3].x_xor_y;
    let values = values + 1;
    let bitwise_ptr = bitwise_ptr + 4 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[0];
    assert bitwise_ptr[0].y = values[5];
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].y = values[10];
    assert bitwise_ptr[2].x = bitwise_ptr[1].x_xor_y;
    assert bitwise_ptr[2].y = values[15];
    assert bitwise_ptr[3].x = bitwise_ptr[2].x_xor_y;
    assert bitwise_ptr[3].y = values[20];
    tempvar c2 = bitwise_ptr[3].x_xor_y;
    let values = values + 1;
    let bitwise_ptr = bitwise_ptr + 4 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[0];
    assert bitwise_ptr[0].y = values[5];
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].y = values[10];
    assert bitwise_ptr[2].x = bitwise_ptr[1].x_xor_y;
    assert bitwise_ptr[2].y = values[15];
    assert bitwise_ptr[3].x = bitwise_ptr[2].x_xor_y;
    assert bitwise_ptr[3].y = values[20];
    tempvar c3 = bitwise_ptr[3].x_xor_y;
    let values = values + 1;
    let bitwise_ptr = bitwise_ptr + 4 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[0];
    assert bitwise_ptr[0].y = values[5];
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].y = values[10];
    assert bitwise_ptr[2].x = bitwise_ptr[1].x_xor_y;
    assert bitwise_ptr[2].y = values[15];
    assert bitwise_ptr[3].x = bitwise_ptr[2].x_xor_y;
    assert bitwise_ptr[3].y = values[20];
    tempvar c4 = bitwise_ptr[3].x_xor_y;
    let values = values + 1;
    let bitwise_ptr = bitwise_ptr + 4 * BitwiseBuiltin.SIZE;

    // ***************************************************************************************.
    // Compute: d[x] = c[(x - 1) % 5] ^ rot_left(c[(x + 1) % 5], 1).                          .
    // ***************************************************************************************.

    // Saving constants as local variables is more efficient in some instructions.
    local mask = 0x800000000000000080000000000000008000000000000000;

    let x = c1;
    let y = c4;
    assert bitwise_ptr[0].x = x;
    assert bitwise_ptr[0].y = mask;
    tempvar x0 = bitwise_ptr[0].x_and_y;
    let rotx = 2 * x + (1 / 2 ** 63 - 2) * x0;
    assert bitwise_ptr[1].x = rotx;
    assert bitwise_ptr[1].y = y;
    tempvar d0 = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    let x = c2;
    let y = c0;
    assert bitwise_ptr[0].x = x;
    assert bitwise_ptr[0].y = mask;
    tempvar x0 = bitwise_ptr[0].x_and_y;
    let rotx = 2 * x + (1 / 2 ** 63 - 2) * x0;
    assert bitwise_ptr[1].x = rotx;
    assert bitwise_ptr[1].y = y;
    tempvar d1 = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    let x = c3;
    let y = c1;
    assert bitwise_ptr[0].x = x;
    assert bitwise_ptr[0].y = mask;
    tempvar x0 = bitwise_ptr[0].x_and_y;
    let rotx = 2 * x + (1 / 2 ** 63 - 2) * x0;
    assert bitwise_ptr[1].x = rotx;
    assert bitwise_ptr[1].y = y;
    tempvar d2 = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    let x = c4;
    let y = c2;
    assert bitwise_ptr[0].x = x;
    assert bitwise_ptr[0].y = mask;
    tempvar x0 = bitwise_ptr[0].x_and_y;
    let rotx = 2 * x + (1 / 2 ** 63 - 2) * x0;
    assert bitwise_ptr[1].x = rotx;
    assert bitwise_ptr[1].y = y;
    tempvar d3 = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    let x = c0;
    let y = c3;
    assert bitwise_ptr[0].x = x;
    assert bitwise_ptr[0].y = mask;
    tempvar x0 = bitwise_ptr[0].x_and_y;
    let rotx = 2 * x + (1 / 2 ** 63 - 2) * x0;
    assert bitwise_ptr[1].x = rotx;
    assert bitwise_ptr[1].y = y;
    tempvar d4 = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    // ***************************************************************************************.
    // Compute: b[(2 * x + 3 * y) % 5][y] = rot_left([a[y][x] ^ d[x], OFFSETS[x][y])          .
    // ***************************************************************************************.

    let values = values_start;

    assert bitwise_ptr[0].x = values[0];
    assert bitwise_ptr[0].y = d0;
    tempvar b0 = bitwise_ptr[0].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 1 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[5];
    assert bitwise_ptr[0].y = d0;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xfffffffff0000000fffffffff0000000fffffffff0000000;
    tempvar b16 = 2 ** 36 * x + (1 / 2 ** 28 - 2 ** 36) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[10];
    assert bitwise_ptr[0].y = d0;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xe000000000000000e000000000000000e000000000000000;
    tempvar b7 = 2 ** 3 * x + (1 / 2 ** 61 - 2 ** 3) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[15];
    assert bitwise_ptr[0].y = d0;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xffffffffff800000ffffffffff800000ffffffffff800000;
    tempvar b23 = 2 ** 41 * x + (1 / 2 ** 23 - 2 ** 41) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[20];
    assert bitwise_ptr[0].y = d0;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xffffc00000000000ffffc00000000000ffffc00000000000;
    tempvar b14 = 2 ** 18 * x + (1 / 2 ** 46 - 2 ** 18) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[1];
    assert bitwise_ptr[0].y = d1;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0x800000000000000080000000000000008000000000000000;
    tempvar b10 = 2 ** 1 * x + (1 / 2 ** 63 - 2 ** 1) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[6];
    assert bitwise_ptr[0].y = d1;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xfffffffffff00000fffffffffff00000fffffffffff00000;
    tempvar b1 = 2 ** 44 * x + (1 / 2 ** 20 - 2 ** 44) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[11];
    assert bitwise_ptr[0].y = d1;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xffc0000000000000ffc0000000000000ffc0000000000000;
    tempvar b17 = 2 ** 10 * x + (1 / 2 ** 54 - 2 ** 10) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[16];
    assert bitwise_ptr[0].y = d1;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xfffffffffff80000fffffffffff80000fffffffffff80000;
    tempvar b8 = 2 ** 45 * x + (1 / 2 ** 19 - 2 ** 45) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[21];
    assert bitwise_ptr[0].y = d1;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xc000000000000000c000000000000000c000000000000000;
    tempvar b24 = 2 ** 2 * x + (1 / 2 ** 62 - 2 ** 2) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[2];
    assert bitwise_ptr[0].y = d2;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xfffffffffffffffcfffffffffffffffcfffffffffffffffc;
    tempvar b20 = 2 ** 62 * x + (1 / 2 ** 2 - 2 ** 62) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[7];
    assert bitwise_ptr[0].y = d2;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xfc00000000000000fc00000000000000fc00000000000000;
    tempvar b11 = 2 ** 6 * x + (1 / 2 ** 58 - 2 ** 6) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[12];
    assert bitwise_ptr[0].y = d2;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xffffffffffe00000ffffffffffe00000ffffffffffe00000;
    tempvar b2 = 2 ** 43 * x + (1 / 2 ** 21 - 2 ** 43) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[17];
    assert bitwise_ptr[0].y = d2;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xfffe000000000000fffe000000000000fffe000000000000;
    tempvar b18 = 2 ** 15 * x + (1 / 2 ** 49 - 2 ** 15) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[22];
    assert bitwise_ptr[0].y = d2;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xfffffffffffffff8fffffffffffffff8fffffffffffffff8;
    tempvar b9 = 2 ** 61 * x + (1 / 2 ** 3 - 2 ** 61) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[3];
    assert bitwise_ptr[0].y = d3;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xfffffff000000000fffffff000000000fffffff000000000;
    tempvar b5 = 2 ** 28 * x + (1 / 2 ** 36 - 2 ** 28) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[8];
    assert bitwise_ptr[0].y = d3;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xfffffffffffffe00fffffffffffffe00fffffffffffffe00;
    tempvar b21 = 2 ** 55 * x + (1 / 2 ** 9 - 2 ** 55) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[13];
    assert bitwise_ptr[0].y = d3;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xffffff8000000000ffffff8000000000ffffff8000000000;
    tempvar b12 = 2 ** 25 * x + (1 / 2 ** 39 - 2 ** 25) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[18];
    assert bitwise_ptr[0].y = d3;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xfffff80000000000fffff80000000000fffff80000000000;
    tempvar b3 = 2 ** 21 * x + (1 / 2 ** 43 - 2 ** 21) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[23];
    assert bitwise_ptr[0].y = d3;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xffffffffffffff00ffffffffffffff00ffffffffffffff00;
    tempvar b19 = 2 ** 56 * x + (1 / 2 ** 8 - 2 ** 56) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[4];
    assert bitwise_ptr[0].y = d4;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xffffffe000000000ffffffe000000000ffffffe000000000;
    tempvar b15 = 2 ** 27 * x + (1 / 2 ** 37 - 2 ** 27) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[9];
    assert bitwise_ptr[0].y = d4;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xfffff00000000000fffff00000000000fffff00000000000;
    tempvar b6 = 2 ** 20 * x + (1 / 2 ** 44 - 2 ** 20) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[14];
    assert bitwise_ptr[0].y = d4;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xfffffffffe000000fffffffffe000000fffffffffe000000;
    tempvar b22 = 2 ** 39 * x + (1 / 2 ** 25 - 2 ** 39) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[19];
    assert bitwise_ptr[0].y = d4;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xff00000000000000ff00000000000000ff00000000000000;
    tempvar b13 = 2 ** 8 * x + (1 / 2 ** 56 - 2 ** 8) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = values[24];
    assert bitwise_ptr[0].y = d4;
    tempvar x = bitwise_ptr[0].x_xor_y;
    assert bitwise_ptr[1].x = x;
    assert bitwise_ptr[1].y = 0xfffc000000000000fffc000000000000fffc000000000000;
    tempvar b4 = 2 ** 14 * x + (1 / 2 ** 50 - 2 ** 14) * bitwise_ptr[1].x_and_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    // ***************************************************************************************.
    // Compute: a[y][x] = [[a[y][x] ^ ((~a[y][(x + 1) % 5]) & a[y][(x + 2) % 5])              .
    // ***************************************************************************************.

    let (local output: felt*) = alloc();

    assert bitwise_ptr[0].x = ALL_ONES - b1;
    assert bitwise_ptr[0].y = b2;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b0;
    assert bitwise_ptr[2].x = bitwise_ptr[1].x_xor_y;
    assert bitwise_ptr[2].y = rc;
    assert output[0] = bitwise_ptr[2].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 3 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b6;
    assert bitwise_ptr[0].y = b7;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b5;
    assert output[5] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b11;
    assert bitwise_ptr[0].y = b12;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b10;
    assert output[10] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b16;
    assert bitwise_ptr[0].y = b17;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b15;
    assert output[15] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b21;
    assert bitwise_ptr[0].y = b22;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b20;
    assert output[20] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b2;
    assert bitwise_ptr[0].y = b3;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b1;
    assert output[1] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b7;
    assert bitwise_ptr[0].y = b8;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b6;
    assert output[6] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b12;
    assert bitwise_ptr[0].y = b13;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b11;
    assert output[11] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b17;
    assert bitwise_ptr[0].y = b18;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b16;
    assert output[16] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b22;
    assert bitwise_ptr[0].y = b23;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b21;
    assert output[21] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b3;
    assert bitwise_ptr[0].y = b4;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b2;
    assert output[2] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b8;
    assert bitwise_ptr[0].y = b9;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b7;
    assert output[7] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b13;
    assert bitwise_ptr[0].y = b14;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b12;
    assert output[12] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b18;
    assert bitwise_ptr[0].y = b19;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b17;
    assert output[17] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b23;
    assert bitwise_ptr[0].y = b24;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b22;
    assert output[22] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b4;
    assert bitwise_ptr[0].y = b0;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b3;
    assert output[3] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b9;
    assert bitwise_ptr[0].y = b5;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b8;
    assert output[8] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b14;
    assert bitwise_ptr[0].y = b10;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b13;
    assert output[13] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b19;
    assert bitwise_ptr[0].y = b15;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b18;
    assert output[18] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b24;
    assert bitwise_ptr[0].y = b20;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b23;
    assert output[23] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b0;
    assert bitwise_ptr[0].y = b1;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b4;
    assert output[4] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b5;
    assert bitwise_ptr[0].y = b6;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b9;
    assert output[9] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b10;
    assert bitwise_ptr[0].y = b11;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b14;
    assert output[14] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b15;
    assert bitwise_ptr[0].y = b16;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b19;
    assert output[19] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    assert bitwise_ptr[0].x = ALL_ONES - b20;
    assert bitwise_ptr[0].y = b21;
    assert bitwise_ptr[1].x = bitwise_ptr[0].x_and_y;
    assert bitwise_ptr[1].y = b24;
    assert output[24] = bitwise_ptr[1].x_xor_y;
    let bitwise_ptr = bitwise_ptr + 2 * BitwiseBuiltin.SIZE;

    return (values_b=output);
}

func packed_keccak_func{bitwise_ptr: BitwiseBuiltin*}(values: felt*) -> (values: felt*) {
    let (values) = keccak_round(values, 0x0000000000000001 * SHIFTS);
    let (values) = keccak_round(values, 0x0000000000008082 * SHIFTS);
    let (values) = keccak_round(values, 0x800000000000808A * SHIFTS);
    let (values) = keccak_round(values, 0x8000000080008000 * SHIFTS);
    let (values) = keccak_round(values, 0x000000000000808B * SHIFTS);
    let (values) = keccak_round(values, 0x0000000080000001 * SHIFTS);
    let (values) = keccak_round(values, 0x8000000080008081 * SHIFTS);
    let (values) = keccak_round(values, 0x8000000000008009 * SHIFTS);
    let (values) = keccak_round(values, 0x000000000000008A * SHIFTS);
    let (values) = keccak_round(values, 0x0000000000000088 * SHIFTS);
    let (values) = keccak_round(values, 0x0000000080008009 * SHIFTS);
    let (values) = keccak_round(values, 0x000000008000000A * SHIFTS);
    let (values) = keccak_round(values, 0x000000008000808B * SHIFTS);
    let (values) = keccak_round(values, 0x800000000000008B * SHIFTS);
    let (values) = keccak_round(values, 0x8000000000008089 * SHIFTS);
    let (values) = keccak_round(values, 0x8000000000008003 * SHIFTS);
    let (values) = keccak_round(values, 0x8000000000008002 * SHIFTS);
    let (values) = keccak_round(values, 0x8000000000000080 * SHIFTS);
    let (values) = keccak_round(values, 0x000000000000800A * SHIFTS);
    let (values) = keccak_round(values, 0x800000008000000A * SHIFTS);
    let (values) = keccak_round(values, 0x8000000080008081 * SHIFTS);
    let (values) = keccak_round(values, 0x8000000000008080 * SHIFTS);
    let (values) = keccak_round(values, 0x0000000080000001 * SHIFTS);
    let (values) = keccak_round(values, 0x8000000080008008 * SHIFTS);

    return (values=values);
}
