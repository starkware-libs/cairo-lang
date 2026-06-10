%builtins output pedersen range_check ecdsa bitwise ec_op keccak poseidon range_check96 add_mod mul_mod

from starkware.cairo.bootloaders.simple_bootloader.run_simple_bootloader import (
    run_simple_bootloader,
)
from starkware.cairo.bootloaders.simple_bootloader.verify_builtins import (
    create_ec_op_builtin_segment_if_needed,
    create_keccak_builtin_segment_if_needed,
    verify_ec_op_builtin_if_needed,
    verify_keccak_builtin_if_needed,
)
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_blake2s.blake2s import encode_felt252_data_and_calc_blake_hash
from starkware.cairo.common.cairo_builtins import (
    BitwiseBuiltin,
    EcOpBuiltin,
    HashBuiltin,
    KeccakBuiltin,
    ModBuiltin,
    PoseidonBuiltin,
    SignatureBuiltin,
)
from starkware.cairo.common.registers import get_fp_and_pc

// Exercises the `jmp abs [[reg] + offset]` (double-dereference) opcode.
func jump_abs_double_deref() {
    alloc_locals;
    let (_, local __pc__) = get_fp_and_pc();
    local x = cast(__pc__ + 8, felt);
    call rel 2;
    jmp abs [[ap - 2] + 1];
    [ap] = 5, ap++;
    ret;
}

// Exercises the `jmp rel [reg + offset]` opcode.
func jump_rel() {
    [ap] = 1, ap++;
    jmp rel [ap - 1];
    ret;
}

// Exercises the `jmp abs [reg + offset]` opcode.
func jump_abs() {
    call rel 2;
    [ap] = [ap - 1] + 3;
    jmp abs [ap];
    ret;
}

// Exercises a "big add" — an add opcode is considered "small" if all its operands (mod P) are
// within [-2^29 - 1, 2^29 - 1], and "big" otherwise. Here we produce a result of 2^29 to ensure
// at least one operand falls outside that range.
func add_big() {
    call rel 2;
    [ap] = 536870910, ap++;
    [ap] = 1, ap++;
    // 536870910 + 1 = 2^29 - 1.
    [ap] = [fp] + [ap - 1], ap++;
    // add 1 to the result to get 2^29.
    [ap] = [ap - 1] + 1, ap++;
    [ap] = 1, ap++;
    ret;
}

// Exercises a "big mul" — a multiplication where at least one factor is >= 2^36.
func mul_big() {
    [ap] = 8, ap++;
    // 2^36 is the minimal factor value for a big mul.
    [ap] = 262144, ap++;
    [ap] = [ap - 1] * 262144, ap++;  // (2^18)^2 = 2^36.
    [ap] = [ap - 1] * [ap - 3], ap++;  // 2^36 * 8 => mul_big is invoked here.
    [ap] = [ap - 2] * 2, ap++;
    [ap] = 1, ap++;
    ret;
}

// Exercises the bitwise builtin by computing AND, XOR, and OR of two known values (3 and 6).
func do_bitwise{bitwise_ptr: BitwiseBuiltin*}() {
    assert bitwise_ptr.x = 3;  // Binary representation 0b011.
    assert bitwise_ptr.y = 6;  // Binary representation 0b110.
    assert 0x2 = bitwise_ptr.x_and_y;  // Calculate 0b011 & 0b110 = 0b010 = 0x2.
    assert 0x5 = bitwise_ptr.x_xor_y;  // Calculate 0b011 ^ 0b110 = 0b101 = 0x5.
    assert 0x7 = bitwise_ptr.x_or_y;  // Calculate 0b011 & 0b110 = 0b111 = 0x7.
    let bitwise_ptr = bitwise_ptr + BitwiseBuiltin.SIZE;
    return ();
}

// For documentation of the simple bootloader, see the docstring of `run_simple_bootloader'.
// Hint arguments:
// program_input - contains the tasks to execute. Formatted as a SimpleBootloaderInput object.
func main{
    output_ptr: felt*,
    pedersen_ptr: HashBuiltin*,
    range_check_ptr,
    ecdsa_ptr: SignatureBuiltin*,
    bitwise_ptr: BitwiseBuiltin*,
    ec_op_ptr: EcOpBuiltin*,
    keccak_ptr: KeccakBuiltin*,
    poseidon_ptr: PoseidonBuiltin*,
    range_check96_ptr,
    add_mod_ptr: ModBuiltin*,
    mul_mod_ptr: ModBuiltin*,
}() {
    alloc_locals;
    %{ LOAD_PRIVACY_SIMPLE_BOOTLOADER_INPUT %}

    // Handle ec_op builtin.
    // See docstring of `create_ec_op_builtin_segment_if_needed` for more info.
    local ec_op_ptr_orig: EcOpBuiltin* = ec_op_ptr;
    let (local ec_op_ptr: EcOpBuiltin*) = create_ec_op_builtin_segment_if_needed(
        ec_op_ptr=ec_op_ptr
    );
    local ec_op_start_ptr: EcOpBuiltin* = ec_op_ptr;

    // Handle keccak builtin.
    // See docstring of `create_keccak_builtin_segment_if_needed` for more info.
    local keccak_ptr_orig: KeccakBuiltin* = keccak_ptr;
    let (local keccak_ptr: KeccakBuiltin*) = create_keccak_builtin_segment_if_needed(
        keccak_ptr=keccak_ptr
    );
    local keccak_start_ptr: KeccakBuiltin* = keccak_ptr;

    // Execute tasks.
    let (local simple_bl_output: felt*) = alloc();
    let simple_bl_output_start = simple_bl_output;
    run_simple_bootloader{output_ptr=simple_bl_output}();

    // Verify the ec_op builtin. See docstring of `verify_ec_op_builtin_if_needed` for more info.
    let (local ec_op_ptr: EcOpBuiltin*) = verify_ec_op_builtin_if_needed(
        ec_op_ptr=ec_op_ptr, ec_op_ptr_orig=ec_op_ptr_orig, ec_op_start_ptr=ec_op_start_ptr
    );

    // Verify the keccak builtin. See docstring of `verify_keccak_builtin_if_needed` for more
    // info.
    let (local keccak_ptr: KeccakBuiltin*) = verify_keccak_builtin_if_needed(
        keccak_ptr=keccak_ptr, keccak_ptr_orig=keccak_ptr_orig, keccak_start_ptr=keccak_start_ptr
    );

    // Invoke additional opcodes and builtins to make sure all needed components for the circuit
    // verifier are present in the execution.
    // Assumptions:
    // - The generic opcode will never be present.
    // - ECDSA, keccak, range_check96, add_mod and mul_mod builtins won't ever be present.
    // - Pedersen and Poseidon builtins will be present in the input task(s).
    jump_abs();
    ap += 1;
    jump_abs_double_deref();
    jump_rel();
    add_big();
    mul_big();
    do_bitwise();

    %{ DUMP_PRIVACY_SIMPLE_BOOTLOADER_OUTPUT_PREIMAGE %}

    let (output_hash: felt) = encode_felt252_data_and_calc_blake_hash(
        data_len=simple_bl_output - simple_bl_output_start, data=simple_bl_output_start
    );
    assert output_ptr[0] = output_hash;
    let output_ptr = output_ptr + 1;
    return ();
}
