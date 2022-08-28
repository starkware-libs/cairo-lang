from starkware.cairo.common.math import assert_in_range, assert_nn, assert_nn_le
from starkware.cairo.common.pow import pow
from starkware.cairo.stark_verifier.core.table_commitment import TableCommitmentConfig

// Constants.
const MAX_LAST_LAYER_LOG_DEGREE_BOUND = 15;
const MAX_FRI_LAYERS = 15;
const MAX_FRI_STEP = 4;

// Configuration for the FRI component.
struct FriConfig {
    // Log2 of the size of the input layer to FRI.
    log_input_size: felt,
    // Number of layers in the FRI. Inner + last layer.
    n_layers: felt,
    // Array of size n_layers - 1, each entry is a configuration of a table commitment for the
    // corresponding inner layer.
    inner_layers: TableCommitmentConfig*,
    // Array of size n_layers, each entry represents the FRI step size,
    // i.e. the number of FRI-foldings between layer i and i+1.
    fri_step_sizes: felt*,
    log_last_layer_degree_bound: felt,
}

func fri_config_validate{range_check_ptr}(config: FriConfig*, log_n_cosets: felt) -> (
    log_expected_degree: felt
) {
    assert_nn_le(config.log_last_layer_degree_bound, MAX_LAST_LAYER_LOG_DEGREE_BOUND);
    assert_in_range(config.n_layers, 2, MAX_FRI_LAYERS + 1);
    assert config.fri_step_sizes[0] = 0;
    let (sum_of_step_sizes) = fri_layers_config_validate(
        n_layers=config.n_layers - 1,
        layers=config.inner_layers,
        fri_step_sizes=&config.fri_step_sizes[1],
        log_input_size=config.log_input_size - config.fri_step_sizes[0],
    );
    tempvar log_expected_input_degree = sum_of_step_sizes + config.log_last_layer_degree_bound;
    assert log_expected_input_degree + log_n_cosets = config.log_input_size;
    return (log_expected_degree=log_expected_input_degree);
}

func fri_layers_config_validate{range_check_ptr}(
    n_layers: felt, layers: TableCommitmentConfig*, fri_step_sizes: felt*, log_input_size: felt
) -> (sum_of_step_sizes: felt) {
    alloc_locals;
    if (n_layers == 0) {
        assert_nn(log_input_size);
        return (sum_of_step_sizes=0);
    }

    local fri_step = fri_step_sizes[0];
    assert_in_range(fri_step, 1, MAX_FRI_STEP + 1);
    let (sum_of_step_sizes) = fri_layers_config_validate(
        n_layers=n_layers - 1,
        layers=&layers[1],
        fri_step_sizes=&fri_step_sizes[1],
        log_input_size=log_input_size - fri_step,
    );
    let (n_columns) = pow(2, fri_step);
    assert layers.n_columns = n_columns;
    assert layers.vector.height = log_input_size - fri_step;
    return (sum_of_step_sizes=sum_of_step_sizes + fri_step);
}
