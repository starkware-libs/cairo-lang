from starkware.cairo.common.pow import pow

// Computes the correct value for the diluted component product.
func get_diluted_prod{range_check_ptr}(n_bits: felt, spacing: felt, z: felt, alpha: felt) -> (
    res: felt
) {
    alloc_locals;
    let (diff_multiplier) = pow(2, spacing);
    let (p, q) = get_diluted_prod_inner(
        n_bits=n_bits - 1,
        x=1,
        diff_x=diff_multiplier - 2,
        diff_multiplier=diff_multiplier,
        z=z,
        p=1 + z,
        q=1,
    );
    return (res=p + q * alpha);
}

// The cumulative value is defined using the next recursive formula:
//   r_1 = 1, r_{j+1} = r_j * (1 + z * u_j) + alpha * u_j^2
// where u_j = Dilute(j, spacing, n_bits) - Dilute(j-1, spacing, n_bits)
// and we want to compute the final value r_{2^n_bits}.
// Note that u_j depends only on the number of trailing zeros in the binary representation of j.
// Specifically, u_{(1+2k)*2^i} = u_{2^i} = u_{2^{i-1}} + 2^{i*spacing} - 2^{(i-1)*spacing + 1}.
//
// The recursive formula can be reduced to a nonrecursive form:
//   r_j = prod_{n=1..j-1}(1+z*u_n) + alpha*sum_{n=1..j-1}(u_n^2 * prod_{m=n+1..j-1}(1+z*u_m))
//
// We rewrite this equation to generate a recursive formula that converges in log(j) steps:
// Denote:
//   p_i = prod_{n=1..2^i-1}(1+z*u_n)
//   q_i = sum_{n=1..2^i-1}(u_n^2 * prod_{m=n+1..2^i-1}(1+z*u_m))
//   x_i = u_{2^i}.
//
// Clearly
//   r_{2^i} = p_i + alpha * q_i.
// Moreover,
//   p_i = p_{i-1} * (1 + z * x_{i-1}) * p_{i-1}
//   q_i = q_{i-1} * (1 + z * x_{i-1}) * p_{i-1} + x_{i-1}^2 * p_{i-1} + q_{i-1}
//
// Now we can compute p_{n_bits} and q_{n_bits} in just n_bits recursive steps and we are done.
func get_diluted_prod_inner(
    n_bits: felt, x: felt, diff_x: felt, diff_multiplier: felt, z: felt, p: felt, q: felt
) -> (p: felt, q: felt) {
    if (n_bits == 0) {
        return (p=p, q=q);
    }
    tempvar x = x + diff_x;
    let diff_x = diff_x * diff_multiplier;
    tempvar x_p = x * p;
    tempvar y = p + z * x_p;
    let q = q * y + x * x_p + q;
    let p = p * y;
    return get_diluted_prod_inner(
        n_bits=n_bits - 1, x=x, diff_x=diff_x, diff_multiplier=diff_multiplier, z=z, p=p, q=q
    );
}
