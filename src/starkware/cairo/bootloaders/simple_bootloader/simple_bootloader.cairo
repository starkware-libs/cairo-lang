%builtins output pedersen range_check ecdsa bitwise ec_op keccak poseidon range_check96 add_mod mul_mod

from starkware.cairo.bootloaders.simple_bootloader.run_simple_bootloader import (
    run_simple_bootloader,
)
from starkware.cairo.bootloaders.simple_bootloader.verify_builtins import (
    create_ecdsa_builtin_segment_if_needed,
    create_keccak_builtin_segment_if_needed,
    verify_ecdsa_builtin_if_needed,
    verify_keccak_builtin_if_needed,
)
from starkware.cairo.common.cairo_builtins import (
    BitwiseBuiltin,
    EcOpBuiltin,
    HashBuiltin,
    KeccakBuiltin,
    ModBuiltin,
    PoseidonBuiltin,
    SignatureBuiltin,
)
from starkware.cairo.common.registers import get_fp_and_pc

// For documentation of the simple bootloader, see the docstring of `run_simple_bootloader'.
// Hint arguments:
// program_input - contains the tasks to execute. Formatted as a SimpleBootloaderInput object.
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
    alloc_locals;
    %{
        from starkware.cairo.bootloaders.simple_bootloader.objects import SimpleBootloaderInput
        simple_bootloader_input = SimpleBootloaderInput.Schema().load(program_input)
    %}

    // Handle keccak builtin.
    // See docstring of `create_keccak_builtin_segment_if_needed` for more info.
    local keccak_ptr_orig: KeccakBuiltin* = keccak_ptr;
    let (local keccak_ptr: KeccakBuiltin*) = create_keccak_builtin_segment_if_needed(
        keccak_ptr=keccak_ptr
    );
    local keccak_start_ptr: KeccakBuiltin* = keccak_ptr;

    // Handle ecdsa builtin.
    // See docstring of `create_ecdsa_builtin_segment_if_needed` for more info.
    local ecdsa_ptr_orig: SignatureBuiltin* = ecdsa_ptr;
    let (local ecdsa_ptr: SignatureBuiltin*) = create_ecdsa_builtin_segment_if_needed(
        ecdsa_ptr=ecdsa_ptr
    );
    local ecdsa_start_ptr: SignatureBuiltin* = ecdsa_ptr;

    // Execute tasks.
    run_simple_bootloader();

    // Verify the keccak builtin. See docstring of `verify_keccak_builtin_if_needed` for more
    // info.
    let (local keccak_ptr: KeccakBuiltin*) = verify_keccak_builtin_if_needed(
        keccak_ptr=keccak_ptr, keccak_ptr_orig=keccak_ptr_orig, keccak_start_ptr=keccak_start_ptr
    );

    // Verify the ecdsa builtin. See docstring of `verify_ecdsa_builtin_if_needed` for more info.
    let (local ecdsa_ptr: SignatureBuiltin*) = verify_ecdsa_builtin_if_needed(
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
