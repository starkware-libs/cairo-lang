from starkware.cairo.stark_verifier.core.air_interface import AirInstance

struct Layout {
    // Virtual functions.
    // Each should be a pointer to a function with the same interface as the function in this file.
    eval_oods_polynomial: felt*,
    // Constants.
    n_original_columns: felt,
    n_interaction_columns: felt,
    n_interaction_elements: felt,
}

struct AirWithLayout {
    air: AirInstance,
    layout: Layout,
}

struct OodsGlobalValues {
}

func eval_oods_polynomial{range_check_ptr}(
    layout: Layout*,
    column_values: felt*,
    oods_values: felt*,
    constraint_coefficients: felt*,
    point: felt,
    oods_point: felt,
    trace_generator: felt,
    global_values: OodsGlobalValues*,
) -> (res: felt) {
    jmp abs layout.eval_oods_polynomial;
}
