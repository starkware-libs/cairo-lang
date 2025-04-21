%builtins output pedersen range_check ecdsa bitwise ec_op keccak poseidon range_check96 add_mod mul_mod

from starkware.cairo.bootloaders.simple_bootloader.run_simple_bootloader import (
    run_simple_bootloader,
)
from starkware.cairo.bootloaders.simple_bootloader.verify_builtins import (
    handle_ec_op_builtin_verification,
    handle_ecdsa_builtin_verification,
    handle_keccak_builtin_verification,
    handle_uninitialized_ec_op_builtin,
    handle_uninitialized_ecdsa_builtin,
    handle_uninitialized_keccak_builtin,
)
from starkware.cairo.common.cairo_builtins import HashBuiltin, PoseidonBuiltin
from starkware.cairo.common.registers import get_fp_and_pc

// For documentation of the simple bootloader, see the docstring of `run_simple_bootloader'.
// Hint arguments:
// program_input - contains the tasks to execute. Formatted as a SimpleBootloaderInput object.
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
    alloc_locals;
    %{
        from starkware.cairo.bootloaders.simple_bootloader.objects import SimpleBootloaderInput
        simple_bootloader_input = SimpleBootloaderInput.Schema().load(program_input)
    %}

    // Handle ec_op builtin. See docstring of `handle_uninitialized_ec_op_builtin` for more info.
    local ec_op_ptr_orig = ec_op_ptr;
    let (local ec_op_ptr) = handle_uninitialized_ec_op_builtin(ec_op_ptr=ec_op_ptr);
    local ec_op_start_ptr = ec_op_ptr;

    // Handle keccak builtin. See docstring of `handle_uninitialized_keccak_builtin` for more info.
    local keccak_ptr_orig = keccak_ptr;
    let (local keccak_ptr) = handle_uninitialized_keccak_builtin(keccak_ptr=keccak_ptr);
    local keccak_start_ptr = keccak_ptr;

    // Handle ecdsa builtin. See docstring of `handle_uninitialized_ecdsa_builtin` for more info.
    local ecdsa_ptr_orig = ecdsa_ptr;
    let (local ecdsa_ptr) = handle_uninitialized_ecdsa_builtin(ecdsa_ptr=ecdsa_ptr);
    local ecdsa_start_ptr = ecdsa_ptr;

    // Execute tasks.
    run_simple_bootloader();

    // Verify the ec_op builtin. See docstring of `handle_ec_op_builtin_verification` for more info.
    let (local ec_op_ptr) = handle_ec_op_builtin_verification(
        ec_op_ptr=ec_op_ptr, ec_op_ptr_orig=ec_op_ptr_orig, ec_op_start_ptr=ec_op_start_ptr
    );

    // Verify the keccak builtin. See docstring of `handle_keccak_builtin_verification` for more
    // info.
    let (local keccak_ptr) = handle_keccak_builtin_verification(
        keccak_ptr=keccak_ptr, keccak_ptr_orig=keccak_ptr_orig, keccak_start_ptr=keccak_start_ptr
    );

    // Verify the ecdsa builtin. See docstring of `handle_ecdsa_builtin_verification` for more info.
    let (local ecdsa_ptr) = handle_ecdsa_builtin_verification(
        ecdsa_ptr=ecdsa_ptr, ecdsa_ptr_orig=ecdsa_ptr_orig, ecdsa_start_ptr=ecdsa_start_ptr
    );

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
