%builtins output pedersen range_check ecdsa bitwise ec_op keccak poseidon range_check96 add_mod mul_mod

from starkware.cairo.bootloaders.bootloader.run_bootloader import run_bootloader
from starkware.cairo.bootloaders.simple_bootloader.run_simple_bootloader import (
    run_simple_bootloader,
    verify_non_negative,
)
from starkware.cairo.common.cairo_builtins import HashBuiltin, PoseidonBuiltin
from starkware.cairo.common.hash import hash2
from starkware.cairo.common.memcpy import memcpy
from starkware.cairo.common.registers import get_fp_and_pc

const AGGREGATOR_CONSTANT = 'AGGREGATOR';

func main{
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
    ap += SIZEOF_LOCALS;
    local task_range_check_ptr;

    // A pointer to the aggregator's task output.
    local aggregator_output_ptr: felt*;
    %{
        from starkware.cairo.bootloaders.applicative_bootloader.objects import (
            ApplicativeBootloaderInput,
        )
        from starkware.cairo.bootloaders.simple_bootloader.objects import SimpleBootloaderInput

        # Create a segment for the aggregator output.
        ids.aggregator_output_ptr = segments.add()

        # Load the applicative bootloader input and the aggregator task.
        applicative_bootloader_input = ApplicativeBootloaderInput.Schema().load(program_input)
        aggregator_task = applicative_bootloader_input.aggregator_task.load_task()

        # Create the simple bootloader input.
        simple_bootloader_input = SimpleBootloaderInput(
            tasks=[aggregator_task], fact_topologies_path=None, single_page=False
        )

        # Change output builtin state to a different segment in preparation for running the
        # aggregator task.
        applicative_output_builtin_state = output_builtin.get_state()
        output_builtin.new_state(base=ids.aggregator_output_ptr)
    %}

    // Save aggregator output start.
    let aggregator_output_start: felt* = aggregator_output_ptr;

    // Execute the simple bootloader with the aggregator task.
    run_simple_bootloader{output_ptr=aggregator_output_ptr}();
    local aggregator_output_end: felt* = aggregator_output_ptr;

    // Check that exactly one task was executed.
    assert aggregator_output_start[0] = 1;

    // Extract the aggregator output size and program hash.
    let aggregator_output_length = aggregator_output_start[1];
    assert aggregator_output_length = aggregator_output_end - aggregator_output_start - 1;
    let aggregator_program_hash = aggregator_output_start[2];
    let aggregator_input_ptr = &aggregator_output_start[3];

    // Allocate a segment for the bootloader output.
    local bootloader_output_ptr: felt*;
    %{
        from starkware.cairo.bootloaders.bootloader.objects import BootloaderInput

        # Save the aggregator's fact_topologies before running the bootloader.
        aggregator_fact_topologies = fact_topologies
        fact_topologies = []

        # Create a segment for the bootloader output.
        ids.bootloader_output_ptr = segments.add()

        # Create the bootloader input.
        bootloader_input = BootloaderInput(
            tasks=applicative_bootloader_input.tasks,
            fact_topologies_path=None,
            bootloader_config=applicative_bootloader_input.bootloader_config,
            packed_outputs=applicative_bootloader_input.packed_outputs,
            single_page=True,
        )

        # Change output builtin state to a different segment in preparation for running the
        # bootloader.
        output_builtin.new_state(base=ids.bootloader_output_ptr)
    %}

    // Save the bootloader output start.
    let bootloader_output_start = bootloader_output_ptr;

    // Execute the bootloader.
    run_bootloader{output_ptr=bootloader_output_ptr}();
    local range_check_ptr = range_check_ptr;
    local ecdsa_ptr = ecdsa_ptr;
    local bitwise_ptr = bitwise_ptr;
    local ec_op_ptr = ec_op_ptr;
    local keccak_ptr = keccak_ptr;
    local pedersen_ptr: HashBuiltin* = pedersen_ptr;
    local poseidon_ptr: PoseidonBuiltin* = poseidon_ptr;
    local range_check96_ptr = range_check96_ptr;
    local add_mod_ptr = add_mod_ptr;
    local mul_mod_ptr = mul_mod_ptr;
    local bootloader_output_end: felt* = bootloader_output_ptr;

    %{
        # Restore the output builtin state.
        output_builtin.set_state(applicative_output_builtin_state)
    %}

    // Output:
    // * The aggregator program hash, hashed with the word "AGGREGATOR".
    // * The bootloader config: the simple bootloader hash and the hash of the list of the Cairo
    //   verifiers.
    let (modified_aggregator_program_hash) = hash2{hash_ptr=pedersen_ptr}(
        AGGREGATOR_CONSTANT, aggregator_program_hash
    );
    local pedersen_ptr: HashBuiltin* = pedersen_ptr;
    assert output_ptr[0] = modified_aggregator_program_hash;
    // Copy the bootloader config.
    assert output_ptr[1] = bootloader_output_start[0];
    assert output_ptr[2] = bootloader_output_start[1];
    let output_ptr = &output_ptr[3];
    let output_start = output_ptr;

    // Assert that the bootloader output agrees with the aggregator input.
    let bootloader_tasks_output_ptr = &bootloader_output_start[2];
    let bootloader_tasks_output_length = bootloader_output_end - bootloader_tasks_output_ptr;
    memcpy(
        dst=aggregator_input_ptr,
        src=bootloader_tasks_output_ptr,
        len=bootloader_tasks_output_length,
    );

    // Output the aggregated output.
    let aggregated_output_ptr = aggregator_input_ptr + bootloader_tasks_output_length;
    let aggregated_output_length = aggregator_output_end - aggregated_output_ptr;
    memcpy(dst=output_ptr, src=aggregated_output_ptr, len=aggregated_output_length);
    let output_ptr = output_ptr + aggregated_output_length;

    %{
        from starkware.cairo.bootloaders.fact_topology import FactTopology
        from starkware.cairo.bootloaders.simple_bootloader.utils import (
            configure_fact_topologies,
            write_to_fact_topologies_file,
        )

        assert len(aggregator_fact_topologies) == 1
        # Subtract the bootloader output length from the first page's length. Note that the
        # bootloader output is always fully contained in the first page.
        original_first_page_length = aggregator_fact_topologies[0].page_sizes[0]
        first_page_length = original_first_page_length - ids.bootloader_tasks_output_length

        # Update the first page's length to account for the bootloader output.
        fact_topology = FactTopology(
            tree_structure=aggregator_fact_topologies[0].tree_structure,
            page_sizes=[first_page_length] + aggregator_fact_topologies[0].page_sizes[1:]
        )

        # Configure the memory pages in the output builtin, based on plain_fact_topologies.
        configure_fact_topologies(
            fact_topologies=[fact_topology], output_start=ids.output_start,
            output_builtin=output_builtin,
        )

        # Dump fact topologies to a json file.
        if applicative_bootloader_input.fact_topologies_path is not None:
            write_to_fact_topologies_file(
                fact_topologies_path=applicative_bootloader_input.fact_topologies_path,
                fact_topologies=[fact_topology],
            )
    %}

    return ();
}
