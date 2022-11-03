from starkware.cairo.common.alloc import alloc
from starkware.cairo.common.cairo_builtins import BitwiseBuiltin
from starkware.cairo.common.math import assert_le, unsigned_div_rem
from starkware.cairo.common.pow import pow
from starkware.cairo.common.usort import usort
from starkware.cairo.stark_verifier.core.channel import Channel, random_uint256_to_prover
from starkware.cairo.stark_verifier.core.config import FIELD_GENERATOR, StarkDomains
from starkware.cairo.stark_verifier.core.utils import bit_reverse_u64

// Samples random queries from the verifier.
func generate_queries{
    blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel, range_check_ptr
}(n_samples: felt, stark_domains: StarkDomains*) -> (n_queries: felt, queries: felt*) {
    alloc_locals;

    // Sample query indices from the channel.
    let (samples: felt*) = alloc();
    sample_random_queries(
        n_samples=n_samples, samples=samples, query_upper_bound=stark_domains.eval_domain_size
    );

    let (n_queries, queries: felt*, multiplicities: felt*) = usort(
        input_len=n_samples, input=samples
    );

    return (n_queries=n_queries, queries=queries);
}

func sample_random_queries{
    blake2s_ptr: felt*, bitwise_ptr: BitwiseBuiltin*, channel: Channel, range_check_ptr
}(n_samples: felt, samples: felt*, query_upper_bound: felt) {
    // Since samples are generated in quadruplets, we might generate up to 3 extra query indices.
    // Return if we n_samples is 0, -1, -2 or -3.
    if (n_samples * (n_samples + 1) * (n_samples + 2) * (n_samples + 3) == 0) {
        return ();
    }
    let (res) = random_uint256_to_prover();
    let (hh, hl) = unsigned_div_rem(res.high, 2 ** 64);
    let (lh, ll) = unsigned_div_rem(res.low, 2 ** 64);
    let (_, r0) = unsigned_div_rem(hh, query_upper_bound);
    let (_, r1) = unsigned_div_rem(hl, query_upper_bound);
    let (_, r2) = unsigned_div_rem(lh, query_upper_bound);
    let (_, r3) = unsigned_div_rem(ll, query_upper_bound);
    assert samples[0] = r0;
    assert samples[1] = r1;
    assert samples[2] = r2;
    assert samples[3] = r3;
    return sample_random_queries(
        n_samples=n_samples - 4, samples=&samples[4], query_upper_bound=query_upper_bound
    );
}

// Computes the corresponding field element for each query index.
// I.e., index -> eval_generator ^ bit_revese(index).
func queries_to_points{range_check_ptr, bitwise_ptr: BitwiseBuiltin*}(
    n_queries: felt, queries: felt*, stark_domains: StarkDomains*
) -> (points: felt*) {
    alloc_locals;
    // Evaluation domains of size greater than 2**64 are not supported.
    assert_le(stark_domains.log_eval_domain_size, 64);

    // A 'log_eval_domain_size' bits index can be bit reversed using bit_reverse_u64 if it is
    // multiplied by 2**(64 - log_eval_domain_size) first.
    let (shift) = pow(2, 64 - stark_domains.log_eval_domain_size);
    let (points: felt*) = alloc();
    queries_to_points_inner(
        n_queries=n_queries,
        queries=queries,
        points=points,
        shift=shift,
        eval_generator=stark_domains.eval_generator,
    );
    return (points=points);
}

func queries_to_points_inner{range_check_ptr, bitwise_ptr: BitwiseBuiltin*}(
    n_queries: felt, queries: felt*, points: felt*, shift: felt, eval_generator: felt
) {
    alloc_locals;
    if (n_queries == 0) {
        return ();
    }
    let (reversed_index) = bit_reverse_u64(queries[0] * shift);

    // Compute the x value of the query in the evaluation domain coset:
    //   FIELD_GENERATOR * eval_generator ^ reversed_index.
    let (point) = pow(eval_generator, reversed_index);
    let point = point * FIELD_GENERATOR;
    assert points[0] = point;
    return queries_to_points_inner(
        n_queries=n_queries - 1,
        queries=&queries[1],
        points=&points[1],
        shift=shift,
        eval_generator=eval_generator,
    );
}
