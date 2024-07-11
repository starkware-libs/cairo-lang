%builtins output range_check poseidon

from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import PoseidonBuiltin
from starkware.starknet.core.aggregator.combine_blocks import combine_blocks
from starkware.starknet.core.os.output import OsOutput, serialize_os_output

func main{output_ptr: felt*, range_check_ptr, poseidon_ptr: PoseidonBuiltin*}() {
    alloc_locals;

    local os_program_hash: felt;
    local n_tasks: felt;

    // Guess the Starknet OS outputs of the inner blocks.
    let (local os_outputs: OsOutput*) = alloc();

    %{
        from starkware.starknet.core.aggregator.output_parser import parse_bootloader_output
        from starkware.starknet.core.aggregator.utils import OsOutputToCairo

        tasks = parse_bootloader_output(program_input["bootloader_output"])
        assert len(tasks) > 0, "No tasks found in the bootloader output."
        ids.os_program_hash = tasks[0].program_hash
        ids.n_tasks = len(tasks)
        os_output_to_cairo = OsOutputToCairo(segments)
        for i, task in enumerate(tasks):
            os_output_to_cairo.process_os_output(
                segments=segments,
                dst_ptr=ids.os_outputs[i].address_,
                os_output=task.os_output,
            )
    %}

    // Compute the aggregated output.
    let combined_output = combine_blocks(
        n=n_tasks, os_outputs=os_outputs, os_program_hash=os_program_hash
    );

    // Output the bootloader output of the inner OsOutput instances.
    // This represents the "input" of the aggregator, whose correctness is later verified
    // by the bootloader by running the Cairo verifier.

    // Output the number of tasks.
    assert output_ptr[0] = n_tasks;
    let output_ptr = output_ptr + 1;

    output_blocks(n_tasks=n_tasks, os_outputs=os_outputs, os_program_hash=os_program_hash);

    // Output the combined result. This represents the "output" of the aggregator.
    %{
        from starkware.starknet.core.os.kzg_manager import KzgManager

        __serialize_data_availability_create_pages__ = True
        if "polynomial_coefficients_to_kzg_commitment_callback" not in globals():
            from services.utils import kzg_utils
            polynomial_coefficients_to_kzg_commitment_callback = (
                kzg_utils.polynomial_coefficients_to_kzg_commitment
            )
        kzg_manager = KzgManager(polynomial_coefficients_to_kzg_commitment_callback)
    %}
    serialize_os_output(os_output=combined_output);

    %{
        import json

        da_path = program_input.get("da_path")
        if da_path is not None:
            da_segment = kzg_manager.da_segment if program_input["use_kzg_da"] else None
            with open(da_path, "w") as da_file:
                json.dump(da_segment, da_file)
    %}

    return ();
}

// Outputs the given OsOutput instances, with the size of the output and the program hash
// (to match the bootloader output format).
func output_blocks{output_ptr: felt*, range_check_ptr, poseidon_ptr: PoseidonBuiltin*}(
    n_tasks: felt, os_outputs: OsOutput*, os_program_hash: felt
) {
    if (n_tasks == 0) {
        return ();
    }

    let output_start = output_ptr;

    // Keep a placeholder for the output size, which is computed at the end of the function.
    let output_size_placeholder = output_ptr[0];
    let output_ptr = output_ptr + 1;

    assert output_ptr[0] = os_program_hash;
    let output_ptr = output_ptr + 1;

    // Validate fields of the inner OS outputs.
    tempvar header = os_outputs[0].header;
    assert header.use_kzg_da = 0;
    assert header.full_output = 1;
    assert header.os_program_hash = 0;

    %{
        # Note that `serialize_os_output` splits its output to memory pages
        # (see OutputBuiltinRunner.add_page).
        # Since this output is only used internally and will not be used in the final fact,
        # we need to disable page creation.
        __serialize_data_availability_create_pages__ = False
    %}
    serialize_os_output(os_output=&os_outputs[0]);

    // Compute the size of the output, including the program hash and the output size fields.
    assert output_size_placeholder = output_ptr - output_start;

    return output_blocks(
        n_tasks=n_tasks - 1, os_outputs=&os_outputs[1], os_program_hash=os_program_hash
    );
}
