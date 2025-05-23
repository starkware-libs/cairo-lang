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
    initial_range_check_addr: felt,
    initial_ecdsa_addr: felt,
    initial_bitwise_addr: felt,
    initial_ec_op_addr: felt,
    initial_keccak_addr: felt,
    initial_poseidon_addr: felt,
    initial_range_check96_addr: felt,
    initial_add_mod_addr: felt,
    initial_mul_mod_addr: felt,
    range_check_min: felt,
    range_check_max: felt,

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
    keccak__keccak__keccak_round_key0: felt,
    keccak__keccak__keccak_round_key1: felt,
    keccak__keccak__keccak_round_key3: felt,
    keccak__keccak__keccak_round_key7: felt,
    keccak__keccak__keccak_round_key15: felt,
    keccak__keccak__keccak_round_key31: felt,
    keccak__keccak__keccak_round_key63: felt,
    poseidon__poseidon__full_round_key0: felt,
    poseidon__poseidon__full_round_key1: felt,
    poseidon__poseidon__full_round_key2: felt,
    poseidon__poseidon__partial_round_key0: felt,
    poseidon__poseidon__partial_round_key1: felt,

    // Interaction elements.
    memory__multi_column_perm__perm__interaction_elm: felt,
    memory__multi_column_perm__hash_interaction_elm0: felt,
    range_check16__perm__interaction_elm: felt,
    diluted_check__permutation__interaction_elm: felt,
    diluted_check__interaction_z: felt,
    diluted_check__interaction_alpha: felt,
    add_mod__interaction_elm: felt,
    mul_mod__interaction_elm: felt,

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
    add_mod__interaction_elm: felt,
    mul_mod__interaction_elm: felt,
}
