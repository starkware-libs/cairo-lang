%builtins output pedersen range_check ecdsa bitwise

from starkware.cairo.bootloaders.simple_bootloader.run_simple_bootloader import (
    run_simple_bootloader,
)
from starkware.cairo.cairo_verifier.objects import CairoVerifierOutput
from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.hash_state import HashState, hash_finalize, hash_init, hash_update
from starkware.cairo.common.memcpy import memcpy

struct BootloaderConfig:
    # The hash of the simple bootloader program.
    member simple_bootloader_program_hash : felt
    # The hash of a (Cairo) program that verifies a STARK proof for the Cairo machine.
    member cairo_verifier_program_hash : felt
end

struct TaskOutputHeader:
    member size : felt
    member program_hash : felt
end

# Runs the simple bootloader on tasks and unpacks them to the output.
#
# Hint arguments:
# program_input - Contains the inputs for the bootloader.
func main{output_ptr : felt*, pedersen_ptr : HashBuiltin*, range_check_ptr, ecdsa_ptr, bitwise_ptr}(
    ):
    alloc_locals
    local simple_bootloader_output_start : felt*
    %{
        from starkware.cairo.bootloaders.bootloader.objects import BootloaderInput
        bootloader_input = BootloaderInput.Schema().load(program_input)

        ids.simple_bootloader_output_start = segments.add()

        # Change output builtin state to a different segment in preparation for calling the
        # simple bootloader.
        output_builtin_state = output_builtin.get_state()
        output_builtin.new_state(base=ids.simple_bootloader_output_start)
    %}

    # Save segment's start.
    let simple_bootloader_output_ptr : felt* = simple_bootloader_output_start

    # Call the simple bootloader program to execute direct subtasks. Simple bootloader input is
    # contained in the bootloader input.
    %{ simple_bootloader_input = bootloader_input %}
    run_simple_bootloader{output_ptr=simple_bootloader_output_ptr}()
    let simple_bootloader_output_end : felt* = simple_bootloader_output_ptr

    %{
        # Restore the bootloader's output builtin state.
        output_builtin.set_state(output_builtin_state)
    %}

    # The bootloader config appears at the beginning of the output.
    let bootloader_config = cast(output_ptr, BootloaderConfig*)
    let output_ptr = output_ptr + BootloaderConfig.SIZE

    %{
        segments.write_arg(
            ids.bootloader_config.address_,
            [
                bootloader_input.simple_bootloader_program_hash,
                bootloader_input.cairo_verifier_program_hash,
            ],
        )
    %}

    # Increment output_ptr to save place for n_total_tasks.
    let output_n_total_tasks = [output_ptr]
    let output_ptr = output_ptr + 1
    %{ output_start = ids.output_ptr %}

    let simple_bootloader_output_ptr = simple_bootloader_output_start

    # Skip n_subtasks in the simple bootloader output.
    let n_subtasks = [simple_bootloader_output_ptr]
    let simple_bootloader_output_ptr = simple_bootloader_output_ptr + 1

    # Parse outputs recursively and write it to the output builtin.
    let n_total_tasks : felt = 0
    %{ packed_outputs = bootloader_input.packed_outputs %}
    with simple_bootloader_output_ptr, n_total_tasks:
        parse_tasks{subtasks_output=simple_bootloader_output_ptr}(
            bootloader_config=bootloader_config, n_subtasks=n_subtasks
        )
    end

    # Assert that parse_tasks used the entire output of the simple bootloader.
    let parse_tasks_end = simple_bootloader_output_ptr
    assert simple_bootloader_output_end = parse_tasks_end

    # Output the total number of tasks.
    assert output_n_total_tasks = n_total_tasks

    %{
        from typing import List

        from starkware.cairo.bootloaders.bootloader.utils import compute_fact_topologies
        from starkware.cairo.bootloaders.fact_topology import FactTopology
        from starkware.cairo.bootloaders.simple_bootloader.utils import (
            configure_fact_topologies,
            write_to_fact_topologies_file,
        )

        # Compute the fact topologies of the plain packed outputs based on packed_outputs and
        # fact_topologies of the inner tasks.
        plain_fact_topologies: List[FactTopology] = compute_fact_topologies(
            packed_outputs=packed_outputs, fact_topologies=fact_topologies,
        )

        # Configure the memory pages in the output builtin, based on plain_fact_topologies.
        configure_fact_topologies(
            fact_topologies=plain_fact_topologies, output_start=output_start,
            output_builtin=output_builtin,
        )

        # Dump fact topologies to a json file.
        if bootloader_input.fact_topologies_path is not None:
            write_to_fact_topologies_file(
                fact_topologies_path=bootloader_input.fact_topologies_path,
                fact_topologies=plain_fact_topologies,
            )
    %}
    return ()
end

# Unpacks composite packed outputs recursively and writes each task's plain output to the output
# builtin.
#
# Arguments:
# n_subtasks - Number of direct subtasks to unfold.
# bootloader_config.
#
# Hint arguments:
# packed_outputs - PackedOutput object that stores the task tree structure.
#
# Implicit arguments:
# n_total_tasks - Number of PlainPackedOutput that were unpacked. This function increments this
# value for each unpacked output.
# subtasks_output - Contains direct subtasks outputs which is used for unpacking. This is an input
# to this function and is returned for validation purposes.
func parse_tasks{
    output_ptr : felt*, pedersen_ptr : HashBuiltin*, n_total_tasks : felt, subtasks_output : felt*
}(bootloader_config : BootloaderConfig*, n_subtasks : felt):
    if n_subtasks == 0:
        return ()
    end

    alloc_locals

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

    if nondet %{ isinstance(packed_output, PlainPackedOutput) %} != 0:
        # Handle plain packed task.
        unpack_plain_packed_task{task_output=subtasks_output}(bootloader_config=bootloader_config)
    else:
        # Handle composite packed task.
        %{ assert isinstance(packed_output, CompositePackedOutput) %}
        unpack_composite_packed_task{task_output=subtasks_output}(
            bootloader_config=bootloader_config
        )
    end

    %{ vm_exit_scope() %}

    # Call recursively for handling the other tasks.
    return parse_tasks(bootloader_config=bootloader_config, n_subtasks=n_subtasks - 1)
end

# Parses the task header.
#
# Implicit arguments:
# task_output - A pointer to the output of the plain packed task. Assumes that task_output is of
# the following format: (task_header, output).
func parse_task_header{task_output : felt*}() -> (task_header : TaskOutputHeader*):
    let task_header = cast(task_output, TaskOutputHeader*)
    let task_output = task_output + TaskOutputHeader.SIZE
    return (task_header=task_header)
end

# Unpacks a composite packed task output.
#
# Arguments:
# bootloader_config.
#
# Implicit arguments:
# task_output - A pointer to the output of the composite packed task. task_output should be of the
# following format:
# (output_len, cairo_verifier_program_hash, simple_bootloader_program_hash, output_hash).
# n_total_tasks - Number of PlainPackedOutput that were unpacked.
#
# Hint arguments:
# packed_output - CompositePackedOutput object which uses for unpacking the task.
func unpack_composite_packed_task{
    output_ptr : felt*, pedersen_ptr : HashBuiltin*, n_total_tasks : felt, task_output : felt*
}(bootloader_config : BootloaderConfig*):
    alloc_locals

    # Guess the pre-image of subtasks_output_hash (subtasks_output_hash appears in task_output).
    local nested_subtasks_output : felt*
    local nested_subtasks_output_len
    %{
        data = packed_output.elements_for_hash()
        ids.nested_subtasks_output_len = len(data)
        ids.nested_subtasks_output = segments.gen_arg(data)
    %}

    # Compute the hash of nested_subtasks_output.
    let (hash_state_ptr : HashState*) = hash_init()
    let (hash_state_ptr) = hash_update{hash_ptr=pedersen_ptr}(
        hash_state_ptr=hash_state_ptr,
        data_ptr=nested_subtasks_output,
        data_length=nested_subtasks_output_len,
    )
    let (subtasks_output_hash) = hash_finalize{hash_ptr=pedersen_ptr}(hash_state_ptr=hash_state_ptr)

    # Verify task output header.
    let (task_header : TaskOutputHeader*) = parse_task_header()
    assert [task_header] = TaskOutputHeader(
        size=TaskOutputHeader.SIZE + CairoVerifierOutput.SIZE,
        program_hash=bootloader_config.cairo_verifier_program_hash)

    # Verify task output.
    assert [cast(task_output, CairoVerifierOutput*)] = CairoVerifierOutput(
        program_hash=bootloader_config.simple_bootloader_program_hash,
        output_hash=subtasks_output_hash)
    let task_output = task_output + CairoVerifierOutput.SIZE

    # Call recursively to parse the composite task's subtasks.
    local nested_subtasks_output_start : felt* = nested_subtasks_output
    let n_subtasks = [nested_subtasks_output]
    let nested_subtasks_output = nested_subtasks_output + 1
    %{ packed_outputs = packed_output.subtasks %}
    with nested_subtasks_output:
        parse_tasks{subtasks_output=nested_subtasks_output}(
            bootloader_config=bootloader_config, n_subtasks=n_subtasks
        )
    end

    # Assert that the entire subtask output was used.
    assert nested_subtasks_output = nested_subtasks_output_start + nested_subtasks_output_len
    return ()
end

# Unpacks a plain packed task output to the output builtin.
#
# Arguments:
# bootloader_config.
#
# Implicit arguments:
# task_output - A pointer to the output of the plain packed task. Assumes that task_output is of
# the following format: (output_len, cairo_verifier_program_hash, *output).
# n_total_tasks - Number of PlainPackedOutput that were unpacked. This function increments this
# value by 1.
func unpack_plain_packed_task{
    output_ptr : felt*, pedersen_ptr : HashBuiltin*, n_total_tasks : felt, task_output : felt*
}(bootloader_config : BootloaderConfig*):
    alloc_locals

    # Parse task output header.
    let (task_header : TaskOutputHeader*) = parse_task_header()

    # Copy the simple bootloader output header to the bootloader output.
    assert [cast(output_ptr, TaskOutputHeader*)] = [task_header]

    # Increment output pointer.
    let output_ptr = output_ptr + TaskOutputHeader.SIZE

    # Copy the program output to the bootloader output.
    let output_size = task_header.size - TaskOutputHeader.SIZE
    memcpy(dst=output_ptr, src=task_output, len=output_size)

    # Increment pointers.
    let output_ptr = output_ptr + output_size
    let task_output = task_output + output_size
    let n_total_tasks = n_total_tasks + 1
    return ()
end
