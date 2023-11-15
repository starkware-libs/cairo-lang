from starkware.cairo.common.cairo_secp.bigint3 import BigInt3
from starkware.cairo.common.secp256r1.constants import BASE, D2_BOUND

// Returns a BigInt3 instance whose value is controlled by a prover hint.
//
// Soundness guarantee:
// d0, d1 limbs are in the range [0, 2 * BASE).
// d2 limb in the range [0, D2_BOUND)
// Completeness guarantee (honest prover): the value is in reduced form and in particular,
// d0, d1 limbs are in the range [0, BASE).
// each limb is in the range [0, D2_BOUND).
//
// Implicit arguments:
//   range_check_ptr - range check builtin pointer.
//
// Hint arguments: value.
func nondet_bigint3{range_check_ptr}() -> (res: BigInt3) {
    let res: BigInt3 = [cast(ap + 4, BigInt3*)];
    %{
        from starkware.cairo.common.cairo_secp.secp_utils import split

        segments.write_arg(ids.res.address_, split(value))
    %}
    // Bound d0, d1 (each) in [0, 2*BASE).
    assert [range_check_ptr] = res.d0 + res.d1 + (2 ** 128 - 2 * BASE);
    // Bound d2 in [0, D2_BOUND).
    assert [range_check_ptr + 1] = res.d2 + (2 ** 128 - D2_BOUND);
    let range_check_ptr = range_check_ptr + 2;

    // Prepare the result at the end of the stack.
    tempvar range_check_ptr = range_check_ptr + 3;
    [range_check_ptr - 3] = res.d0, ap++;
    [range_check_ptr - 2] = res.d1, ap++;
    [range_check_ptr - 1] = res.d2, ap++;
    static_assert &res + BigInt3.SIZE == ap;
    return (res=res);
}
