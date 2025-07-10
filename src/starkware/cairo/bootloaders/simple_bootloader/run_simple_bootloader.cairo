from starkware.cairo.bootloaders.simple_bootloader.execute_task import (
    BuiltinData,
    PrevProgramTaskParams,
    execute_task,
)
from starkware.cairo.common.cairo_builtins import HashBuiltin, PoseidonBuiltin
from starkware.cairo.common.registers import get_fp_and_pc
from starkware.cairo.common.segments import relocate_segment

// Loads the given tasks and executes them.
// Outputs the program hashes of the tasks, and their outputs.
//
// Hint Arguments:
// simple_bootloader_input - contains the tasks to execute.
//
// Returns (written to output_ptr):
// - The number of tasks executed.
// - For each task:
//   - Size.
//   - Program hash.
//   - The output of the program (of length=Size-2).
//
// Furthermore, returns:
// Updated builtin pointers after executing all programs.
// fact_topologies - that corresponds to the tasks (hint variable).
func run_simple_bootloader{
    output_ptr: felt*,
    pedersen_ptr: HashBuiltin*,
    range_check_ptr,
    ecdsa_ptr,
    bitwise_ptr,
    ec_op_ptr,
    keccak_ptr,
    poseidon_ptr: PoseidonBuiltin*,
    range_check96_ptr,
    add_mod_ptr,
    mul_mod_ptr,
}() {
    alloc_locals;

    local initial_subtasks_range_check_ptr;

    // The following hint is used to:
    // 1. Write the number of tasks into `output_ptr[0]`.
    // 2. Set `initial_subtasks_range_check_ptr` to a new temporary segment.
    // 3. Initialize the `fact_topologies` hint variable to an empty array.
    %{ SETUP_RUN_SIMPLE_BOOTLOADER_BEFORE_TASK_EXECUTION %}

    let n_tasks = [output_ptr];
    let output_ptr = output_ptr + 1;

    // A struct containing the pointer to each builtin.
    local builtin_ptrs_before: BuiltinData = BuiltinData(
        output=cast(output_ptr, felt),
        pedersen=cast(pedersen_ptr, felt),
        range_check=initial_subtasks_range_check_ptr,
        ecdsa=ecdsa_ptr,
        bitwise=bitwise_ptr,
        ec_op=ec_op_ptr,
        keccak=keccak_ptr,
        poseidon=cast(poseidon_ptr, felt),
        range_check96=range_check96_ptr,
        add_mod=add_mod_ptr,
        mul_mod=mul_mod_ptr,
    );

    // A struct containing the encoding of each builtin.
    local builtin_encodings: BuiltinData = BuiltinData(
        output='output',
        pedersen='pedersen',
        range_check='range_check',
        ecdsa='ecdsa',
        bitwise='bitwise',
        ec_op='ec_op',
        keccak='keccak',
        poseidon='poseidon',
        range_check96='range_check96',
        add_mod='add_mod',
        mul_mod='mul_mod',
    );

    local builtin_instance_sizes: BuiltinData = BuiltinData(
        output=1,
        pedersen=3,
        range_check=1,
        ecdsa=2,
        bitwise=5,
        ec_op=7,
        keccak=16,
        poseidon=6,
        range_check96=1,
        add_mod=7,
        mul_mod=7,
    );

    // Call execute_tasks.
    let (__fp__, _) = get_fp_and_pc();

    %{ tasks = simple_bootloader_input.tasks %}
    let builtin_ptrs = &builtin_ptrs_before;
    let self_range_check_ptr = range_check_ptr;
    // The first prev task is a dummy task as we don't have a previous task to compare to.
    tempvar prev_program_task_params = new PrevProgramTaskParams(
        prev_hash=0, prev_program_segment_ptr=cast(0, felt*), prev_program_hash_function=-1
    );
    with builtin_ptrs, self_range_check_ptr, prev_program_task_params {
        execute_tasks(
            builtin_encodings=&builtin_encodings,
            builtin_instance_sizes=&builtin_instance_sizes,
            n_tasks=n_tasks,
        );
    }

    // Relocate the range checks used by the subtasks after the range checks used by the bootloader.
    relocate_segment(
        src_ptr=cast(initial_subtasks_range_check_ptr, felt*),
        dest_ptr=cast(self_range_check_ptr, felt*),
    );

    // Return the updated builtin pointers.
    local builtin_ptrs: BuiltinData* = builtin_ptrs;
    let output_ptr = cast(builtin_ptrs.output, felt*);
    let pedersen_ptr = cast(builtin_ptrs.pedersen, HashBuiltin*);
    let range_check_ptr = builtin_ptrs.range_check;
    let ecdsa_ptr = builtin_ptrs.ecdsa;
    let bitwise_ptr = builtin_ptrs.bitwise;
    let ec_op_ptr = builtin_ptrs.ec_op;
    let keccak_ptr = builtin_ptrs.keccak;
    let poseidon_ptr = cast(builtin_ptrs.poseidon, PoseidonBuiltin*);
    let range_check96_ptr = builtin_ptrs.range_check96;
    let add_mod_ptr = builtin_ptrs.add_mod;
    let mul_mod_ptr = builtin_ptrs.mul_mod;

    // 'execute_tasks' runs untrusted code and uses the range_check builtin to verify that
    // the builtin pointers were advanced correctly by said code.
    // Since range_check itself is used for the verification, we cannot assume that the verification
    // above is sound unless we know that the self range checks that were used during verification
    // are indeed valid (that is, within the segment of the range_check builtin).
    // Following the Cairo calling convention, we can guarantee the validity of the self range
    // checks by making sure that range_check_ptr >= self_range_check_ptr.
    // The following check validates that the inequality above holds without using the range check
    // builtin.
    let additional_range_checks = range_check_ptr - self_range_check_ptr;
    verify_non_negative(num=additional_range_checks, n_bits=64);

    return ();
}

// Verifies that a field element is in the range [0, 2^n_bits), without relying on the range_check
// builtin.
func verify_non_negative(num: felt, n_bits: felt) {
    if (n_bits == 0) {
        assert num = 0;
        return ();
    }

    tempvar num_div2 = nondet %{ ids.num // 2 %};
    tempvar bit = num - (num_div2 + num_div2);
    // Check that bit is 0 or 1.
    assert bit = bit * bit;
    return verify_non_negative(num=num_div2, n_bits=n_bits - 1);
}

// Executes the last n_tasks from simple_bootloader_input.tasks.
//
// Arguments:
// builtin_encodings - String encodings of the builtins.
// builtin_instance_sizes - Mapping to builtin sizes.
// n_tasks - The number of tasks to execute.
//
// Implicit arguments:
// builtin_ptrs - Pointer to the builtin pointers before/after executing the tasks.
// self_range_check_ptr - range_check pointer (used for validating the builtins).
// prev_program_task_params - The parameters of the previous program task. Used for
//   optimization by reusing the previous task's hash and segment if the current
//   task is identical to the previous one.
//
// Hint arguments:
// tasks - A list of tasks to execute.
func execute_tasks{
    builtin_ptrs: BuiltinData*,
    self_range_check_ptr,
    prev_program_task_params: PrevProgramTaskParams*,
}(builtin_encodings: BuiltinData*, builtin_instance_sizes: BuiltinData*, n_tasks: felt) {
    if (n_tasks == 0) {
        return ();
    }

    %{ SIMPLE_BOOTLOADER_SET_CURRENT_TASK %}
    tempvar program_hash_function = nondet %{ task.program_hash_function %};
    // Call execute_task to execute the current task.
    execute_task(
        builtin_encodings=builtin_encodings,
        builtin_instance_sizes=builtin_instance_sizes,
        program_hash_function=program_hash_function,
    );

    return execute_tasks(
        builtin_encodings=builtin_encodings,
        builtin_instance_sizes=builtin_instance_sizes,
        n_tasks=n_tasks - 1,
    );
}
