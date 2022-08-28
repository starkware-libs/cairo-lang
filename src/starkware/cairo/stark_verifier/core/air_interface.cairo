from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.hash import HashBuiltin
from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.stark_verifier.core.channel import Channel
from starkware.cairo.stark_verifier.core.domains import StarkDomains
from starkware.cairo.stark_verifier.core.table_commitment import TableDecommitment

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
    n_constraints: felt,
    constraint_degree: felt,
    mask_size: felt,
}

func public_input_hash{
    range_check_ptr, pedersen_ptr: HashBuiltin*, bitwise_ptr: BitwiseBuiltin*, blake2s_ptr: felt*
}(air: AirInstance*, public_input: PublicInput*) -> (res: Uint256) {
    jmp abs air.public_input_hash;
}

func public_input_validate{range_check_ptr}(
    air: AirInstance*, public_input: PublicInput*, stark_domains: StarkDomains*
) {
    jmp abs air.public_input_validate;
}

func traces_config_validate{range_check_ptr}(
    air: AirInstance*, config: TracesConfig*, log_eval_domain_size: felt
) {
    jmp abs air.traces_config_validate;
}

func traces_commit{
    range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel
}(
    air: AirInstance*,
    public_input: PublicInput*,
    unsent_commitment: TracesUnsentCommitment*,
    config: TracesConfig*,
) -> (commitment: TracesCommitment*) {
    jmp abs air.traces_commit;
}

func traces_decommit{range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*}(
    air: AirInstance*,
    n_queries: felt,
    queries: felt*,
    commitment: TracesCommitment*,
    decommitment: TracesDecommitment*,
    witness: TracesWitness*,
) {
    jmp abs air.traces_decommit;
}

func traces_eval_composition_polynomial{range_check_ptr}(
    air: AirInstance*,
    commitment: TracesCommitment*,
    mask_values: felt*,
    constraint_coefficients: felt*,
    point: felt,
    trace_domain_size: felt,
    trace_generator: felt,
) -> (res: felt) {
    jmp abs air.traces_eval_composition_polynomial;
}

func eval_oods_boundary_poly_at_points{range_check_ptr}(
    air: AirInstance*,
    eval_info: OodsEvaluationInfo*,
    n_points: felt,
    points: felt*,
    decommitment: TracesDecommitment*,
    composition_decommitment: TableDecommitment*,
) -> (evaluations: felt*) {
    jmp abs air.eval_oods_boundary_poly_at_points;
}
