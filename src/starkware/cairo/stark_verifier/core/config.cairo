from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.math import assert_in_range, assert_le, assert_nn, assert_nn_le
from starkware.cairo.common.pow import pow
from starkware.cairo.stark_verifier.core.air_interface import AirInstance, traces_config_validate
from starkware.cairo.stark_verifier.core.config_instances import (
    MAX_LOG_BLOWUP_FACTOR,
    MAX_LOG_TRACE,
    MAX_N_QUERIES,
    StarkConfig,
)
from starkware.cairo.stark_verifier.core.domains import StarkDomains
from starkware.cairo.stark_verifier.core.fri.config import fri_config_validate
from starkware.cairo.stark_verifier.core.proof_of_work import proof_of_work_config_validate
from starkware.cairo.stark_verifier.core.utils import FIELD_GENERATOR
from starkware.cairo.stark_verifier.core.vector_commitment import (
    VectorCommitmentConfig,
    validate_vector_commitment,
)

// Validates the StarkConfig object.
func stark_config_validate{range_check_ptr}(
    air: AirInstance*, config: StarkConfig*, security_bits: felt
) {
    alloc_locals;

    // Proof of work.
    proof_of_work_config_validate(config=config.proof_of_work);

    // Sanity checks for the configuration. Many of the bounds are somewhat arbitrary.
    assert_in_range(config.log_trace_domain_size, 1, MAX_LOG_TRACE + 1);
    assert_nn(security_bits);
    assert_in_range(config.log_n_cosets, 1, MAX_LOG_BLOWUP_FACTOR + 1);
    assert_le(config.proof_of_work.n_bits, security_bits);
    assert_in_range(config.n_queries, 1, MAX_N_QUERIES + 1);
    assert_nn(config.n_verifier_friendly_commitment_layers);

    // Check security bits.
    assert_nn_le(
        security_bits, config.n_queries * config.log_n_cosets + config.proof_of_work.n_bits
    );

    // Validate traces config.
    let log_eval_domain_size = config.log_trace_domain_size + config.log_n_cosets;
    traces_config_validate(
        air=air,
        config=config.traces,
        log_eval_domain_size=log_eval_domain_size,
        n_verifier_friendly_commitment_layers=config.n_verifier_friendly_commitment_layers,
    );

    // Validate composition config.
    assert config.composition.n_columns = air.constraint_degree;
    validate_vector_commitment(
        config=config.composition.vector,
        expected_height=log_eval_domain_size,
        n_verifier_friendly_commitment_layers=config.n_verifier_friendly_commitment_layers,
    );

    // Validate Fri config.
    let (log_expected_degree) = fri_config_validate(
        config=config.fri,
        log_n_cosets=config.log_n_cosets,
        n_verifier_friendly_commitment_layers=config.n_verifier_friendly_commitment_layers,
    );
    assert log_expected_degree = config.log_trace_domain_size;

    return ();
}

// Returns a StarkDomains object with information about the domains.
func stark_domains_create{range_check_ptr}(config: StarkConfig*) -> (stark_domains: StarkDomains*) {
    alloc_locals;

    // Compute stark_domains.
    local log_eval_domain_size = config.log_trace_domain_size + config.log_n_cosets;
    let (eval_domain_size) = pow(2, log_eval_domain_size);
    let (eval_generator) = pow(FIELD_GENERATOR, (-1) / eval_domain_size);
    let (trace_domain_size) = pow(2, config.log_trace_domain_size);
    let (trace_generator) = pow(FIELD_GENERATOR, (-1) / trace_domain_size);

    return (
        stark_domains=new StarkDomains(
            log_eval_domain_size=log_eval_domain_size,
            eval_domain_size=eval_domain_size,
            eval_generator=eval_generator,
            log_trace_domain_size=config.log_trace_domain_size,
            trace_domain_size=trace_domain_size,
            trace_generator=trace_generator,
        ),
    );
}
