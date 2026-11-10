%builtins output pedersen range_check ecdsa bitwise ec_op keccak poseidon range_check96 add_mod mul_mod

from starkware.cairo.bootloaders.simple_bootloader.component_exercises import (
    big_int_ops,
    do_bitwise,
    jump_abs,
    jump_abs_double_deref,
    jump_rel,
)
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
from starkware.cairo.common.cairo_blake2s.blake2s import encode_felt252_data_and_calc_blake2s
from starkware.cairo.common.cairo_builtins import (
    BitwiseBuiltin,
    EcOpBuiltin,
    HashBuiltin,
    KeccakBuiltin,
    ModBuiltin,
    PoseidonBuiltin,
    SignatureBuiltin,
)
from starkware.cairo.common.uint256 import Uint256

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
    jump_abs_double_deref();
    jump_rel();
    big_int_ops();
    do_bitwise();

    %{ DUMP_PRIVACY_SIMPLE_BOOTLOADER_OUTPUT_PREIMAGE %}

    let output_hash = encode_felt252_data_and_calc_blake2s(
        data_len=simple_bl_output - simple_bl_output_start, data=simple_bl_output_start
    );
    assert [cast(output_ptr, Uint256*)] = output_hash;
    let output_ptr = output_ptr + Uint256.SIZE;
    return ();
}
