%builtins output pedersen range_check bitwise

from starkware.cairo.cairo_verifier.objects import CairoVerifierOutput
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin, HashBuiltin
from starkware.cairo.common.hash_state import hash_felts
from starkware.cairo.common.math import assert_nn_le
from starkware.cairo.common.registers import get_label_location
from starkware.cairo.stark_verifier.air.layouts.recursive.public_verify import (
    get_layout_builtins,
    segments,
)
from starkware.cairo.stark_verifier.air.layouts.recursive.verify import verify_proof
from starkware.cairo.stark_verifier.air.public_input import PublicInput, SegmentInfo
from starkware.cairo.stark_verifier.air.public_memory import AddrValue
from starkware.cairo.stark_verifier.core.stark import StarkProof

const SECURITY_BITS = 80;
const MAX_ADDRESS = 2 ** 64 - 1;
const INITIAL_PC = 1;

// Returns the list of builtins that need to be passed to the verified program.
// The list is zero-terminated.
//
// See verify_stack() for more detail.
func get_program_builtins() -> (n_builtins: felt, builtins: felt*) {
    let (builtins_address) = get_label_location(data);
    let n_builtins = 7;
    assert builtins_address[n_builtins] = 0;
    return (n_builtins=n_builtins, builtins=builtins_address);

    data:
    dw 'output';
    dw 'pedersen';
    dw 'range_check';
    dw 'ecdsa';
    dw 'bitwise';
    dw 'ec_op';
    dw 'keccak';
    dw 0;
}

// Verifies a complete Cairo proof of a Cairo program with a "start" section, with a single output
// page.
// Returns the program hash and the output hash.
func verify_cairo_proof{range_check_ptr, pedersen_ptr: HashBuiltin*, bitwise_ptr: BitwiseBuiltin*}(
    proof: StarkProof*
) -> (program_hash: felt, output_hash: felt) {
    alloc_locals;
    verify_proof(proof=proof, security_bits=SECURITY_BITS);
    return _verify_public_input(public_input=cast(proof.public_input, PublicInput*));
}

func _verify_public_input{
    range_check_ptr, pedersen_ptr: HashBuiltin*, bitwise_ptr: BitwiseBuiltin*
}(public_input: PublicInput*) -> (program_hash: felt, output_hash: felt) {
    alloc_locals;
    local public_segments: SegmentInfo* = public_input.segments;

    local initial_pc = public_segments[segments.PROGRAM].begin_addr;
    local final_pc = public_segments[segments.PROGRAM].stop_ptr;
    local initial_ap = public_segments[segments.EXECUTION].begin_addr;
    let initial_fp = initial_ap;
    local final_ap = public_segments[segments.EXECUTION].stop_ptr;
    local output_start = public_segments[segments.OUTPUT].begin_addr;
    local output_stop = public_segments[segments.OUTPUT].stop_ptr;

    // Sanity checks.
    assert_nn_le(initial_ap, MAX_ADDRESS);
    assert_nn_le(final_ap, MAX_ADDRESS);

    assert public_input.n_continuous_pages = 0;

    // Program builtins.
    let (n_program_builtins, program_builtins) = get_program_builtins();
    let (n_layout_builtins, layout_builtins) = get_layout_builtins();

    // Verify the public memory.
    let memory: AddrValue* = public_input.main_page;
    with memory {
        // 1. Program segment.
        // Check that the program counter starts and ends at the right places.
        assert initial_pc = INITIAL_PC;
        assert final_pc = INITIAL_PC + 4;
        // Extract program.
        let (program: felt*) = alloc();
        let program_end_pc = initial_fp - 2;
        let program_len = program_end_pc - initial_pc;
        extract_range(addr=initial_pc, length=program_len, output=program);
        // Check that the program starts with a "start" section as follows:
        assert program[0] = 0x40780017fff7fff;  // Instruction: ap += N_BUILTINS.
        assert program[1] = n_program_builtins;
        assert program[2] = 0x1104800180018000;  // Instruction: call rel ?.
        assert program[4] = 0x10780017fff7fff;  // Instruction: jmp rel 0.
        assert program[5] = 0x0;
        // Program hash.
        let (program_hash) = hash_felts{hash_ptr=pedersen_ptr}(data=program, length=program_len);

        // 2. Execution segment.
        // 2.1. initial_fp, initial_pc.
        // Make sure [initial_fp - 2] = initial_fp.
        // This is required for the "safe call" feature (that is, all "call" instructions will
        // return, even if the called function is malicious).
        // It guarantees that it's not possible to create a cycle in the call stack.
        assert memory[0] = AddrValue(address=initial_fp - 2, value=initial_fp);
        // Make sure [initial_fp - 1] = 0.
        assert memory[1] = AddrValue(address=initial_fp - 1, value=0);
        let memory = &memory[2];
        // 2.2 main's arguments and return values.
        verify_stack(
            start_ap=initial_ap,
            segment_addresses=&public_segments[2].begin_addr,
            program_builtins=program_builtins,
            layout_builtins=layout_builtins,
        );
        verify_stack(
            start_ap=final_ap - n_program_builtins,
            segment_addresses=&public_segments[2].stop_ptr,
            program_builtins=program_builtins,
            layout_builtins=layout_builtins,
        );
        // 3. Output segment.
        let (output: felt*) = alloc();
        local output_len = output_stop - output_start;
        extract_range(addr=output_start, length=output_len, output=output);
        let (output_hash) = hash_felts{hash_ptr=pedersen_ptr}(data=output, length=output_len);
    }

    // Make sure main_page_len is correct.
    assert memory = &public_input.main_page[public_input.main_page_len];

    return (program_hash=program_hash, output_hash=output_hash);
}

// Verifies the initial or the final part of the stack.
// segment_addresses should point to either begin_addr, or stop_ptr for the segment of the first
// builtin, inside a SegmentInfo array (i.e. step SegmentInfo.SIZE).
func verify_stack{memory: AddrValue*}(
    start_ap: felt, segment_addresses: felt*, program_builtins: felt*, layout_builtins: felt*
) {
    if (program_builtins[0] == 0) {
        // Done.
        return ();
    }

    if (program_builtins[0] != layout_builtins[0]) {
        // Skip.
        assert memory[0] = AddrValue(address=start_ap, value=0);
        let memory = &memory[1];
        return verify_stack(
            start_ap=start_ap + 1,
            segment_addresses=segment_addresses,
            program_builtins=&program_builtins[1],
            layout_builtins=layout_builtins,
        );
    } else {
        // Use.
        assert memory[0] = AddrValue(address=start_ap, value=[segment_addresses]);
        let memory = &memory[1];
        return verify_stack(
            start_ap=start_ap + 1,
            segment_addresses=segment_addresses + SegmentInfo.SIZE,
            program_builtins=&program_builtins[1],
            layout_builtins=&layout_builtins[1],
        );
    }
}

// Extracts a consecutive memory range from the public memory of the Cairo proof.
func extract_range{memory: AddrValue*}(addr: felt, length: felt, output: felt*) {
    if (length == 0) {
        return ();
    }
    assert memory.address = addr;
    assert output[0] = memory.value;
    let memory = &memory[1];
    return extract_range(addr=addr + 1, length=length - 1, output=&output[1]);
}

// Main function for the Cairo verifier.
//
// Hint arguments:
// program_input - Contains the inputs for the Cairo verifier.
//
// Outputs the program hash and the hash of the output.
func main{
    output_ptr: felt*, pedersen_ptr: HashBuiltin*, range_check_ptr, bitwise_ptr: BitwiseBuiltin*
}() {
    alloc_locals;
    local proof: StarkProof*;
    %{
        from starkware.cairo.stark_verifier.air.parser import parse_proof
        ids.proof = segments.gen_arg(parse_proof(
            identifiers=ids._context.identifiers,
            proof_json=program_input["proof"]))
    %}
    let (program_hash, output_hash) = verify_cairo_proof(proof);

    // Write program_hash and output_hash to output.
    assert [cast(output_ptr, CairoVerifierOutput*)] = CairoVerifierOutput(
        program_hash=program_hash,
        output_hash=output_hash);
    let output_ptr = output_ptr + CairoVerifierOutput.SIZE;

    return ();
}
