from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_blake2s.blake2s import blake2s_add_felts, blake2s_bigend
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.math import assert_nn, split_felt, unsigned_div_rem
from starkware.cairo.common.uint256 import Uint256
from starkware.cairo.stark_verifier.core.channel import MONTGOMERY_R, Channel, ChannelUnsentFelt
from starkware.cairo.stark_verifier.core.vector_commitment import (
    VectorCommitment,
    VectorCommitmentConfig,
    VectorCommitmentWitness,
    VectorQuery,
    VectorUnsentCommitment,
    vector_commit,
    vector_commitment_decommit,
)

// Commitment values for a table commitment protocol. Used to generate a commitment by "reading"
// these values from the channel.
struct TableUnsentCommitment {
    vector: VectorUnsentCommitment,
}

// Commitment for a table (n_rows x n_columns) of field elements in montgomery form.
struct TableCommitment {
    config: TableCommitmentConfig*,
    vector_commitment: VectorCommitment*,
}

struct TableCommitmentConfig {
    n_columns: felt,
    vector: VectorCommitmentConfig*,
}

// Responses for queries to the table commitment.
// Each query corresponds to a full row of the table.
struct TableDecommitment {
    // n_columns * n_queries values to decommit.
    n_values: felt,
    values: felt*,
}

// Witness for a decommitment over queries.
struct TableCommitmentWitness {
    vector: VectorCommitmentWitness*,
}

func table_commit{
    blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel, range_check_ptr
}(unsent_commitment: TableUnsentCommitment, config: TableCommitmentConfig*) -> (
    res: TableCommitment*
) {
    let (vector_commitment: VectorCommitment*) = vector_commit(
        unsent_commitment=unsent_commitment.vector, config=config.vector
    );
    return (res=new TableCommitment(config=config, vector_commitment=vector_commitment));
}

// Decommits a TableCommitment at multiple indices.
// rows must be sorted and unique.
// Args:
// commitment - the table commitment.
// n_queries - number of queries to decommit.
// queries - the claimed indices.
// decommitment - the claimed values at those indices.
// witness - the decommitment witness.
func table_decommit{range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*}(
    commitment: TableCommitment*,
    n_queries: felt,
    queries: felt*,
    decommitment: TableDecommitment*,
    witness: TableCommitmentWitness*,
) {
    alloc_locals;

    // Must have at least 1 column.
    local n_columns = commitment.config.n_columns;
    assert_nn(n_columns - 1);
    assert decommitment.n_values = n_queries * n_columns;

    // Convert decommitment values to Montgomery form, since the commitment is in that form.
    let (montgomery_values: felt*) = alloc();
    to_montgomery(
        n_values=decommitment.n_values, values=decommitment.values, output=montgomery_values
    );

    // Generate queries to the underlying vector commitment.
    let (vector_queries: VectorQuery*) = alloc();
    generate_vector_queries(
        n_queries=n_queries,
        queries=queries,
        values=montgomery_values,
        vector_queries=vector_queries,
        n_columns=n_columns,
    );

    vector_commitment_decommit(
        commitment=commitment.vector_commitment,
        n_queries=n_queries,
        queries=vector_queries,
        witness=witness.vector,
    );

    return ();
}

// Converts an array of felts to their montgomery representation.
func to_montgomery(n_values: felt, values: felt*, output: felt*) {
    if (n_values == 0) {
        return ();
    }
    assert output[0] = values[0] * MONTGOMERY_R;
    return to_montgomery(n_values=n_values - 1, values=&values[1], output=&output[1]);
}

// Generates vector queries to the underlying vector commitment from the table queries.
// Args:
// n_queries - number of table queries. Also the number of resulting vector queries.
// queries - input table queries (indices).
// decommitment - input table values.
// vector_queries - output vector queries.
// n_columns - number of columns in table.
func generate_vector_queries{range_check_ptr, blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*}(
    n_queries: felt, queries: felt*, values: felt*, vector_queries: VectorQuery*, n_columns: felt
) {
    if (n_queries == 0) {
        return ();
    }

    alloc_locals;
    assert vector_queries.index = queries[0];
    if (n_columns == 1) {
        let (high, low) = split_felt(values[0]);
        assert vector_queries.value = Uint256(low=low, high=high);

        return generate_vector_queries(
            n_queries=n_queries - 1,
            queries=&queries[1],
            values=&values[n_columns],
            vector_queries=&vector_queries[1],
            n_columns=n_columns,
        );
    }

    let (data: felt*) = alloc();
    let data_start = data;
    blake2s_add_felts{data=data}(n_elements=n_columns, elements=values, bigend=1);
    let (hash) = blake2s_bigend(data=data_start, n_bytes=32 * n_columns);

    // Truncate hash.
    let (low_h, low_l) = unsigned_div_rem(hash.low, 2 ** 96);
    assert vector_queries.value = Uint256(low=low_h * 2 ** 96, high=hash.high);

    return generate_vector_queries(
        n_queries=n_queries - 1,
        queries=&queries[1],
        values=&values[n_columns],
        vector_queries=&vector_queries[1],
        n_columns=n_columns,
    );
}
