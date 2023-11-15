struct EcPoint {
    x: felt,
    y: felt,
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
    initial_range_check_addr: felt,
    initial_bitwise_addr: felt,
    range_check_min: felt,
    range_check_max: felt,

    // Constants.
    offset_size: felt,
    half_offset_size: felt,
    pedersen__shift_point: EcPoint,

    // Periodic columns.
    pedersen__points__x: felt,
    pedersen__points__y: felt,

    // Interaction elements.
    memory__multi_column_perm__perm__interaction_elm: felt,
    memory__multi_column_perm__hash_interaction_elm0: felt,
    range_check16__perm__interaction_elm: felt,
    diluted_check__permutation__interaction_elm: felt,
    diluted_check__interaction_z: felt,
    diluted_check__interaction_alpha: felt,

    // Permutation products.
    memory__multi_column_perm__perm__public_memory_prod: felt,
    range_check16__perm__public_memory_prod: felt,
    diluted_check__first_elm: felt,
    diluted_check__permutation__public_memory_prod: felt,
    diluted_check__final_cum_val: felt,
}

// Elements that are sent from the prover after the commitment on the original trace.
// Used for components after the first interaction, e.g., memory and range check.
struct InteractionElements {
    memory__multi_column_perm__perm__interaction_elm: felt,
    memory__multi_column_perm__hash_interaction_elm0: felt,
    range_check16__perm__interaction_elm: felt,
    diluted_check__permutation__interaction_elm: felt,
    diluted_check__interaction_z: felt,
    diluted_check__interaction_alpha: felt,
}
