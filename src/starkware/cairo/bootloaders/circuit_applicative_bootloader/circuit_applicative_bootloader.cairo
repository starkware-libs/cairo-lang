%builtins output pedersen range_check ecdsa bitwise ec_op keccak poseidon range_check96 add_mod mul_mod

from starkware.cairo.bootloaders.circuit_applicative_bootloader.circuit_unpack import (
    BLAKE2S_DIGEST_N_WORDS,
    CircuitUnpackerConfig,
    unpack_circuit_tree,
)
from starkware.cairo.bootloaders.circuit_applicative_bootloader.config_commitment import (
    compute_circuit_applicative_bootloader_config_commitment,
)
from starkware.cairo.bootloaders.simple_bootloader.execute_task import BLAKE_HASH, PEDERSEN_HASH
from starkware.cairo.bootloaders.simple_bootloader.run_simple_bootloader import (
    run_simple_bootloader,
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
from starkware.cairo.common.hash import hash2
from starkware.cairo.common.memcpy import memcpy

const AGGREGATOR_CONSTANT = 'AGGREGATOR';

// Computes a modified program hash for the aggregator task by hashing the word "AGGREGATOR" with
// the aggregator program hash. This distinguishes aggregator programs from regular programs.
//
// Arguments:
// aggregator_program_hash - The original program hash of the aggregator task.
// program_hash_function - The hash function H to use (PEDERSEN_HASH or BLAKE_HASH).
//
// Implicit arguments:
// range_check_ptr - Pointer to the range check builtin (used for Blake).
// pedersen_ptr - Pointer to the pedersen builtin.
//
// Returns:
// hash - The modified aggregator program hash: H("AGGREGATOR", aggregator_program_hash).
func compute_modified_aggregator_program_hash{pedersen_ptr: HashBuiltin*, range_check_ptr: felt}(
    aggregator_program_hash: felt, program_hash_function: felt
) -> (hash: felt) {
    if (program_hash_function == BLAKE_HASH) {
        let (input_data: felt*) = alloc();
        assert input_data[0] = AGGREGATOR_CONSTANT;
        assert input_data[1] = aggregator_program_hash;
        let (hash) = encode_felt252_data_and_calc_blake_hash(data_len=2, data=input_data);
        return (hash=hash);
    }
    assert program_hash_function = PEDERSEN_HASH;
    let (hash) = hash2{hash_ptr=pedersen_ptr}(AGGREGATOR_CONSTANT, aggregator_program_hash);
    return (hash=hash);
}

// The applicative bootloader of the circuit recursive-tree flow. It runs the circuit verifier as a
// single task (verifying the recursive tree's root circuit proof and emitting its output digest),
// then opens that digest down to the raw leaf task outputs with `unpack_circuit_tree` (walking
// the prover's packed-output tree hash by hash).
//
// Runs the simple bootloader on the aggregator task, then on the circuit verifier task; unpacks
// the packed-output tree against the verifier's digest; compares the reconstructed tasks output
// with the aggregator's input; and outputs the aggregated output.
//
// Hint arguments:
// program_input - Contains the aggregator task, the circuit verifier task, the packed output tree,
// and the supported circuit hashes. Formatted as a CircuitApplicativeBootloaderInput object.
//
// Returns (written to output_ptr):
// - The modified aggregator program hash (the aggregator program hash, hashed with the word
//   "AGGREGATOR").
// - The config commitment: a hash binding the circuit verifier program hash and the supported
//   circuit hashes the unpacking trusted.
// - The aggregated output.
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
    ap += SIZEOF_LOCALS;
    local task_range_check_ptr;

    // A pointer to the aggregator's task output.
    local aggregator_output_ptr: felt*;
    // The following hint is used to:
    // 1. Load the CircuitApplicativeBootloaderInput.
    // 2. Create a segment for the aggregator output (ids.aggregator_output_ptr).
    // 3. Save the applicative output builtin state.
    // 4. Point the output builtin at the aggregator segment.
    // 5. Prepare the simple bootloader input holding only the aggregator task.
    // 6. Set the `aggregator_program_hash_function` scope variable.
    %{ LOAD_CIRCUIT_APPLICATIVE_BOOTLOADER_INPUT %}

    // Save aggregator output start.
    let aggregator_output_start: felt* = aggregator_output_ptr;

    // Execute the simple bootloader with the aggregator task.
    run_simple_bootloader{output_ptr=aggregator_output_ptr}();
    local aggregator_output_end: felt* = aggregator_output_ptr;

    // Check that exactly one task was executed.
    assert aggregator_output_start[0] = 1;

    // Extract the aggregator output length (includes the header length (2)) and program hash.
    let aggregator_output_length = aggregator_output_start[1];
    let aggregator_program_hash = aggregator_output_start[2];

    // Sanity check, not contributing to soundness (as long as the simple bootloader is not
    // changed).
    assert aggregator_output_length = aggregator_output_end - aggregator_output_start - 1;

    // Set the aggregator input pointer.
    let aggregator_input_ptr = &aggregator_output_start[3];

    // A pointer to the circuit verifier task's output.
    local verifier_output_ptr: felt*;
    // The following hint is used to:
    // 1. Save the aggregator's fact topologies (resetting the list).
    // 2. Create a segment for the verifier task output (ids.verifier_output_ptr).
    // 3. Point the output builtin at it.
    // 4. Prepare the simple bootloader input holding only the circuit verifier task.
    %{ CIRCUIT_APPLICATIVE_SETUP_VERIFIER_RUN %}

    let verifier_output_start: felt* = verifier_output_ptr;

    // Execute the simple bootloader with the circuit verifier task.
    run_simple_bootloader{output_ptr=verifier_output_ptr}();
    local verifier_output_end: felt* = verifier_output_ptr;

    local range_check_ptr = range_check_ptr;
    local ecdsa_ptr: SignatureBuiltin* = ecdsa_ptr;
    local bitwise_ptr: BitwiseBuiltin* = bitwise_ptr;
    local ec_op_ptr: EcOpBuiltin* = ec_op_ptr;
    local keccak_ptr: KeccakBuiltin* = keccak_ptr;
    local pedersen_ptr: HashBuiltin* = pedersen_ptr;
    local poseidon_ptr: PoseidonBuiltin* = poseidon_ptr;
    local range_check96_ptr = range_check96_ptr;
    local add_mod_ptr: ModBuiltin* = add_mod_ptr;
    local mul_mod_ptr: ModBuiltin* = mul_mod_ptr;

    // Check that exactly one task was executed.
    assert verifier_output_start[0] = 1;
    // The verifier task's output is the eight-word digest.
    assert verifier_output_start[1] = 2 + BLAKE2S_DIGEST_N_WORDS;
    let verifier_program_hash = verifier_output_start[2];
    let verifier_digest: felt* = &verifier_output_start[3];

    // The following hint is used to:
    // 1. Restore the applicative output builtin state.
    // 2. Build the unpacker config from the input's supported circuit hashes (ids.config).
    // 3. Enter the packed-output root node scope.
    local config: CircuitUnpackerConfig*;
    %{ CIRCUIT_APPLICATIVE_SETUP_UNPACK %}

    // Unpack the verified digest.
    let tasks_output = aggregator_input_ptr;
    with tasks_output {
        unpack_circuit_tree(config=config, verifier_output=verifier_digest);
    }
    // Exits the packed-output root node scope.
    %{ CIRCUIT_UNPACK_EXIT_SCOPE %}
    local tasks_output_end: felt* = tasks_output;
    local range_check_ptr = range_check_ptr;

    // Output:
    // * The aggregator program hash, hashed with the word "AGGREGATOR".
    // * The config commitment.

    // Save the applicative bootloader output start.
    local output_start: felt* = output_ptr;
    // Read the aggregator task program hash function from the bootloader input.
    tempvar aggregator_program_hash_function = nondet %{ aggregator_program_hash_function %};
    let (modified_aggregator_program_hash) = compute_modified_aggregator_program_hash(
        aggregator_program_hash=aggregator_program_hash,
        program_hash_function=aggregator_program_hash_function,
    );
    local pedersen_ptr: HashBuiltin* = pedersen_ptr;
    local range_check_ptr = range_check_ptr;
    assert output_ptr[0] = modified_aggregator_program_hash;
    let output_ptr = &output_ptr[1];

    // See `config_commitment.cairo` (the on-chain unpacker recomputes the same commitment).
    let (config_commitment) = compute_circuit_applicative_bootloader_config_commitment(
        verifier_program_hash=verifier_program_hash, config=config
    );
    local pedersen_ptr: HashBuiltin* = pedersen_ptr;
    assert output_ptr[0] = config_commitment;
    let output_ptr = &output_ptr[1];

    // Output the aggregated output.
    let aggregated_output_ptr = tasks_output_end;
    let aggregated_output_length = aggregator_output_end - aggregated_output_ptr;
    memcpy(dst=output_ptr, src=aggregated_output_ptr, len=aggregated_output_length);
    let output_ptr = output_ptr + aggregated_output_length;

    // The following hint is used to:
    // 1. Build the final fact topology from the aggregator's (page 0 resized for the removed
    //    tasks output and the added header).
    // 2. Configure the output builtin pages.
    // 3. Dump the topologies file.
    // It reads ids.output_start, ids.aggregator_input_ptr and ids.tasks_output_end.
    %{ CIRCUIT_APPLICATIVE_WRITE_FACT_TOPOLOGY %}

    return ();
}
