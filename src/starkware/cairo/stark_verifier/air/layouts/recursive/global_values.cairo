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
    initial_rc_addr: felt,
    initial_bitwise_addr: felt,
    initial_keccak_addr: felt,
    rc_min: felt,
    rc_max: felt,

    // Constants.
    offset_size: felt,
    half_offset_size: felt,
    pedersen__shift_point: EcPoint,

    // Periodic columns.
    pedersen__points__x: felt,
    pedersen__points__y: felt,
    keccak__keccak__keccak_round_key0: felt,
    keccak__keccak__keccak_round_key1: felt,
    keccak__keccak__keccak_round_key3: felt,
    keccak__keccak__keccak_round_key7: felt,
    keccak__keccak__keccak_round_key15: felt,
    keccak__keccak__keccak_round_key31: felt,
    keccak__keccak__keccak_round_key63: felt,

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
