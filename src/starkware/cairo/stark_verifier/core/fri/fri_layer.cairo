from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.math import assert_nn, assert_not_equal
from starkware.cairo.common.pow import pow
from starkware.cairo.common.registers import get_label_location
from starkware.cairo.stark_verifier.core.fri.fri_formula import fri_formula

// Constant parameters for computing the next FRI layer.
struct FriLayerComputationParams {
    coset_size: felt,
    fri_group: felt*,
    eval_point: felt,
}

struct FriLayerQuery {
    index: felt,
    y_value: felt,
    x_inv_value: felt,
}

// Computes the elements of the coset starting at coset_start_index.
//
// Inputs:
//   - n_queries: the number of input queries.
//   - queries: an iterator over the input queries.
//   - sibling_witness: a list of all the query's siblings.
//   - coset_size: the number of elements in the coset.
//   - coset_start_index: the index of the first element of the coset being calculated.
//   - offset_within_coset: the offset of the current processed element within the coset.
//   - fri_group: holds the group <g> in bit reversed order, where g is the generator of the coset.
//
// Outputs:
//   - coset_elements: the values of the coset elements.
//   - coset_x_inv: x_inv of the first element in the coset. This value is set only if at least one
//   query was consumed by this function.
func compute_coset_elements{n_queries: felt, queries: FriLayerQuery*, sibling_witness: felt*}(
    coset_size: felt,
    coset_start_index: felt,
    offset_within_coset: felt,
    fri_group: felt*,
    coset_elements: felt*,
    coset_x_inv: felt*,
) {
    if (offset_within_coset == coset_size) {
        return ();
    }

    if (n_queries != 0) {
        if (queries.index == coset_start_index + offset_within_coset) {
            assert [coset_elements] = queries.y_value;
            assert [coset_x_inv] = queries.x_inv_value * [fri_group];

            let n_queries = n_queries - 1;
            let queries = &queries[1];
            return compute_coset_elements(
                coset_size=coset_size,
                coset_start_index=coset_start_index,
                offset_within_coset=offset_within_coset + 1,
                fri_group=&fri_group[1],
                coset_elements=&coset_elements[1],
                coset_x_inv=coset_x_inv,
            );
        }
    }

    assert [coset_elements] = [sibling_witness];
    let sibling_witness = &sibling_witness[1];
    return compute_coset_elements(
        coset_size=coset_size,
        coset_start_index=coset_start_index,
        offset_within_coset=offset_within_coset + 1,
        fri_group=&fri_group[1],
        coset_elements=&coset_elements[1],
        coset_x_inv=coset_x_inv,
    );
}

// Computes FRI next layer for the given queries. I.e., takes the given i-th layer queries
// and produces queries for layer i+1 (a single query for each coset in the i-th layer).
//
// Inputs:
//   - n_queries: the number of input queries.
//   - queries: input queries.
//   - sibling_witness: a list of all the query's siblings.
//   - params: the parameters to use for the layer computation.
//
// Outputs:
//   - next_queries: queries for the next layer.
//   - verify_indices: query indices of the given layer for Merkle verification.
//   - verify_y_values: query y values of the given layer for Merkle verification.
func compute_next_layer{
    range_check_ptr,
    n_queries: felt,
    queries: FriLayerQuery*,
    sibling_witness: felt*,
    next_queries: FriLayerQuery*,
    verify_indices: felt*,
    verify_y_values: felt*,
}(params: FriLayerComputationParams*) {
    if (n_queries == 0) {
        return ();
    }

    alloc_locals;
    local coset_size = params.coset_size;

    // Guess coset_index.
    // Note that compute_coset_elements() consumes queries, and it is verified
    // that it consumed at least one query. This will imply that coset_index is correct.
    local coset_index = nondet %{ ids.queries.index // ids.params.coset_size %};
    assert_nn(coset_index);

    // Write verification query.
    assert [verify_indices] = coset_index;
    let verify_indices = &verify_indices[1];
    let coset_elements = verify_y_values;
    let verify_y_values = &verify_y_values[coset_size];

    // Store n_queries in order to verify at least one query was consumed.
    local n_queries_before = n_queries;
    let (coset_x_inv: felt*) = alloc();
    compute_coset_elements(
        coset_size=coset_size,
        coset_start_index=coset_index * coset_size,
        offset_within_coset=0,
        fri_group=params.fri_group,
        coset_elements=coset_elements,
        coset_x_inv=coset_x_inv,
    );

    // Verify that at least one query was consumed.
    assert_not_equal(n_queries_before, n_queries);

    let (fri_formula_res) = fri_formula(
        values=coset_elements,
        eval_point=params.eval_point,
        x_inv=[coset_x_inv],
        coset_size=coset_size,
    );

    // Write next layer query.
    let (next_x_inv) = pow([coset_x_inv], params.coset_size);
    assert next_queries[0] = FriLayerQuery(
        index=coset_index, y_value=fri_formula_res, x_inv_value=next_x_inv
    );
    let next_queries = &next_queries[1];

    return compute_next_layer(params=params);
}

// Returns the elements of the multiplicative subgroup of order 16, in bit-reversed order for the
// cairo prime field. Note that the first 2^k elements correspond to the group of size 2^k.
func get_fri_group() -> (address: felt*) {
    alloc_locals;
    let (address) = get_label_location(data);
    return (address=address);

    data:
    dw 0x1;
    dw 0x800000000000011000000000000000000000000000000000000000000000000;
    dw 0x625023929a2995b533120664329f8c7c5268e56ac8320da2a616626f41337e3;
    dw 0x1dafdc6d65d66b5accedf99bcd607383ad971a9537cdf25d59e99d90becc81e;
    dw 0x63365fe0de874d9c90adb1e2f9c676e98c62155e4412e873ada5e1dee6feebb;
    dw 0x1cc9a01f2178b3736f524e1d06398916739deaa1bbed178c525a1e211901146;
    dw 0x3b912c31d6a226e4a15988c6b7ec1915474043aac68553537192090b43635cd;
    dw 0x446ed3ce295dda2b5ea677394813e6eab8bfbc55397aacac8e6df6f4bc9ca34;
    dw 0x5ec467b88826aba4537602d514425f3b0bdf467bbf302458337c45f6021e539;
    dw 0x213b984777d9556bac89fd2aebbda0c4f420b98440cfdba7cc83ba09fde1ac8;
    dw 0x5ce3fa16c35cb4da537753675ca3276ead24059dddea2ca47c36587e5a538d1;
    dw 0x231c05e93ca34c35ac88ac98a35cd89152dbfa622215d35b83c9a781a5ac730;
    dw 0x00b54759e8c46e1258dc80f091e6f3be387888015452ce5f0ca09ce9e571f52;
    dw 0x7f4ab8a6173b92fda7237f0f6e190c41c78777feabad31a0f35f63161a8e0af;
    dw 0x23c12f3909539339b83645c1b8de3e14ebfee15c2e8b3ad2867e3a47eba558c;
    dw 0x5c3ed0c6f6ac6dd647c9ba3e4721c1eb14011ea3d174c52d7981c5b8145aa75;
}
