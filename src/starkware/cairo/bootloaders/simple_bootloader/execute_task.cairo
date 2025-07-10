from starkware.cairo.builtin_selection.inner_select_builtins import inner_select_builtins
from starkware.cairo.builtin_selection.select_input_builtins import select_input_builtins
from starkware.cairo.builtin_selection.validate_builtins import validate_builtins
from starkware.cairo.common.builtin_poseidon.poseidon import PoseidonBuiltin, poseidon_hash_many
from starkware.cairo.common.cairo_blake2s.blake2s import encode_felt252_data_and_calc_blake_hash
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.hash_chain import hash_chain
from starkware.cairo.common.math import assert_not_nullptr
from starkware.cairo.common.registers import get_ap, get_fp_and_pc

const BOOTLOADER_VERSION = 0;

const PEDERSEN_HASH = 0;
const POSEIDON_HASH = 1;
const BLAKE_HASH = 2;

// This struct contains the previous task hash, segment and hash function.
// It is used to optimize the execution of the tasks by reusing the previous task's hash and segment
// if the current task is identical to the previous one.
struct PrevProgramTaskParams {
    prev_hash: felt,
    prev_program_segment_ptr: felt*,
    prev_program_hash_function: felt,
}

// Use an empty struct to encode an arbitrary-length array.
struct BuiltinList {
}

struct ProgramHeader {
    // The data length field specifies the length of the data (i.e., program header + program)
    // and guarantees unique decoding of the program hash.
    data_length: felt,
    bootloader_version: felt,
    program_main: felt,
    n_builtins: felt,
    // 'builtin_list' is a continuous memory segment containing the ASCII encoding of the (ordered)
    // builtins used by the program.
    builtin_list: BuiltinList,
}

struct BuiltinData {
    output: felt,
    pedersen: felt,
    range_check: felt,
    ecdsa: felt,
    bitwise: felt,
    ec_op: felt,
    keccak: felt,
    poseidon: felt,
    range_check96: felt,
    add_mod: felt,
    mul_mod: felt,
}

// Computes the hash of a program.
// Arguments:
//  * program_segment_ptr - the pointer to the program to be hashed.
//  * program_hash_function - determines which hash function is to be used.
// Return values:
//  * hash - the computed program hash.
func compute_program_hash{
    pedersen_ptr: HashBuiltin*, poseidon_ptr: PoseidonBuiltin*, self_range_check_ptr: felt
}(program_segment_ptr: felt*, program_hash_function: felt) -> (hash: felt) {
    if (program_hash_function == BLAKE_HASH) {
        let (hash) = encode_felt252_data_and_calc_blake_hash{range_check_ptr=self_range_check_ptr}(
            data_len=program_segment_ptr[0], data=&program_segment_ptr[1]
        );
        return (hash=hash);
    }
    if (program_hash_function == PEDERSEN_HASH) {
        let (hash) = hash_chain{hash_ptr=pedersen_ptr}(data_ptr=program_segment_ptr);
        return (hash=hash);
    }
    assert program_hash_function = POSEIDON_HASH;
    let (hash) = poseidon_hash_many{poseidon_ptr=poseidon_ptr}(
        n=program_segment_ptr[0], elements=&program_segment_ptr[1]
    );
    return (hash=hash);
}

// Loads the program header and calculates the program hash.
// Arguments:
//  * program_hash_function - determines the hashing type.
// Return values:
//  * program_hash - the computed program hash.
//  * program_segment_ptr - the pointer to the program segment.
func load_program_segment{
    pedersen_ptr: HashBuiltin*,
    poseidon_ptr: PoseidonBuiltin*,
    self_range_check_ptr: felt,
    prev_program_task_params: PrevProgramTaskParams*,
}(program_hash_function: felt) -> (program_hash: felt, program_segment_ptr: felt*) {
    // Allocate memory for local variables.
    alloc_locals;

    local use_prev_hash: felt;

    %{ DETERMINE_USE_PREV_HASH %}

    if (use_prev_hash != 0) {
        assert program_hash_function = prev_program_task_params.prev_program_hash_function;
        assert_not_nullptr(prev_program_task_params.prev_program_segment_ptr);
        return (
            prev_program_task_params.prev_hash, prev_program_task_params.prev_program_segment_ptr
        );
    }

    local program_segment_ptr: felt*;
    let program_header = cast(program_segment_ptr, ProgramHeader*);

    %{ LOAD_PROGRAM_SEGMENT %}

    // Verify that the bootloader version is compatible with the bootloader.
    assert program_header.bootloader_version = BOOTLOADER_VERSION;

    // Call hash_chain, to verify the program hash.
    let (program_hash) = compute_program_hash(
        program_segment_ptr=program_segment_ptr, program_hash_function=program_hash_function
    );
    // Update `prev_program_task_params`.
    tempvar prev_program_task_params = new PrevProgramTaskParams(
        prev_hash=program_hash,
        prev_program_segment_ptr=program_segment_ptr,
        prev_program_hash_function=program_hash_function,
    );

    return (program_hash, program_segment_ptr);
}

// Executes a single task.
// The task is passed in the 'task' hint variable.
// Outputs of the task are prefixed by:
//   a. Output size (including this prefix)
//   b. hash_chain(ProgramHeader || task.program.data) where ProgramHeader is defined below.
// The function returns a pointer to the updated builtin pointers after executing the task.
// Hint argument: `vm_ecdsa_additional_data` - stores the signatures if the ecdsa builtin was
// used, but the ecdsa runner wasn't initialized.
func execute_task{
    builtin_ptrs: BuiltinData*,
    self_range_check_ptr: felt,
    prev_program_task_params: PrevProgramTaskParams*,
}(
    builtin_encodings: BuiltinData*,
    builtin_instance_sizes: BuiltinData*,
    program_hash_function: felt,
) {
    // Allocate memory for local variables.
    alloc_locals;

    // Load the builtin pointers for computing the program hash.
    let pedersen_ptr = cast(builtin_ptrs.pedersen, HashBuiltin*);
    let poseidon_ptr = cast(builtin_ptrs.poseidon, PoseidonBuiltin*);
    with pedersen_ptr, poseidon_ptr {
        // Load the program segment and compute the program hash.
        let (program_hash: felt, program_segment_ptr: felt*) = load_program_segment(
            program_hash_function=program_hash_function
        );
    }

    // Get the value of fp.
    let (local __fp__, _) = get_fp_and_pc();
    // The struct of input builtin pointers pointed by the given builtin_ptrs.
    local output_ptr = builtin_ptrs.output;

    // Write hash_chain result to output_ptr + 1.
    assert [output_ptr + 1] = program_hash;

    let program_header: ProgramHeader* = cast(program_segment_ptr, ProgramHeader*);

    // Set the program entry point, so the bootloader can later run the program.
    local builtin_list: felt* = &program_header.builtin_list;
    local n_builtins = program_header.n_builtins;
    tempvar program_address = builtin_list + n_builtins;
    %{
        # Sanity check.
        assert ids.program_address == program_address
    %}
    tempvar program_main = program_header.program_main;
    // The address in memory where the main function of the task is loaded.
    local program_entry_point: felt* = program_address + program_main;

    // Fill in all builtin pointers which may be used by the task.
    // Skip the 2 slots prefix that we add to the task output.
    local pre_execution_builtin_ptrs: BuiltinData = BuiltinData(
        output=output_ptr + 2,
        pedersen=cast(pedersen_ptr, felt),
        range_check=builtin_ptrs.range_check,
        ecdsa=builtin_ptrs.ecdsa,
        bitwise=builtin_ptrs.bitwise,
        ec_op=builtin_ptrs.ec_op,
        keccak=builtin_ptrs.keccak,
        poseidon=cast(poseidon_ptr, felt),
        range_check96=builtin_ptrs.range_check96,
        add_mod=builtin_ptrs.add_mod,
        mul_mod=builtin_ptrs.mul_mod,
    );

    // Call select_input_builtins to get the relevant input builtin pointers for the task.
    select_input_builtins(
        all_encodings=builtin_encodings,
        all_ptrs=&pre_execution_builtin_ptrs,
        n_all_builtins=BuiltinData.SIZE,
        selected_encodings=builtin_list,
        n_selected_builtins=n_builtins,
    );

    call_task:
    %{
        from starkware.cairo.bootloaders.simple_bootloader.objects import (
            CairoPieTask,
            RunProgramTask,
            Task,
        )
        from starkware.cairo.bootloaders.simple_bootloader.utils import (
            load_cairo_pie,
            prepare_output_runner,
        )

        assert isinstance(task, Task)
        n_builtins = len(task.get_program().builtins)
        new_task_locals = {}
        if isinstance(task, RunProgramTask):
            new_task_locals['program_input'] = task.program_input
            new_task_locals['WITH_BOOTLOADER'] = True

            vm_load_program(task.program, program_address)
        elif isinstance(task, CairoPieTask):
            ret_pc = ids.ret_pc_label.instruction_offset_ - ids.call_task.instruction_offset_ + pc
            load_cairo_pie(
                task=task.cairo_pie, memory=memory, segments=segments,
                program_address=program_address, execution_segment_address= ap - n_builtins,
                builtin_runners=builtin_runners, ret_fp=fp, ret_pc=ret_pc,
                ecdsa_additional_data=vm_ecdsa_additional_data)
        else:
            raise NotImplementedError(f'Unexpected task type: {type(task).__name__}.')

        output_runner_data = prepare_output_runner(
            task=task,
            output_builtin=output_builtin,
            output_ptr=ids.pre_execution_builtin_ptrs.output)
        vm_enter_scope(new_task_locals)
    %}

    // Call the inner program's main() function.
    call abs program_entry_point;

    ret_pc_label:
    %{
        vm_exit_scope()
        # Note that bootloader_input will only be available in the next hint.
    %}

    // Note that used_builtins_addr cannot be set in a hint because doing so will allow a malicious
    // prover to lie about the outputs of a valid program.
    let (ap_val) = get_ap();
    local used_builtins_addr: felt* = cast(ap_val - n_builtins, felt*);

    // Call inner_select_builtins to validate that the values of the builtin pointers for the next
    // task are updated according to the task return builtin pointers.

    // Allocate a struct containing all builtin pointers just after the program returns.
    local return_builtin_ptrs: BuiltinData;
    %{
        from starkware.cairo.bootloaders.simple_bootloader.utils import write_return_builtins

        # Fill the values of all builtin pointers after executing the task.
        builtins = task.get_program().builtins
        write_return_builtins(
            memory=memory, return_builtins_addr=ids.return_builtin_ptrs.address_,
            used_builtins=builtins, used_builtins_addr=ids.used_builtins_addr,
            pre_execution_builtins_addr=ids.pre_execution_builtin_ptrs.address_, task=task)

        vm_enter_scope({'n_selected_builtins': n_builtins})
    %}
    let select_builtins_ret = inner_select_builtins(
        all_encodings=builtin_encodings,
        all_ptrs=&return_builtin_ptrs,
        selected_encodings=builtin_list,
        selected_ptrs=used_builtins_addr,
        n_builtins=BuiltinData.SIZE,
    );
    %{ vm_exit_scope() %}

    // Assert that the correct number of builtins was selected.
    // Note that builtin_list is a pointer to the list containing the selected encodings.
    assert n_builtins = select_builtins_ret.selected_encodings_end - builtin_list;

    // Call validate_builtins to validate that the builtin pointers have advanced correctly.
    validate_builtins{range_check_ptr=self_range_check_ptr}(
        prev_builtin_ptrs=&pre_execution_builtin_ptrs,
        new_builtin_ptrs=&return_builtin_ptrs,
        builtin_instance_sizes=builtin_instance_sizes,
        n_builtins=BuiltinData.SIZE,
    );

    // Verify that [output_ptr] = return_builtin_ptrs.output - output_ptr.
    // Output size should be 2 + the number of output slots that were consumed by the task.
    local output_size = return_builtin_ptrs.output - output_ptr;
    assert [output_ptr] = output_size;

    %{
        from starkware.cairo.bootloaders.simple_bootloader.utils import get_task_fact_topology

        # Add the fact topology of the current task to 'fact_topologies'.
        output_start = ids.pre_execution_builtin_ptrs.output
        output_end = ids.return_builtin_ptrs.output
        fact_topologies.append(get_task_fact_topology(
            output_size=output_end - output_start,
            task=task,
            output_builtin=output_builtin,
            output_runner_data=output_runner_data,
        ))
    %}

    let builtin_ptrs = &return_builtin_ptrs;

    return ();
}
