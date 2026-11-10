%builtins output pedersen range_check ecdsa bitwise ec_op keccak poseidon range_check96 add_mod mul_mod

from starkware.cairo.bootloaders.simple_bootloader.component_exercises import (
    big_int_ops,
    do_bitwise,
    do_ec_op,
    do_mod_builtins,
    do_pedersen,
    do_poseidon,
    generic_opcode,
    jump_abs,
    jump_abs_double_deref,
    jump_rel,
    qm31_op,
)
from starkware.cairo.bootloaders.simple_bootloader.run_simple_bootloader import (
    run_simple_bootloader,
)
from starkware.cairo.bootloaders.simple_bootloader.verify_builtins import (
    create_ecdsa_builtin_segment_if_needed,
    create_keccak_builtin_segment_if_needed,
    verify_ecdsa_builtin_if_needed,
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

// A simple bootloader variant that runs exactly one task and outputs only the blake2s hash of the
// task's program hash followed by the task's output.
// It is intended to be proven with stwo on the all_cairo_stwo layout and verified by the verifier
// circuit, which requires every circuit component to appear in the execution - hence the dummy
// invocations of the opcodes and builtins that the task is not guaranteed to use (see
// component_exercises.cairo).

// Hint arguments:
// program_input - contains the single task to execute. Formatted as a
// PrivacySimpleBootloaderInput object.
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

    // Handle keccak builtin (not present in the all_cairo_stwo layout).
    // See docstring of `create_keccak_builtin_segment_if_needed` for more info.
    local keccak_ptr_orig: KeccakBuiltin* = keccak_ptr;
    let (local keccak_ptr: KeccakBuiltin*) = create_keccak_builtin_segment_if_needed(
        keccak_ptr=keccak_ptr
    );
    let keccak_start_ptr: KeccakBuiltin* = keccak_ptr;

    // Handle ecdsa builtin (not present in the all_cairo_stwo layout).
    // See docstring of `create_ecdsa_builtin_segment_if_needed` for more info.
    local ecdsa_ptr_orig: SignatureBuiltin* = ecdsa_ptr;
    let (local ecdsa_ptr: SignatureBuiltin*) = create_ecdsa_builtin_segment_if_needed(
        ecdsa_ptr=ecdsa_ptr
    );
    let ecdsa_start_ptr: SignatureBuiltin* = ecdsa_ptr;

    // Execute the task, writing its output to a local segment; only a hash of it is written to
    // the actual output.
    let (local task_segment_start: felt*) = alloc();
    let task_segment_end = task_segment_start;
    run_simple_bootloader{output_ptr=task_segment_end}();

    // Check that exactly one task was executed.
    assert task_segment_start[0] = 1;

    // Verify the keccak builtin. See docstring of `verify_keccak_builtin_if_needed` for more
    // info.
    let (local keccak_ptr: KeccakBuiltin*) = verify_keccak_builtin_if_needed(
        keccak_ptr=keccak_ptr, keccak_ptr_orig=keccak_ptr_orig, keccak_start_ptr=keccak_start_ptr
    );

    // Verify the ecdsa builtin. See docstring of `verify_ecdsa_builtin_if_needed` for more info.
    let (local ecdsa_ptr: SignatureBuiltin*) = verify_ecdsa_builtin_if_needed(
        ecdsa_ptr=ecdsa_ptr, ecdsa_ptr_orig=ecdsa_ptr_orig, ecdsa_start_ptr=ecdsa_start_ptr
    );

    // Invoke additional opcodes and builtins to make sure all needed components for the circuit
    // verifier are present in the execution.
    // Assumptions:
    // - The ECDSA and keccak builtins are simulated with other components if the task uses them,
    //   so they are never present in the execution.
    jump_abs();
    jump_abs_double_deref();
    jump_rel();
    big_int_ops();
    generic_opcode();
    qm31_op();
    do_bitwise();
    do_pedersen();
    do_poseidon();
    do_ec_op();
    do_mod_builtins();

    // The hashed output preimage is the task's program hash followed by the task's output,
    // skipping the two scratch slots (number of tasks and task output size) at the start of the
    // task segment.
    // Note: the names `simple_bl_output_start` and `simple_bl_output` are read by the hint below.
    local simple_bl_output_start: felt* = task_segment_start + 2;
    local simple_bl_output: felt* = task_segment_end;

    %{ DUMP_PRIVACY_SIMPLE_BOOTLOADER_OUTPUT_PREIMAGE %}

    let output_hash = encode_felt252_data_and_calc_blake2s(
        data_len=simple_bl_output - simple_bl_output_start, data=simple_bl_output_start
    );
    assert [cast(output_ptr, Uint256*)] = output_hash;
    let output_ptr = output_ptr + Uint256.SIZE;
    return ();
}
