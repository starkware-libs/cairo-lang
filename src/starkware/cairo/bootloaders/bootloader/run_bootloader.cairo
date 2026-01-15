from starkware.cairo.bootloaders.bootloader.constants import BOOTLOADER_CONFIG_SIZE
from starkware.cairo.bootloaders.simple_bootloader.run_simple_bootloader import (
    run_simple_bootloader,
)
from starkware.cairo.cairo_verifier.objects import CairoVerifierHashedOutput
from starkware.cairo.common.builtin_poseidon.poseidon import poseidon_hash_many
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
from starkware.cairo.common.find_element import find_element
from starkware.cairo.common.hash_state import hash_felts
from starkware.cairo.common.memcpy import memcpy

// BLAKE_UNPACKING/POSEIDON_UNPACKING - The composite packed task output is unpacked using the
// Blake/Poseidon hash function.
// The unpacking is done by guessing the output of the subtasks and verifying that it matches the
// output hash given in the Cairo verifier output.
const BLAKE_UNPACKING = 0;
const POSEIDON_UNPACKING = 1;

struct BootloaderConfig {
    // The supported hashes of the simple bootloader program. Currently, we hash it using either
    // the poseidon or blake hash function in our verifiers.
    supported_simple_bootloader_hash_list_len: felt,
    supported_simple_bootloader_hash_list: felt*,
    // The hashes of the supported (Cairo) programs that verify a STARK proof for the Cairo machine.
    supported_cairo_verifier_program_hashes_len: felt,
    supported_cairo_verifier_program_hashes: felt*,
    // The hash of the applicative bootloader program.
    applicative_bootloader_program_hash: felt,
}

struct TaskOutputHeader {
    size: felt,
    program_hash: felt,
}

// Runs the simple bootloader on tasks and unpacks recursive tasks.
// A task is called recursive (or 'composite_packed_task') if its program hash is a cairo verifier
// hash given in the bootloader config. Otherwise it is called non-recursive (or leaf, or
// 'plain_packed_task').
// The unpacking is done as follows:
// For each non-recursive task, outputs the program hash and the output of the task.
// For each recursive task:
//   Guesses the output of its children (using `packed_outputs`), and verifies that it
//   matches the output hash given in the cairo verifier output using the appropriate hash function
//   (flagged by `unpacking_mode`). Then, unpacks each child recursively.
// Moreover, if a non-recursive task has the program hash of the applicative bootloader, then it
// verifies that it used the correct bootloader config and outputs the modified aggregator hash and
// the aggregated output, instead of the applicative bootloader hash and output.
//
// Hint arguments:
// bootloader_input - contains the following:
// - tasks: The tasks to execute.
// - packed_outputs: The packed outputs of the tasks, used for unpacking recursive tasks.
// - bootloader_config: The bootloader config, consisting of the simple bootloader program hash, the
//   applicative bootloader program hash, and the hash of the supported Cairo verifier programs.
//
// Returns (written to output_ptr):
// - The bootloader config.
// - The number of plain packed tasks (leaves) executed.
// - For each plain packed task:
//   - Size.
//   - Program hash.
//   - The output of the program (of length=Size-2).
//
// Note - except for the bootloader config, the output is in the same format as the output of the
// simple bootloader.
func run_bootloader{
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
}(unpacking_mode: felt) {
    ap += SIZEOF_LOCALS;

    local simple_bootloader_output_start: felt*;
    %{
        ids.simple_bootloader_output_start = segments.add()

        # Change output builtin state to a different segment in preparation for calling the
        # simple bootloader.
        output_builtin_state = output_builtin.get_state()
        output_builtin.new_state(base=ids.simple_bootloader_output_start)
    %}

    // Save segment's start.
    let simple_bootloader_output_ptr: felt* = simple_bootloader_output_start;

    // Call the simple bootloader program to execute direct subtasks. Simple bootloader input is
    // contained in the bootloader input.
    %{ simple_bootloader_input = bootloader_input %}
    run_simple_bootloader{output_ptr=simple_bootloader_output_ptr}();
    local range_check_ptr = range_check_ptr;
    local ecdsa_ptr: SignatureBuiltin* = ecdsa_ptr;
    local bitwise_ptr: BitwiseBuiltin* = bitwise_ptr;
    local ec_op_ptr: EcOpBuiltin* = ec_op_ptr;
    local keccak_ptr: KeccakBuiltin* = keccak_ptr;
    local poseidon_ptr: PoseidonBuiltin* = poseidon_ptr;
    local range_check96_ptr = range_check96_ptr;
    local add_mod_ptr: ModBuiltin* = add_mod_ptr;
    local mul_mod_ptr: ModBuiltin* = mul_mod_ptr;
    local simple_bootloader_output_end: felt* = simple_bootloader_output_ptr;

    %{
        # Restore the bootloader's output builtin state.
        output_builtin.set_state(output_builtin_state)
    %}

    local bootloader_config: BootloaderConfig*;
    %{
        from starkware.cairo.bootloaders.bootloader.objects import BootloaderConfig

        bootloader_config: BootloaderConfig = bootloader_input.bootloader_config

        ids.bootloader_config = segments.gen_arg(
            [
                len(bootloader_config.supported_simple_bootloader_hash_list),
                bootloader_config.supported_simple_bootloader_hash_list,
                len(bootloader_config.supported_cairo_verifier_program_hashes),
                bootloader_config.supported_cairo_verifier_program_hashes,
                bootloader_config.applicative_bootloader_program_hash,
            ],
        )
    %}

    // The bootloader config appears at the beginning of the output.
    local bootloader_config_output_start: felt* = output_ptr;
    serialize_bootloader_config(bootloader_config=bootloader_config);

    // Increment output_ptr to save place for n_total_tasks.
    local output_n_total_tasks_ptr: felt* = output_ptr;
    let output_ptr = output_ptr + 1;
    %{ output_start = ids.output_ptr %}

    let simple_bootloader_output_ptr = simple_bootloader_output_start;

    // Skip n_subtasks in the simple bootloader output.
    let n_subtasks = [simple_bootloader_output_ptr];
    let simple_bootloader_output_ptr = simple_bootloader_output_ptr + 1;

    // Parse outputs recursively and write it to the output builtin.
    let n_total_tasks: felt = 0;
    %{ packed_outputs = bootloader_input.packed_outputs %}
    with simple_bootloader_output_ptr, n_total_tasks {
        parse_tasks{subtasks_output=simple_bootloader_output_ptr}(
            bootloader_config=bootloader_config,
            n_subtasks=n_subtasks,
            bootloader_config_output_start=bootloader_config_output_start,
            unpacking_mode=unpacking_mode,
        );
    }

    // Assert that parse_tasks used the entire output of the simple bootloader.
    let parse_tasks_end = simple_bootloader_output_ptr;
    assert simple_bootloader_output_end = parse_tasks_end;

    // Output the total number of tasks.
    assert [output_n_total_tasks_ptr] = n_total_tasks;

    return ();
}

// Unpacks composite packed outputs recursively and writes each task's plain output to the output
// builtin.
//
// Arguments:
// n_subtasks - Number of direct subtasks to unfold.
// bootloader_config.
// bootloader_config_output_start - A pointer to the start of the bootloader config in the output.
// unpacking_mode - The unpacking mode to use for composite packed tasks.
//
// Hint arguments:
// packed_outputs - PackedOutput object that stores the task tree structure.
//
// Implicit arguments:
// n_total_tasks - Number of PlainPackedOutput that were unpacked. This function increments this
// value for each unpacked output.
// subtasks_output - Contains direct subtasks outputs which is used for unpacking. This is an input
// to this function and is returned for validation purposes.
func parse_tasks{
    output_ptr: felt*,
    pedersen_ptr: HashBuiltin*,
    poseidon_ptr: PoseidonBuiltin*,
    range_check_ptr,
    n_total_tasks: felt,
    subtasks_output: felt*,
}(
    bootloader_config: BootloaderConfig*,
    n_subtasks: felt,
    bootloader_config_output_start: felt*,
    unpacking_mode: felt,
) {
    if (n_subtasks == 0) {
        return ();
    }

    ap += SIZEOF_LOCALS;

    %{
        from starkware.cairo.bootloaders.bootloader.objects import PackedOutput

        task_id = len(packed_outputs) - ids.n_subtasks
        packed_output: PackedOutput = packed_outputs[task_id]

        vm_enter_scope(new_scope_locals=dict(packed_output=packed_output))
    %}

    %{
        from starkware.cairo.bootloaders.bootloader.objects import (
            CompositePackedOutput,
            PlainPackedOutput,
        )
    %}

    if (nondet %{ isinstance(packed_output, PlainPackedOutput) %} != 0) {
        // Handle plain packed task.
        unpack_plain_packed_task{task_output=subtasks_output}(
            bootloader_config=bootloader_config,
            bootloader_config_output_start=bootloader_config_output_start,
        );
    } else {
        // Handle composite packed task.
        %{ assert isinstance(packed_output, CompositePackedOutput) %}
        unpack_composite_packed_task{task_output=subtasks_output}(
            bootloader_config=bootloader_config,
            bootloader_config_output_start=bootloader_config_output_start,
            unpacking_mode=unpacking_mode,
        );
    }

    %{ vm_exit_scope() %}

    // Call recursively for handling the other tasks.
    return parse_tasks(
        bootloader_config=bootloader_config,
        n_subtasks=n_subtasks - 1,
        bootloader_config_output_start=bootloader_config_output_start,
        unpacking_mode=unpacking_mode,
    );
}

// Serializes the bootloader config.
//
// Arguments:
// bootloader_config - A pointer to the bootloader config.
func serialize_bootloader_config{output_ptr: felt*, pedersen_ptr: HashBuiltin*}(
    bootloader_config: BootloaderConfig*
) {
    static_assert BOOTLOADER_CONFIG_SIZE == 3;
    // Compute the hash of the supported simple bootloader hash list.
    let (supported_simple_bootloader_hash_list_hash) = hash_felts{hash_ptr=pedersen_ptr}(
        data=bootloader_config.supported_simple_bootloader_hash_list,
        length=bootloader_config.supported_simple_bootloader_hash_list_len,
    );
    assert [output_ptr] = supported_simple_bootloader_hash_list_hash;
    assert [output_ptr + 1] = bootloader_config.applicative_bootloader_program_hash;

    // Compute the hash of the supported Cairo verifiers.
    let (supported_cairo_verifiers_hash) = hash_felts{hash_ptr=pedersen_ptr}(
        data=bootloader_config.supported_cairo_verifier_program_hashes,
        length=bootloader_config.supported_cairo_verifier_program_hashes_len,
    );
    assert [output_ptr + 2] = supported_cairo_verifiers_hash;
    let output_ptr = output_ptr + 3;
    return ();
}

// Parses the task header.
//
// Implicit arguments:
// task_output - A pointer to the output of the plain packed task. Assumes that task_output is of
// the following format: (task_header, output).
func parse_task_header{task_output: felt*}() -> (task_header: TaskOutputHeader*) {
    let task_header = cast(task_output, TaskOutputHeader*);
    let task_output = task_output + TaskOutputHeader.SIZE;
    return (task_header=task_header);
}

// Unpacks a composite packed task output using the Blake/Poseidon hash function.
//
// Arguments:
// expected_task_size - Used to verify the size of the task after parsing the
// CairoVerifierHashedOutput.
// unpacking_mode - The unpacking mode to use for composite packed tasks.
// Could be either BLAKE_UNPACKING or POSEIDON_UNPACKING, indicating which hash function to use
// when unpacking the task.
//
// Implicit arguments:
// range_check_ptr - Pointer to the range check builtin.
// task_output - A pointer to the output of the composite packed task. task_output should be of the
// following format:
// (simple_bootloader_program_hash, output_hash).
// poseidon_ptr - pointer to the poseidon builtin to use in the poseidon unpacking flow.
//
// Hint arguments:
// packed_output - CompositePackedOutput object which's used for unpacking the task.
func handle_unpacking_flow{task_output: felt*, range_check_ptr, poseidon_ptr: PoseidonBuiltin*}(
    expected_task_size: felt, unpacking_mode: felt
) -> (
    nested_subtasks_output: felt*,
    nested_subtasks_output_len: felt,
    nested_subtasks_program_hash: felt,
) {
    alloc_locals;
    // Guess the pre-image of subtasks_output_hash (subtasks_output_hash appears in task_output).
    local nested_subtasks_output_len: felt;
    local nested_subtasks_output: felt*;
    %{
        data = packed_output.elements_for_hash()
        ids.nested_subtasks_output_len = len(data)
        ids.nested_subtasks_output = segments.gen_arg(data)
    %}

    if (unpacking_mode == BLAKE_UNPACKING) {
        // Compute the Blake hash of nested_subtasks_output.
        let (subtasks_output_hash: felt) = encode_felt252_data_and_calc_blake_hash(
            data_len=nested_subtasks_output_len, data=nested_subtasks_output
        );
        tempvar range_check_ptr = range_check_ptr;
        tempvar poseidon_ptr = poseidon_ptr;
    } else {
        assert unpacking_mode = POSEIDON_UNPACKING;
        // Compute the Poseidon hash of nested_subtasks_output.
        let (subtasks_output_hash: felt) = poseidon_hash_many(
            n=nested_subtasks_output_len, elements=nested_subtasks_output
        );
        tempvar range_check_ptr = range_check_ptr;
        tempvar poseidon_ptr = poseidon_ptr;
    }

    // Verify task output header size. The output of the simple bootloader when running a verifier
    // program follows the following format:
    // [size, verifier_hash, verified_program_hash, output_hash],
    // where [verified_program_hash, output_hash] is the output of the verifier program.
    // We currently only verify runs of the simple bootloader, and so the above becomes:
    // [size, verifier_hash, simple_bootloader_hash, output_hash].
    assert expected_task_size = TaskOutputHeader.SIZE + CairoVerifierHashedOutput.SIZE;
    let cairo_verifier_hashed_output = cast(task_output, CairoVerifierHashedOutput*);

    // Verify task output hash.
    assert subtasks_output_hash = cairo_verifier_hashed_output.output_hash;

    let nested_subtasks_program_hash = cairo_verifier_hashed_output.program_hash;
    let task_output: felt* = &task_output[CairoVerifierHashedOutput.SIZE];
    return (
        nested_subtasks_output=nested_subtasks_output,
        nested_subtasks_output_len=nested_subtasks_output_len,
        nested_subtasks_program_hash=nested_subtasks_program_hash,
    );
}

// Unpacks a composite packed task output.
//
// Arguments:
// bootloader_config.
// bootloader_config_output_start - A pointer to the start of the bootloader config in the output.
// unpacking_mode - The unpacking mode to use for composite packed tasks.
//
// Implicit arguments:
// task_output - A pointer to the output of the composite packed task. task_output should be of the
// following format:
// (output_size, cairo_verifier_program_hash, simple_bootloader_program_hash, output_hash), where
// output_hash is hashed using the hash function indicated by unpacking_mode.
// n_total_tasks - Number of PlainPackedOutput that were unpacked.
//
// Hint arguments:
// packed_output - CompositePackedOutput object which uses for unpacking the task.
func unpack_composite_packed_task{
    output_ptr: felt*,
    pedersen_ptr: HashBuiltin*,
    poseidon_ptr: PoseidonBuiltin*,
    range_check_ptr,
    n_total_tasks: felt,
    task_output: felt*,
}(
    bootloader_config: BootloaderConfig*,
    bootloader_config_output_start: felt*,
    unpacking_mode: felt,
) {
    ap += SIZEOF_LOCALS;

    let (local task_header: TaskOutputHeader*) = parse_task_header();

    // Make sure the program hash is one of the supported verifier program hashes.
    find_element(
        array_ptr=bootloader_config.supported_cairo_verifier_program_hashes,
        elm_size=1,
        n_elms=bootloader_config.supported_cairo_verifier_program_hashes_len,
        key=task_header.program_hash,
    );

    // Handle the task's output based on the unpacking mode.
    let (
        nested_subtasks_output, nested_subtasks_output_len, nested_subtasks_program_hash
    ) = handle_unpacking_flow(expected_task_size=task_header.size, unpacking_mode=unpacking_mode);
    local task_output: felt* = task_output;

    // Verify the program hash of the nested subtasks.
    // Make sure the program hash of the task is one of the supported simple bootloader hashes.
    find_element(
        array_ptr=bootloader_config.supported_simple_bootloader_hash_list,
        elm_size=1,
        n_elms=bootloader_config.supported_simple_bootloader_hash_list_len,
        key=nested_subtasks_program_hash,
    );

    // Call recursively to parse the composite task's subtasks.
    local expected_nested_subtasks_output_after_consumption: felt* = nested_subtasks_output +
        nested_subtasks_output_len;
    let n_subtasks = [nested_subtasks_output];
    let nested_subtasks_output = nested_subtasks_output + 1;
    %{ packed_outputs = packed_output.subtasks %}
    with nested_subtasks_output {
        parse_tasks{subtasks_output=nested_subtasks_output}(
            bootloader_config=bootloader_config,
            n_subtasks=n_subtasks,
            bootloader_config_output_start=bootloader_config_output_start,
            unpacking_mode=unpacking_mode,
        );
    }

    // Assert that the entire subtask output was used.
    assert nested_subtasks_output = expected_nested_subtasks_output_after_consumption;
    return ();
}

// Unpacks a plain packed task output to the output builtin.
//
// Arguments:
// bootloader_config.
//
// Implicit arguments:
// task_output - A pointer to the output of the plain packed task. Assumes that task_output is of
// the following format: (output_len, cairo_verifier_program_hash, *output).
// n_total_tasks - Number of PlainPackedOutput that were unpacked. This function increments this
// value by 1.
func unpack_plain_packed_task{
    output_ptr: felt*,
    pedersen_ptr: HashBuiltin*,
    poseidon_ptr: PoseidonBuiltin*,
    range_check_ptr,
    n_total_tasks: felt,
    task_output: felt*,
}(bootloader_config: BootloaderConfig*, bootloader_config_output_start: felt*) {
    ap += SIZEOF_LOCALS;

    // Parse task output header.
    let (task_header: TaskOutputHeader*) = parse_task_header();

    local task_output: felt* = task_output;
    local updated_task_output_header: TaskOutputHeader;
    local task_output_offset: felt;
    if (task_header.program_hash == bootloader_config.applicative_bootloader_program_hash) {
        // Adjust the task output pointer to skip the bootloader config and the aggregator hash.
        assert task_output_offset = BOOTLOADER_CONFIG_SIZE + 1;

        // If the program is the applicative bootloader, adjust the header size to skip the
        // bootloader config and the aggregator hash. Also, output the modified aggregator hash
        // instead of the applicative bootloader hash.
        assert updated_task_output_header = TaskOutputHeader(
            size=task_header.size - task_output_offset, program_hash=task_output[0]
        );

        // Assert that the bootloader_config used by the applicative bootloader is correct.
        memcpy(dst=&task_output[1], src=bootloader_config_output_start, len=BOOTLOADER_CONFIG_SIZE);
    } else {
        // Otherwise, output the task as is.
        assert updated_task_output_header = [task_header];
        assert task_output_offset = 0;
    }

    // Output the task output header.
    assert [cast(output_ptr, TaskOutputHeader*)] = updated_task_output_header;
    let output_ptr = output_ptr + TaskOutputHeader.SIZE;

    // Copy the (actual) output to the bootloader output.
    let output_size = updated_task_output_header.size - TaskOutputHeader.SIZE;
    let task_output = task_output + task_output_offset;
    memcpy(dst=output_ptr, src=task_output, len=output_size);

    // Increment pointers.
    let output_ptr = output_ptr + output_size;
    let task_output = task_output + output_size;
    let n_total_tasks = n_total_tasks + 1;
    return ();
}
