from starkware.cairo.bootloaders.simple_bootloader.execute_task import BuiltinData, execute_task
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.registers import get_fp_and_pc

# Loads the programs and executes them.
#
# Hint Arguments:
# simple_bootloader_input - contains the tasks to execute.
#
# Returns:
# Updated builtin pointers after executing all programs.
# fact_topologies - that corresponds to the tasks (hint variable).
func run_simple_bootloader{
    output_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr, bitwise_ptr
}():
    alloc_locals
    local task_range_check_ptr

    %{
        n_tasks = len(simple_bootloader_input.tasks)
        memory[ids.output_ptr] = n_tasks

        # Task range checks are located right after simple bootloader validation range checks, and
        # this is validated later in this function.
        ids.task_range_check_ptr = ids.range_check_ptr + ids.BuiltinData.SIZE * n_tasks

        # A list of fact_tooplogies that instruct how to generate the fact from the program output
        # for each task.
        fact_topologies = []
    %}

    let n_tasks = [output_ptr]
    let output_ptr = output_ptr + 1

    # A struct containing the pointer to each builtin.
    local builtin_ptrs_before : BuiltinData = BuiltinData(
        output=cast(output_ptr, felt),
        pedersen=cast(pedersen_ptr, felt),
        range_check=task_range_check_ptr,
        ecdsa=ecdsa_ptr,
        bitwise=bitwise_ptr)

    # A struct containing the encoding of each builtin.
    local builtin_encodings : BuiltinData = BuiltinData(
        output='output',
        pedersen='pedersen',
        range_check='range_check',
        ecdsa='ecdsa',
        bitwise='bitwise')

    local builtin_instance_sizes : BuiltinData = BuiltinData(
        output=1, pedersen=3, range_check=1, ecdsa=2, bitwise=5)

    # Call execute_tasks.
    let (__fp__, _) = get_fp_and_pc()

    %{ tasks = simple_bootloader_input.tasks %}
    let builtin_ptrs = &builtin_ptrs_before
    let self_range_check_ptr = range_check_ptr
    with builtin_ptrs, self_range_check_ptr:
        execute_tasks(
            builtin_encodings=&builtin_encodings,
            builtin_instance_sizes=&builtin_instance_sizes,
            n_tasks=n_tasks,
        )
    end

    # Verify that the task range checks appear after the self range checks of execute_task.
    assert self_range_check_ptr = task_range_check_ptr

    # Return the updated builtin pointers.
    local builtin_ptrs : BuiltinData* = builtin_ptrs
    let output_ptr = cast(builtin_ptrs.output, felt*)
    let pedersen_ptr = cast(builtin_ptrs.pedersen, HashBuiltin*)
    let range_check_ptr = builtin_ptrs.range_check
    let ecdsa_ptr = builtin_ptrs.ecdsa
    let bitwise_ptr = builtin_ptrs.bitwise

    # Verify that range_check has indeed advanced.
    let additional_range_checks = range_check_ptr - self_range_check_ptr
    verify_non_negative(num=additional_range_checks, n_bits=64)

    return ()
end

# Verifies that a field element is in the range [0, 2^n_bits), without relying on the range_check
# builtin.
func verify_non_negative(num : felt, n_bits : felt):
    if n_bits == 0:
        assert num = 0
        return ()
    end

    tempvar num_div2 = nondet %{ ids.num // 2 %}
    tempvar bit = num - (num_div2 + num_div2)
    # Check that bit is 0 or 1.
    assert bit = bit * bit
    return verify_non_negative(num=num_div2, n_bits=n_bits - 1)
end

# Executes the last n_tasks from simple_bootloader_input.tasks.
#
# Arguments:
# builtin_encodings - String encodings of the builtins.
# builtin_instance_sizes - Mapping to builtin sizes.
# n_tasks - The number of tasks to execute.
#
# Implicit arguments:
# builtin_ptrs - Pointer to the builtin pointers before/after executing the tasks.
# self_range_check_ptr - range_check pointer (used for validating the builtins).
#
# Hint arguments:
# tasks - A list of tasks to execute.
func execute_tasks{builtin_ptrs : BuiltinData*, self_range_check_ptr}(
    builtin_encodings : BuiltinData*, builtin_instance_sizes : BuiltinData*, n_tasks
):
    if n_tasks == 0:
        return ()
    end

    %{
        from starkware.cairo.bootloaders.simple_bootloader.objects import Task

        # Pass current task to execute_task.
        task_id = len(simple_bootloader_input.tasks) - ids.n_tasks
        task = simple_bootloader_input.tasks[task_id].load_task()
    %}
    # Call execute_task to execute the current task.
    execute_task(builtin_encodings=builtin_encodings, builtin_instance_sizes=builtin_instance_sizes)

    return execute_tasks(
        builtin_encodings=builtin_encodings,
        builtin_instance_sizes=builtin_instance_sizes,
        n_tasks=n_tasks - 1,
    )
end
