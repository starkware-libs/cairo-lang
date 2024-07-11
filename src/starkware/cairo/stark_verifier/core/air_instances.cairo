struct PublicInput {
}

struct TracesConfig {
}

struct TracesUnsentCommitment {
}

struct TracesCommitment {
}

struct TracesDecommitment {
}

struct TracesWitness {
}

struct OodsEvaluationInfo {
    oods_values: felt*,
    oods_point: felt,
    trace_generator: felt,
    constraint_coefficients: felt*,
}

struct AirInstance {
    // Virtual functions.
    // Each should be a pointer to a function with the same interface as the function in this file.
    public_input_hash: felt*,
    public_input_validate: felt*,
    traces_config_validate: felt*,
    traces_commit: felt*,
    traces_decommit: felt*,
    traces_eval_composition_polynomial: felt*,
    eval_oods_boundary_poly_at_points: felt*,
    // Constants.
    n_dynamic_params: felt,
    n_constraints: felt,
    constraint_degree: felt,
    mask_size: felt,
}
