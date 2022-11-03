%builtins output pedersen range_check ecdsa bitwise ec_op keccak

from starkware.cairo.bootloaders.simple_bootloader.run_simple_bootloader import (
    run_simple_bootloader,
)
from starkware.cairo.common.cairo_builtins import HashBuiltin
from starkware.cairo.common.registers import get_fp_and_pc

func main{
    output_ptr: felt*,
    pedersen_ptr: HashBuiltin*,
    range_check_ptr,
    ecdsa_ptr,
    bitwise_ptr,
    ec_op_ptr,
    keccak_ptr,
}() {
    %{
        from starkware.cairo.bootloaders.simple_bootloader.objects import SimpleBootloaderInput
        simple_bootloader_input = SimpleBootloaderInput.Schema().load(program_input)
    %}

    // Execute tasks.
    run_simple_bootloader();

    %{
        # Dump fact topologies to a json file.
        from starkware.cairo.bootloaders.simple_bootloader.utils import (
            configure_fact_topologies,
            write_to_fact_topologies_file,
        )

        # The task-related output is prefixed by a single word that contains the number of tasks.
        tasks_output_start = output_builtin.base + 1

        if not simple_bootloader_input.single_page:
            # Configure the memory pages in the output builtin, based on fact_topologies.
            configure_fact_topologies(
                fact_topologies=fact_topologies, output_start=tasks_output_start,
                output_builtin=output_builtin,
            )

        if simple_bootloader_input.fact_topologies_path is not None:
            write_to_fact_topologies_file(
                fact_topologies_path=simple_bootloader_input.fact_topologies_path,
                fact_topologies=fact_topologies,
            )
    %}
    return ();
}
