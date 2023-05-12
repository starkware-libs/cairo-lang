struct EcPoint {
    x: felt,
    y: felt,
}

struct CurveConfig {
    alpha: felt,
    beta: felt,
}

struct EcdsaSigConfig {
    alpha: felt,
    beta: felt,
    shift_point: EcPoint,
}

// Accumulation of member expressions for auto generated composition polynomial code.
struct GlobalValues {
    // Public input.
    trace_length: felt,
    initial_pc: felt,
    final_pc: felt,
    initial_ap: felt,
    final_ap: felt,
    initial_pedersen_addr: felt,
    initial_rc_addr: felt,
    initial_ecdsa_addr: felt,
    initial_bitwise_addr: felt,
    initial_ec_op_addr: felt,
    initial_poseidon_addr: felt,
    rc_min: felt,
    rc_max: felt,

    // Constants.
    offset_size: felt,
    half_offset_size: felt,
    pedersen__shift_point: EcPoint,
    ecdsa__sig_config: EcdsaSigConfig,
    ec_op__curve_config: CurveConfig,

    // Periodic columns.
    pedersen__points__x: felt,
    pedersen__points__y: felt,
    ecdsa__generator_points__x: felt,
    ecdsa__generator_points__y: felt,
    poseidon__poseidon__full_round_key0: felt,
    poseidon__poseidon__full_round_key1: felt,
    poseidon__poseidon__full_round_key2: felt,
    poseidon__poseidon__partial_round_key0: felt,
    poseidon__poseidon__partial_round_key1: felt,

    // Interaction elements.
    memory__multi_column_perm__perm__interaction_elm: felt,
    memory__multi_column_perm__hash_interaction_elm0: felt,
    rc16__perm__interaction_elm: felt,
    diluted_check__permutation__interaction_elm: felt,
    diluted_check__interaction_z: felt,
    diluted_check__interaction_alpha: felt,

    // Permutation products.
    memory__multi_column_perm__perm__public_memory_prod: felt,
    rc16__perm__public_memory_prod: felt,
    diluted_check__first_elm: felt,
    diluted_check__permutation__public_memory_prod: felt,
    diluted_check__final_cum_val: felt,
}

// Elements that are sent from the prover after the commitment on the original trace.
// Used for components after the first interaction, e.g., memory and range check.
struct InteractionElements {
    memory__multi_column_perm__perm__interaction_elm: felt,
    memory__multi_column_perm__hash_interaction_elm0: felt,
    rc16__perm__interaction_elm: felt,
    diluted_check__permutation__interaction_elm: felt,
    diluted_check__interaction_z: felt,
    diluted_check__interaction_alpha: felt,
}
