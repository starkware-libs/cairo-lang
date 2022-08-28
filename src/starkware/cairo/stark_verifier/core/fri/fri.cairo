from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.math import horner_eval
from starkware.cairo.common.pow import pow
from starkware.cairo.stark_verifier.core.channel import (
    Channel,
    ChannelSentFelt,
    ChannelUnsentFelt,
    random_felts_to_prover,
    read_felt_vector_from_prover,
)
from starkware.cairo.stark_verifier.core.fri.config import FriConfig, fri_config_validate
from starkware.cairo.stark_verifier.core.fri.fri_layer import (
    FriLayerComputationParams,
    FriLayerQuery,
    compute_next_layer,
    get_fri_group,
)
from starkware.cairo.stark_verifier.core.table_commitment import (
    TableCommitment,
    TableCommitmentConfig,
    TableCommitmentWitness,
    TableDecommitment,
    TableUnsentCommitment,
    table_commit,
    table_decommit,
)
from starkware.cairo.stark_verifier.core.utils import FIELD_GENERATOR

// A FRI phase with N layers starts with a single input layer.
// Afterwards, there are N - 1 inner layers resulting from FRI-folding each preceding layer.
// Each such layer has a separate table commitment, for a total of N - 1 commitments.
// Lastly, there is another FRI-folding resulting in the last FRI layer, that is commited by
// sending the polynomial coefficients, instead of a table commitment.
// Each folding has a step size.
// Illustration:
// InputLayer, no commitment.
//   fold step 0
// InnerLayer 0, Table commitment
//   fold step 1
// ...
// InnerLayer N - 2, Table commitment
//   fold step N - 1
// LastLayer, Polynomial coefficients
//
// N steps.
// N - 1 inner layers.

// Commitment values for FRI. Used to generate a commitment by "reading" these values
// from the channel.
struct FriUnsentCommitment {
    // Array of size n_layers - 1 containing unsent table commitments for each inner layer.
    inner_layers: TableUnsentCommitment*,
    // Array of size 2**log_last_layer_degree_bound containing coefficients for the last layer
    // polynomial.
    last_layer_coefficients: ChannelUnsentFelt*,
}

struct FriCommitment {
    config: FriConfig*,
    // Array of size n_layers - 1 containing table commitments for each inner layer.
    inner_layers: TableCommitment**,
    // Array of size n_layers, of one evaluation point for each layer.
    eval_points: felt*,
    // Array of size 2**log_last_layer_degree_bound containing coefficients for the last layer
    // polynomial.
    last_layer_coefficients: ChannelSentFelt*,
}

struct FriDecommitment {
    // Number of queries.
    n_values: felt,
    // Array of size n_values, containing the values of the input layer at query indices.
    values: felt*,
    // Array of size n_values, containing the field elements that correspond to the query indices
    // (See queries_to_points).
    points: felt*,
}

// A witness for the decommitment of the FRI layers over queries.
struct FriWitness {
    // An array of size n_layers - 1, containing a witness for each inner layer.
    layers: FriLayerWitness*,
}

// A witness for a single FRI layer. This witness is required to verify the transition from an
// inner layer to the following layer.
struct FriLayerWitness {
    // Values for the sibling leaves required for decommitment.
    n_leaves: felt,
    leaves: felt*,
    // Table commitment witnesses for decommiting all the leaves.
    table_witness: TableCommitmentWitness*,
}

// Commit function of the FRI component.
// Implements the commit phase of the FRI protocol.
func fri_commit{
    blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel, range_check_ptr
}(unsent_commitment: FriUnsentCommitment*, config: FriConfig*) -> (commitment: FriCommitment*) {
    alloc_locals;
    let (inner_layer_commitments: TableCommitment**) = alloc();
    let (eval_points: felt*) = alloc();

    // The first step should be 0, and thus we don't need a point for it.
    assert config.fri_step_sizes[0] = 0;
    assert eval_points[0] = 0;

    // Read inner layer commitments and eval_points.
    fri_commit_rounds(
        n_layers=config.n_layers - 1,
        configs=config.inner_layers,
        unsent_commitments=unsent_commitment.inner_layers,
        step_sizes=config.fri_step_sizes,
        commitments=inner_layer_commitments,
        eval_points=&eval_points[1],
    );

    // Read last layer coefficients.
    let (n_coefficients) = pow(2, config.log_last_layer_degree_bound);
    let (coefficients) = read_felt_vector_from_prover(
        n_values=n_coefficients, values=unsent_commitment.last_layer_coefficients
    );

    return (
        commitment=new FriCommitment(
        config=config,
        inner_layers=inner_layer_commitments,
        eval_points=eval_points,
        last_layer_coefficients=coefficients),
    );
}

// Performs FRI commitment phase rounds. Each round reads a commitment on a layer, and sends an
// evaluation point for the next round.
func fri_commit_rounds{
    blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel, range_check_ptr
}(
    n_layers: felt,
    configs: TableCommitmentConfig*,
    unsent_commitments: TableUnsentCommitment*,
    step_sizes: felt*,
    commitments: TableCommitment**,
    eval_points: felt*,
) {
    alloc_locals;
    if (n_layers == 0) {
        return ();
    }

    // Read commitments.
    let (table_commitment) = table_commit(unsent_commitment=unsent_commitments[0], config=configs);
    assert commitments[0] = table_commitment;

    // Send the next eval_points.
    random_felts_to_prover(n_elements=1, elements=eval_points);

    return fri_commit_rounds(
        n_layers=n_layers - 1,
        configs=&configs[1],
        unsent_commitments=&unsent_commitments[1],
        step_sizes=&step_sizes[1],
        commitments=&commitments[1],
        eval_points=&eval_points[1],
    );
}

// FRI protocol component decommitment.
func fri_decommit{range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*}(
    n_queries: felt,
    queries: felt*,
    commitment: FriCommitment*,
    decommitment: FriDecommitment*,
    witness: FriWitness*,
) {
    alloc_locals;

    assert n_queries = decommitment.n_values;
    let fri_first_layer_evaluations = decommitment.values;

    // Compute first FRI layer queries.
    let (fri_queries: FriLayerQuery*) = alloc();
    gather_first_layer_queries(
        n_queries=n_queries,
        queries=queries,
        evaluations=decommitment.values,
        x_values=decommitment.points,
        fri_queries=fri_queries,
    );

    // Compute fri_group.
    let (fri_group) = get_fri_group();

    // Decommit inner layers.
    let (n_last_queries, last_queries) = fri_decommit_layers(
        fri_group=fri_group,
        n_layers=commitment.config.n_layers - 1,
        commitment=commitment.inner_layers,
        layer_witness=witness.layers,
        eval_points=&commitment.eval_points[1],
        step_sizes=&commitment.config.fri_step_sizes[1],
        n_queries=n_queries,
        queries=fri_queries,
    );

    // Last layer.
    let (n_coefficients) = pow(2, commitment.config.log_last_layer_degree_bound);
    verify_last_layer(
        n_queries=n_last_queries,
        queries=last_queries,
        n_coefficients=n_coefficients,
        coefficients=commitment.last_layer_coefficients,
    );
    return ();
}

func gather_first_layer_queries(
    n_queries: felt,
    queries: felt*,
    evaluations: felt*,
    x_values: felt*,
    fri_queries: FriLayerQuery*,
) {
    if (n_queries == 0) {
        return ();
    }

    // Translate the coset to the homogenous group to have simple FRI equations.
    let shifted_x_value = x_values[0] / FIELD_GENERATOR;
    assert fri_queries[0] = FriLayerQuery(
        index=queries[0],
        y_value=evaluations[0],
        x_inv_value=1 / shifted_x_value,
        );

    return gather_first_layer_queries(
        n_queries=n_queries - 1,
        queries=&queries[1],
        evaluations=&evaluations[1],
        x_values=&x_values[1],
        fri_queries=&fri_queries[1],
    );
}

func fri_decommit_layers{range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*}(
    fri_group: felt*,
    n_layers: felt,
    commitment: TableCommitment**,
    layer_witness: FriLayerWitness*,
    eval_points: felt*,
    step_sizes: felt*,
    n_queries: felt,
    queries: FriLayerQuery*,
) -> (n_last_queries: felt, last_queries: FriLayerQuery*) {
    if (n_layers == 0) {
        return (n_last_queries=n_queries, last_queries=queries);
    }

    alloc_locals;
    // Params.
    let (coset_size) = pow(2, step_sizes[0]);
    tempvar params: FriLayerComputationParams* = new FriLayerComputationParams(
        coset_size=coset_size, fri_group=fri_group, eval_point=eval_points[0]);

    // Allocate values for the next layer computation.
    let (next_queries: FriLayerQuery*) = alloc();
    let next_queries_start = next_queries;
    let sibling_witness = layer_witness.leaves;
    let (verify_indices) = alloc();
    let verify_indices_start = verify_indices;
    let (verify_y_values) = alloc();
    let verify_y_values_start = verify_y_values;

    // Compute next layer queries.
    with n_queries, queries, sibling_witness, next_queries, verify_indices, verify_y_values {
        compute_next_layer(params=params);
    }
    let n_next_queries = (next_queries - next_queries_start) / FriLayerQuery.SIZE;

    // Table decommitment.
    tempvar decommitment: TableDecommitment* = new TableDecommitment(
        n_values=verify_y_values - verify_y_values_start,
        values=verify_y_values_start,
        );
    table_decommit(
        commitment=commitment[0],
        n_queries=verify_indices - verify_indices_start,
        queries=verify_indices_start,
        decommitment=decommitment,
        witness=layer_witness.table_witness,
    );

    return fri_decommit_layers(
        fri_group=fri_group,
        n_layers=n_layers - 1,
        commitment=&commitment[1],
        layer_witness=&layer_witness[1],
        eval_points=&eval_points[1],
        step_sizes=&step_sizes[1],
        n_queries=n_next_queries,
        queries=next_queries_start,
    );
}

// Verifies FRI last layer by evaluating the given polynomial on the given points (=inverses of
// x_inv_values), and comparing the results to the given values.
func verify_last_layer(
    n_queries: felt, queries: FriLayerQuery*, n_coefficients: felt, coefficients: felt*
) {
    if (n_queries == 0) {
        return ();
    }

    let (value) = horner_eval(
        n_coefficients=n_coefficients, coefficients=coefficients, point=1 / queries[0].x_inv_value
    );
    assert value = queries[0].y_value;

    return verify_last_layer(
        n_queries=n_queries - 1,
        queries=&queries[1],
        n_coefficients=n_coefficients,
        coefficients=coefficients,
    );
}
