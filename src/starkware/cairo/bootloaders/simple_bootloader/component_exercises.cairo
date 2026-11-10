from starkware.cairo.common.cairo_builtins import (
    BitwiseBuiltin,
    EcOpBuiltin,
    HashBuiltin,
    ModBuiltin,
    PoseidonBuiltin,
    UInt384,
)
from starkware.cairo.common.modulo import run_mod_p_circuit
from starkware.cairo.common.poseidon_state import PoseidonBuiltinState
from starkware.cairo.common.registers import get_fp_and_pc, get_label_location

// Dummy invocations of opcodes and builtins, used by the circuit-facing bootloaders (the privacy
// and leaf simple bootloaders) to make sure every component required by the verifier circuit
// appears in the execution, regardless of what the input task uses.
//
// The builtin exercises only write the builtin inputs and deliberately leave the output cells
// unwritten, saving the instructions that would write them. The runner completes the missing
// cells after the run via the builtin auto-deduction rules (`fill_holes` in the Rust VM's
// CairoRunConfig, enabled in proof mode), before the segments reach the stwo adapter.

// Exercises the `jmp abs [[reg + offset]]` (double-dereference) opcode.
func jump_abs_double_deref() {
    alloc_locals;
    let (__fp__, _) = get_fp_and_pc();
    let (local label_location) = get_label_location(jump_abs_double_deref_lbl);
    local label_location_addr: felt** = &label_location;

    // Compiles to `jmp abs [[fp + 1]]`.
    jmp abs [label_location_addr];

    jump_abs_double_deref_lbl:
    return ();
}

// Exercises the `jmp rel [reg + offset]` opcode.
func jump_rel() {
    tempvar one = 1;
    // Jump to `return ()` (the instruction compiles to `jmp rel [ap + (-1)]`).
    jmp rel one;
    return ();
}

// Exercises the `jmp abs [reg + offset]` opcode.
func jump_abs() {
    let (label_location) = get_label_location(jump_abs_lbl);
    // Compiles to `jmp abs [ap + (-1)]`.
    jmp abs label_location;

    jump_abs_lbl:
    return ();
}

// Exercises the "big add" and "big mul" opcodes.
// An add opcode is considered "small" if all its operands are within [-2^29 - 1, 2^29 - 1].
// A mul opcode is considered "small" if the factors are < 2^36.
func big_int_ops() {
    tempvar x = 2 ** 200;
    tempvar y = x * x + x;
    return ();
}

// Exercises the generic opcode: a conditional jump whose offset is read from memory (rather than
// an immediate), which none of the specialized opcode components handles.
func generic_opcode() {
    tempvar one = 1;
    // Jumps to the `ret` opcode.
    // Compiles to `jmp rel [ap + (-1)] if [ap + (-1)] != 0`.
    jmp rel one if one != 0;
    return ();
}

// Exercises the QM31 add/mul opcode.
func qm31_op() {
    alloc_locals;
    const IN_A = 0x544b2fba;
    const IN_B = 0x673cff77;
    const IN_C = 0x60713d44;
    const IN_D = 0x499602d2;
    local op0 = IN_A + IN_B * (2 ** 36) + IN_C * (2 ** 72) + IN_D * (2 ** 108);

    static_assert op0 == [fp];

    // The opcode `[ap] = [fp] x [fp]; ap++` (QM31 multiplication).
    dw 0x1c84a800080008000;

    return ();
}

// Exercises the bitwise builtin.
func do_bitwise{bitwise_ptr: BitwiseBuiltin*}() {
    assert bitwise_ptr[0].x = 3;
    assert bitwise_ptr[0].y = 6;
    let bitwise_ptr = &bitwise_ptr[1];
    return ();
}

// Exercises the pedersen builtin.
func do_pedersen{pedersen_ptr: HashBuiltin*}() {
    assert pedersen_ptr[0].x = 123;
    assert pedersen_ptr[0].y = 456;
    let pedersen_ptr = &pedersen_ptr[1];
    return ();
}

// Exercises the poseidon builtin.
func do_poseidon{poseidon_ptr: PoseidonBuiltin*}() {
    assert poseidon_ptr[0].input = PoseidonBuiltinState(s0=0, s1=1, s2=2);
    let poseidon_ptr = &poseidon_ptr[1];
    return ();
}

// Exercises the ec_op builtin by computing r = p + 3 * q for known points p, q.
func do_ec_op{ec_op_ptr: EcOpBuiltin*}() {
    assert ec_op_ptr[0].p.x = 0x49ee3eba8c1600700ee1b87eb599f16716b0b1022947733551fde4050ca6804;
    assert ec_op_ptr[0].p.y = 0x3ca0cfe4b3bc6ddf346d49d06ea0ed34e621062c0e056c1d0405d266e10268a;
    assert ec_op_ptr[0].q.x = 0x1ef15c18599971b7beced415a40f0c7deacfd9b0d1819e03d723d8bc943cfca;
    assert ec_op_ptr[0].q.y = 0x5668060aa49730b7be4801df46ec62de53ecd11abe43a32873000c36e8dc1f;
    assert ec_op_ptr[0].m = 3;
    let ec_op_ptr = &ec_op_ptr[1];
    return ();
}

// Exercises the range_check96, add_mod and mul_mod builtins by running a mod-p circuit.
func do_mod_builtins{range_check96_ptr, add_mod_ptr: ModBuiltin*, mul_mod_ptr: ModBuiltin*}() {
    // The prime.
    let p = UInt384(
        d0=0xb153ffffb9feffffffffaaab,
        d1=0x6730d2a0f6b0f6241eabfffe,
        d2=0x434bacd764774b84f38512bf,
        d3=0x1a0111ea397fe69a4b1ba7b6,
    );

    // Allocate 12 range_check96 values (3 UInt384).
    let vals = cast(range_check96_ptr, UInt384*);
    let range_check96_ptr = cast(&vals[3], felt);

    assert vals[0] = UInt384(d0=0x1234, d1=0x5678, d2=0x9abc, d3=0xdef0);
    let (add_mod_offsets_ptr) = get_label_location(adds_offsets);
    let (mul_mod_offsets_ptr) = get_label_location(muls_offsets);
    run_mod_p_circuit(
        p=p,
        values_ptr=vals,
        add_mod_offsets_ptr=add_mod_offsets_ptr,
        add_mod_n=1,
        mul_mod_offsets_ptr=mul_mod_offsets_ptr,
        mul_mod_n=1,
    );

    return ();

    adds_offsets:
    dw 0;
    dw 0;
    dw 4;

    muls_offsets:
    dw 0;
    dw 0;
    dw 8;
}
