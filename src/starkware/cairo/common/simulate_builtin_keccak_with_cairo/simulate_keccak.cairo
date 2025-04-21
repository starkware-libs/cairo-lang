from src.starkware.cairo.common.cairo_keccak.keccak import finalize_keccak

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.keccak_state import KeccakBuiltinState

// This function converts a KeccakBuiltinState to an array of 25 felts, each representing 64 bits.
// Receives a KeccakBuiltinState and a pointer to an array felts and writes 25 felts to the array.
func keccak_builtin_state_to_felts{range_check_ptr}(
    keccak_builtin_state: KeccakBuiltinState, felt_array: felt*
) {
    %{
        full_num = ids.keccak_builtin_state.s0
        full_num += (2**200) * ids.keccak_builtin_state.s1
        full_num += (2**400) * ids.keccak_builtin_state.s2
        full_num += (2**600) * ids.keccak_builtin_state.s3
        full_num += (2**800) * ids.keccak_builtin_state.s4
        full_num += (2**1000) * ids.keccak_builtin_state.s5
        full_num += (2**1200) * ids.keccak_builtin_state.s6
        full_num += (2**1400) * ids.keccak_builtin_state.s7
        for i in range(25):
            memory[ids.felt_array + i] = full_num % (2**64)
            full_num = full_num >> 64
    %}

    // Assert that felt_array[0], felt_array[1] and felt_array[2] consist of 8 bytes each.
    assert [range_check_ptr] = felt_array[0];
    assert [range_check_ptr + 1] = felt_array[0] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 2] = felt_array[1];
    assert [range_check_ptr + 3] = felt_array[1] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 4] = felt_array[2];
    assert [range_check_ptr + 5] = felt_array[2] - 256 ** 8 + 2 ** 128;

    // Split felt_array[3] into low3 (1 byte) and high3 (7 bytes).
    let low3 = [range_check_ptr + 6];
    let high3 = [range_check_ptr + 7];
    %{ ids.high3, ids.low3 = divmod(memory[ids.felt_array + 3], 256) %}
    assert [range_check_ptr + 8] = low3 - 256 + 2 ** 128;
    assert [range_check_ptr + 9] = high3 - 256 ** 7 + 2 ** 128;
    assert felt_array[3] = low3 + high3 * 256;

    // Assert that s0 is a concatenation of felt_array[0], felt_array[1], felt_array[2] and low3.
    assert keccak_builtin_state.s0 = felt_array[0] + felt_array[1] * 256 ** 8 + felt_array[2] *
        256 ** 16 + low3 * 256 ** 24;

    // Assert that felt_array[4] and felt_array[5] consist of 8 bytes each.
    assert [range_check_ptr + 10] = felt_array[4];
    assert [range_check_ptr + 11] = felt_array[4] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 12] = felt_array[5];
    assert [range_check_ptr + 13] = felt_array[5] - 256 ** 8 + 2 ** 128;

    // Split felt_array[6] into low6 (2 byte) and high6 (6 bytes).
    let low6 = [range_check_ptr + 14];
    let high6 = [range_check_ptr + 15];
    %{ ids.high6, ids.low6 = divmod(memory[ids.felt_array + 6], 256 ** 2) %}
    assert [range_check_ptr + 16] = low6 - 256 ** 2 + 2 ** 128;
    assert [range_check_ptr + 17] = high6 - 256 ** 6 + 2 ** 128;
    assert felt_array[6] = low6 + high6 * 256 ** 2;

    // Assert that s1 is a concatenation of high3, felt_array[4], felt_array[5] and low6.
    assert keccak_builtin_state.s1 = high3 + felt_array[4] * 256 ** 7 + felt_array[5] * 256 ** 15 +
        low6 * 256 ** 23;

    // Assert that felt_array[7] and felt_array[8] consist of 8 bytes each.
    assert [range_check_ptr + 18] = felt_array[7];
    assert [range_check_ptr + 19] = felt_array[7] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 20] = felt_array[8];
    assert [range_check_ptr + 21] = felt_array[8] - 256 ** 8 + 2 ** 128;

    // Split felt_array[9] into low9 (3 byte) and high9 (5 bytes).
    let low9 = [range_check_ptr + 22];
    let high9 = [range_check_ptr + 23];
    %{ ids.high9, ids.low9 = divmod(memory[ids.felt_array + 9], 256 ** 3) %}
    assert [range_check_ptr + 24] = low9 - 256 ** 3 + 2 ** 128;
    assert [range_check_ptr + 25] = high9 - 256 ** 5 + 2 ** 128;
    assert felt_array[9] = low9 + high9 * 256 ** 3;

    // Assert that s2 is a concatenation of high6, felt_array[7], felt_array[8] and low9.
    assert keccak_builtin_state.s2 = high6 + felt_array[7] * 256 ** 6 + felt_array[8] * 256 ** 14 +
        low9 * 256 ** 22;

    // Assert that felt_array[10] and felt_array[11] consist of 8 bytes each.
    assert [range_check_ptr + 26] = felt_array[10];
    assert [range_check_ptr + 27] = felt_array[10] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 28] = felt_array[11];
    assert [range_check_ptr + 29] = felt_array[11] - 256 ** 8 + 2 ** 128;

    // Split felt_array[12] into low12 (4 byte) and high12 (4 bytes).
    let low12 = [range_check_ptr + 30];
    let high12 = [range_check_ptr + 31];
    %{ ids.high12, ids.low12 = divmod(memory[ids.felt_array + 12], 256 ** 4) %}
    assert [range_check_ptr + 32] = low12 - 256 ** 4 + 2 ** 128;
    assert [range_check_ptr + 33] = high12 - 256 ** 4 + 2 ** 128;
    assert felt_array[12] = low12 + high12 * 256 ** 4;

    // Assert that s3 is a concatenation of high9, felt_array[10], felt_array[11] and low12.
    assert keccak_builtin_state.s3 = high9 + felt_array[10] * 256 ** 5 + felt_array[11] * 256 **
        13 + low12 * 256 ** 21;

    // Assert that felt_array[13] and felt_array[14] consist of 8 bytes each.
    assert [range_check_ptr + 34] = felt_array[13];
    assert [range_check_ptr + 35] = felt_array[13] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 36] = felt_array[14];
    assert [range_check_ptr + 37] = felt_array[14] - 256 ** 8 + 2 ** 128;

    // Split felt_array[15] into low15 (5 byte) and high15 (3 bytes).
    let low15 = [range_check_ptr + 38];
    let high15 = [range_check_ptr + 39];
    %{ ids.high15, ids.low15 = divmod(memory[ids.felt_array + 15], 256 ** 5) %}
    assert [range_check_ptr + 40] = low15 - 256 ** 5 + 2 ** 128;
    assert [range_check_ptr + 41] = high15 - 256 ** 3 + 2 ** 128;
    assert felt_array[15] = low15 + high15 * 256 ** 5;

    // Assert that s4 is a concatenation of high12, felt_array[13], felt_array[14] and low15.
    assert keccak_builtin_state.s4 = high12 + felt_array[13] * 256 ** 4 + felt_array[14] * 256 **
        12 + low15 * 256 ** 20;

    // Assert that felt_array[16] and felt_array[17] consist of 8 bytes each..
    assert [range_check_ptr + 42] = felt_array[16];
    assert [range_check_ptr + 43] = felt_array[16] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 44] = felt_array[17];
    assert [range_check_ptr + 45] = felt_array[17] - 256 ** 8 + 2 ** 128;

    // Split felt_array[18] into low18 (6 byte) and high18 (2 bytes).
    let low18 = [range_check_ptr + 46];
    let high18 = [range_check_ptr + 47];
    %{ ids.high18, ids.low18 = divmod(memory[ids.felt_array + 18], 256 ** 6) %}
    assert [range_check_ptr + 48] = low18 - 256 ** 6 + 2 ** 128;
    assert [range_check_ptr + 49] = high18 - 256 ** 2 + 2 ** 128;
    assert felt_array[18] = low18 + high18 * 256 ** 6;

    // Assert that s5 is a concatenation of high15, felt_array[16], felt_array[17] and low18.
    assert keccak_builtin_state.s5 = high15 + felt_array[16] * 256 ** 3 + felt_array[17] * 256 **
        11 + low18 * 256 ** 19;

    // Assert that felt_array[19] and felt_array[20] consist of 8 bytes each..
    assert [range_check_ptr + 50] = felt_array[19];
    assert [range_check_ptr + 51] = felt_array[19] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 52] = felt_array[20];
    assert [range_check_ptr + 53] = felt_array[20] - 256 ** 8 + 2 ** 128;

    // Split felt_array[21] into low21 (7 byte) and high21 (1 bytes).
    let low21 = [range_check_ptr + 54];
    let high21 = [range_check_ptr + 55];
    %{ ids.high21, ids.low21 = divmod(memory[ids.felt_array + 21], 256 ** 7) %}
    assert [range_check_ptr + 56] = low21 - 256 ** 7 + 2 ** 128;
    assert [range_check_ptr + 57] = high21 - 256 + 2 ** 128;
    assert felt_array[21] = low21 + high21 * 256 ** 7;

    // Assert that s6 is a concatenation of high18, felt_array[19], felt_array[20] and low21.
    assert keccak_builtin_state.s6 = high18 + felt_array[19] * 256 ** 2 + felt_array[20] * 256 **
        10 + low21 * 256 ** 18;

    // Assert that felt_array[22], felt_array[23] and felt_array[24] consist of 8 bytes each..
    assert [range_check_ptr + 58] = felt_array[22];
    assert [range_check_ptr + 59] = felt_array[22] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 60] = felt_array[23];
    assert [range_check_ptr + 61] = felt_array[23] - 256 ** 8 + 2 ** 128;
    assert [range_check_ptr + 62] = felt_array[24];
    assert [range_check_ptr + 63] = felt_array[24] - 256 ** 8 + 2 ** 128;

    // Assert that s7 is a concatenation of high21, felt_array[22],
    // felt_array[23] and felt_array[24].
    assert keccak_builtin_state.s7 = high21 + felt_array[22] * 256 + felt_array[23] * 256 ** 9 +
        felt_array[24] * 256 ** 17;

    let range_check_ptr = range_check_ptr + 64;

    return ();
}
