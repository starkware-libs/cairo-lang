from starkware.cairo.common.cairo_builtins import BitwiseBuiltin, PoseidonBuiltin
from starkware.cairo.common.hash import HashBuiltin
from starkware.cairo.stark_verifier.air.config_instances import TracesConfig
from starkware.cairo.stark_verifier.core.air_instances import (
    AirInstance,
    OodsEvaluationInfo,
    PublicInput,
    TracesCommitment,
    TracesDecommitment,
    TracesUnsentCommitment,
    TracesWitness,
)
from starkware.cairo.stark_verifier.core.channel import Channel
from starkware.cairo.stark_verifier.core.config_instances import StarkConfig
from starkware.cairo.stark_verifier.core.domains import StarkDomains
from starkware.cairo.stark_verifier.core.table_commitment import TableDecommitment

func public_input_hash{range_check_ptr, pedersen_ptr: HashBuiltin*, poseidon_ptr: PoseidonBuiltin*}(
    air: AirInstance*, public_input: PublicInput*, config: StarkConfig*
) -> (res: felt) {
    jmp abs air.public_input_hash;
}

func public_input_validate{range_check_ptr}(
    air: AirInstance*, public_input: PublicInput*, stark_domains: StarkDomains*
) {
    jmp abs air.public_input_validate;
}

func traces_config_validate{range_check_ptr}(
    air: AirInstance*,
    config: TracesConfig*,
    log_eval_domain_size: felt,
    n_verifier_friendly_commitment_layers: felt,
) {
    jmp abs air.traces_config_validate;
}

func traces_commit{range_check_ptr, poseidon_ptr: PoseidonBuiltin*, channel: Channel}(
    air: AirInstance*,
    public_input: PublicInput*,
    unsent_commitment: TracesUnsentCommitment*,
    config: TracesConfig*,
) -> (commitment: TracesCommitment*) {
    jmp abs air.traces_commit;
}

func traces_decommit{
    range_check_ptr,
    blake2s_ptr: felt*,
    bitwise_ptr: BitwiseBuiltin*,
    poseidon_ptr: PoseidonBuiltin*,
}(
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
    public_input: PublicInput*,
    eval_info: OodsEvaluationInfo*,
    n_points: felt,
    points: felt*,
    decommitment: TracesDecommitment*,
    composition_decommitment: TableDecommitment*,
) -> (evaluations: felt*) {
    jmp abs air.eval_oods_boundary_poly_at_points;
}
