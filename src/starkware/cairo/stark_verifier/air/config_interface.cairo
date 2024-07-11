from starkware.cairo.common.math import assert_in_range
from starkware.cairo.stark_verifier.air.config_instances import MAX_N_COLUMNS, TracesConfig
from starkware.cairo.stark_verifier.air.layout import AirWithLayout
from starkware.cairo.stark_verifier.core.vector_commitment import validate_vector_commitment

// Validates the configuration of the traces.
// log_eval_domain_size - Log2 of the evaluation domain size.
func traces_config_validate{range_check_ptr}(
    air: AirWithLayout*,
    config: TracesConfig*,
    log_eval_domain_size: felt,
    n_verifier_friendly_commitment_layers: felt,
) {
    assert_in_range(config.original.n_columns, 1, MAX_N_COLUMNS + 1);
    assert_in_range(config.interaction.n_columns, 1, MAX_N_COLUMNS + 1);
    assert config.original.n_columns = air.layout.n_original_columns;
    assert config.interaction.n_columns = air.layout.n_interaction_columns;
    validate_vector_commitment(
        config=config.original.vector,
        expected_height=log_eval_domain_size,
        n_verifier_friendly_commitment_layers=n_verifier_friendly_commitment_layers,
    );
    validate_vector_commitment(
        config=config.interaction.vector,
        expected_height=log_eval_domain_size,
        n_verifier_friendly_commitment_layers=n_verifier_friendly_commitment_layers,
    );
    return ();
}
