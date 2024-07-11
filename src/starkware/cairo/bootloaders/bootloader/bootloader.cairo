%builtins output pedersen range_check ecdsa bitwise ec_op keccak poseidon range_check96 add_mod mul_mod

from starkware.cairo.bootloaders.bootloader.run_bootloader import run_bootloader
from starkware.cairo.common.cairo_builtins import HashBuiltin, PoseidonBuiltin
from starkware.cairo.common.registers import get_fp_and_pc

// Runs the simple bootloader on tasks and unpacks them to the output.
//
// Hint arguments:
// program_input - Contains the inputs for the bootloader.
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
    %{
        from starkware.cairo.bootloaders.bootloader.objects import BootloaderInput
        bootloader_input = BootloaderInput.Schema().load(program_input)
    %}

    // Execute bootloader.
    run_bootloader();

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
    return ();
}
