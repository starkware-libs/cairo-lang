from starkware.cairo.common.math import assert_in_range
from starkware.cairo.stark_verifier.air.layout import AirWithLayout
from starkware.cairo.stark_verifier.core.table_commitment import TableCommitmentConfig

const MAX_N_COLUMNS = 128;

// Configuration for the Traces component.
struct TracesConfig {
    original: TableCommitmentConfig*,
    interaction: TableCommitmentConfig*,
}

// Validates the configuration of the traces.
// log_eval_domain_size - Log2 of the evaluation domain size.
func traces_config_validate{range_check_ptr}(
    air: AirWithLayout*, config: TracesConfig*, log_eval_domain_size: felt
) {
    assert_in_range(config.original.n_columns, 1, MAX_N_COLUMNS + 1);
    assert_in_range(config.interaction.n_columns, 1, MAX_N_COLUMNS + 1);
    assert config.original.n_columns = air.layout.n_original_columns;
    assert config.interaction.n_columns = air.layout.n_interaction_columns;
    assert config.original.vector.height = log_eval_domain_size;
    assert config.interaction.vector.height = log_eval_domain_size;
    return ();
}
