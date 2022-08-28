from starkware.cairo.common.bool import FALSE, TRUE

// Inline functions with no locals.

// Verifies that value != 0. The proof will fail otherwise.
func assert_not_zero(value) {
    %{
        from starkware.cairo.common.math_utils import assert_integer
        assert_integer(ids.value)
        assert ids.value % PRIME != 0, f'assert_not_zero failed: {ids.value} = 0.'
    %}
    if (value == 0) {
        // If value == 0, add an unsatisfiable requirement.
        value = 1;
    }

    return ();
}

// Verifies that a != b. The proof will fail otherwise.
func assert_not_equal(a, b) {
    %{
        from starkware.cairo.lang.vm.relocatable import RelocatableValue
        both_ints = isinstance(ids.a, int) and isinstance(ids.b, int)
        both_relocatable = (
            isinstance(ids.a, RelocatableValue) and isinstance(ids.b, RelocatableValue) and
            ids.a.segment_index == ids.b.segment_index)
        assert both_ints or both_relocatable, \
            f'assert_not_equal failed: non-comparable values: {ids.a}, {ids.b}.'
        assert (ids.a - ids.b) % PRIME != 0, f'assert_not_equal failed: {ids.a} = {ids.b}.'
    %}
    if (a == b) {
        // If a == b, add an unsatisfiable requirement.
        a = a + 1;
    }

    return ();
}

// Verifies that a >= 0 (or more precisely 0 <= a < RANGE_CHECK_BOUND).
func assert_nn{range_check_ptr}(a) {
    %{
        from starkware.cairo.common.math_utils import assert_integer
        assert_integer(ids.a)
        assert 0 <= ids.a % PRIME < range_check_builtin.bound, f'a = {ids.a} is out of range.'
    %}
    a = [range_check_ptr];
    let range_check_ptr = range_check_ptr + 1;
    return ();
}

// Verifies that a <= b (or more precisely 0 <= b - a < RANGE_CHECK_BOUND).
func assert_le{range_check_ptr}(a, b) {
    assert_nn(b - a);
    return ();
}

// Verifies that a <= b - 1 (or more precisely 0 <= b - 1 - a < RANGE_CHECK_BOUND).
func assert_lt{range_check_ptr}(a, b) {
    assert_le(a, b - 1);
    return ();
}

// Verifies that 0 <= a <= b.
//
// Prover assumption: b < RANGE_CHECK_BOUND.
//
// This function is still sound without the prover assumptions. In that case, it is guaranteed
// that a < RANGE_CHECK_BOUND and b < 2 * RANGE_CHECK_BOUND.
func assert_nn_le{range_check_ptr}(a, b) {
    assert_nn(a);
    assert_le(a, b);
    return ();
}

// Asserts that value is in the range [lower, upper).
// Or more precisely:
// (0 <= value - lower < RANGE_CHECK_BOUND) and (0 <= upper - 1 - value < RANGE_CHECK_BOUND).
//
// Prover assumption: 0 <= upper - lower <= RANGE_CHECK_BOUND.
func assert_in_range{range_check_ptr}(value, lower, upper) {
    assert_le(lower, value);
    assert_le(value, upper - 1);
    return ();
}

// Asserts that 'value' is in the range [0, 2**250).
@known_ap_change
func assert_250_bit{range_check_ptr}(value) {
    const UPPER_BOUND = 2 ** 250;
    const SHIFT = 2 ** 128;
    const HIGH_BOUND = UPPER_BOUND / SHIFT;

    let low = [range_check_ptr];
    let high = [range_check_ptr + 1];

    %{
        from starkware.cairo.common.math_utils import as_int

        # Correctness check.
        value = as_int(ids.value, PRIME) % PRIME
        assert value < ids.UPPER_BOUND, f'{value} is outside of the range [0, 2**250).'

        # Calculation for the assertion.
        ids.high, ids.low = divmod(ids.value, ids.SHIFT)
    %}

    assert [range_check_ptr + 2] = HIGH_BOUND - 1 - high;

    // The assert below guarantees that
    //   value = high * SHIFT + low <= (HIGH_BOUND - 1) * SHIFT + 2**128 - 1 =
    //   HIGH_BOUND * SHIFT - SHIFT + SHIFT - 1 = 2**250 - 1.
    assert value = high * SHIFT + low;

    let range_check_ptr = range_check_ptr + 3;
    return ();
}

// Splits the unsigned integer lift of a field element into the higher 128 bit and lower 128 bit.
// The unsigned integer lift is the unique integer in the range [0, PRIME) that represents the field
// element.
// For example, if value=17 * 2^128 + 8, then high=17 and low=8.
@known_ap_change
func split_felt{range_check_ptr}(value) -> (high: felt, low: felt) {
    // Note: the following code works because PRIME - 1 is divisible by 2**128.
    const MAX_HIGH = (-1) / 2 ** 128;
    const MAX_LOW = 0;

    // Guess the low and high parts of the integer.
    let low = [range_check_ptr];
    let high = [range_check_ptr + 1];
    let range_check_ptr = range_check_ptr + 2;

    %{
        from starkware.cairo.common.math_utils import assert_integer
        assert ids.MAX_HIGH < 2**128 and ids.MAX_LOW < 2**128
        assert PRIME - 1 == ids.MAX_HIGH * 2**128 + ids.MAX_LOW
        assert_integer(ids.value)
        ids.low = ids.value & ((1 << 128) - 1)
        ids.high = ids.value >> 128
    %}
    assert value = high * (2 ** 128) + low;
    if (high == MAX_HIGH) {
        assert_le(low, MAX_LOW);
    } else {
        assert_le(high, MAX_HIGH - 1);
    }
    return (high=high, low=low);
}

// Asserts that the unsigned integer lift (as a number in the range [0, PRIME)) of a is lower than
// or equal to that of b.
@known_ap_change
func assert_le_felt{range_check_ptr}(a, b) {
    // ceil(PRIME / 3 / 2 ** 128).
    const PRIME_OVER_3_HIGH = 0x2aaaaaaaaaaaab05555555555555556;
    // ceil(PRIME / 2 / 2 ** 128).
    const PRIME_OVER_2_HIGH = 0x4000000000000088000000000000001;
    // The numbers [0, a, b, PRIME - 1] should be ordered. To prove that, we show that two of the
    // 3 arcs {0 -> a, a -> b, b -> PRIME - 1} are small:
    //   One is less than PRIME / 3 + 2 ** 129.
    //   Another is less than PRIME / 2 + 2 ** 129.
    // Since the sum of the lengths of these two arcs is less than PRIME, there is no wrap-around.
    %{
        import itertools

        from starkware.cairo.common.math_utils import assert_integer
        assert_integer(ids.a)
        assert_integer(ids.b)
        a = ids.a % PRIME
        b = ids.b % PRIME
        assert a <= b, f'a = {a} is not less than or equal to b = {b}.'

        # Find an arc less than PRIME / 3, and another less than PRIME / 2.
        lengths_and_indices = [(a, 0), (b - a, 1), (PRIME - 1 - b, 2)]
        lengths_and_indices.sort()
        assert lengths_and_indices[0][0] <= PRIME // 3 and lengths_and_indices[1][0] <= PRIME // 2
        excluded = lengths_and_indices[2][1]

        memory[ids.range_check_ptr + 1], memory[ids.range_check_ptr + 0] = (
            divmod(lengths_and_indices[0][0], ids.PRIME_OVER_3_HIGH))
        memory[ids.range_check_ptr + 3], memory[ids.range_check_ptr + 2] = (
            divmod(lengths_and_indices[1][0], ids.PRIME_OVER_2_HIGH))
    %}
    // Guess two arc lengths.
    tempvar arc_short = [range_check_ptr] + [range_check_ptr + 1] * PRIME_OVER_3_HIGH;
    tempvar arc_long = [range_check_ptr + 2] + [range_check_ptr + 3] * PRIME_OVER_2_HIGH;
    let range_check_ptr = range_check_ptr + 4;

    // First, choose which arc to exclude from {0 -> a, a -> b, b -> PRIME - 1}.
    // Then, to compare the set of two arc lengths, compare their sum and product.
    let arc_sum = arc_short + arc_long;
    let arc_prod = arc_short * arc_long;

    // Exclude "0 -> a".
    %{ memory[ap] = 1 if excluded != 0 else 0 %}
    jmp skip_exclude_a if [ap] != 0, ap++;
    assert arc_sum = (-1) - a;
    assert arc_prod = (a - b) * (1 + b);
    return ();

    // Exclude "a -> b".
    skip_exclude_a:
    %{ memory[ap] = 1 if excluded != 1 else 0 %}
    jmp skip_exclude_b_minus_a if [ap] != 0, ap++;
    tempvar m1mb = (-1) - b;
    assert arc_sum = a + m1mb;
    assert arc_prod = a * m1mb;
    return ();

    // Exclude "b -> PRIME - 1".
    skip_exclude_b_minus_a:
    %{ assert excluded == 2 %}
    assert arc_sum = b;
    assert arc_prod = a * (b - a);
    ap += 2;
    return ();
}

// Asserts that the unsigned integer lift (as a number in the range [0, PRIME)) of a is lower than
// that of b.
@known_ap_change
func assert_lt_felt{range_check_ptr}(a, b) {
    %{
        from starkware.cairo.common.math_utils import assert_integer
        assert_integer(ids.a)
        assert_integer(ids.b)
        assert (ids.a % PRIME) < (ids.b % PRIME), \
            f'a = {ids.a % PRIME} is not less than b = {ids.b % PRIME}.'
    %}
    if (a == b) {
        // If a == b, add an unsatisfiable requirement.
        a = a + 1;
    }
    assert_le_felt(a, b);
    return ();
}

// Returns the absolute value of value.
// Prover asumption: -rc_bound < value < rc_bound.
@known_ap_change
func abs_value{range_check_ptr}(value) -> felt {
    tempvar is_positive: felt;
    %{
        from starkware.cairo.common.math_utils import is_positive
        ids.is_positive = 1 if is_positive(
            value=ids.value, prime=PRIME, rc_bound=range_check_builtin.bound) else 0
    %}
    if (is_positive == 0) {
        tempvar new_range_check_ptr = range_check_ptr + 1;
        tempvar abs_value = value * (-1);
        [range_check_ptr] = abs_value;
        let range_check_ptr = new_range_check_ptr;
        return abs_value;
    } else {
        [range_check_ptr] = value;
        let range_check_ptr = range_check_ptr + 1;
        return value;
    }
}

// Returns the sign of value: -1, 0 or 1.
// Prover asumption: -rc_bound < value < rc_bound.
@known_ap_change
func sign{range_check_ptr}(value) -> felt {
    if (value == 0) {
        ap += 2;
        return 0;
    }

    tempvar is_positive: felt;
    %{
        from starkware.cairo.common.math_utils import is_positive
        ids.is_positive = 1 if is_positive(
            value=ids.value, prime=PRIME, rc_bound=range_check_builtin.bound) else 0
    %}
    if (is_positive == 0) {
        assert [range_check_ptr] = value * (-1);
        let range_check_ptr = range_check_ptr + 1;
        return -1;
    } else {
        ap += 1;
        [range_check_ptr] = value;
        let range_check_ptr = range_check_ptr + 1;
        return 1;
    }
}

// Returns q and r such that:
//  0 <= q < rc_bound, 0 <= r < div and value = q * div + r.
//
// Assumption: 0 < div <= PRIME / rc_bound.
// Prover assumption: value / div < rc_bound.
//
// The value of div is restricted to make sure there is no overflow.
// q * div + r < (q + 1) * div <= rc_bound * (PRIME / rc_bound) = PRIME.
func unsigned_div_rem{range_check_ptr}(value, div) -> (q: felt, r: felt) {
    let r = [range_check_ptr];
    let q = [range_check_ptr + 1];
    let range_check_ptr = range_check_ptr + 2;
    %{
        from starkware.cairo.common.math_utils import assert_integer
        assert_integer(ids.div)
        assert 0 < ids.div <= PRIME // range_check_builtin.bound, \
            f'div={hex(ids.div)} is out of the valid range.'
        ids.q, ids.r = divmod(ids.value, ids.div)
    %}
    assert_le(r, div - 1);

    assert value = q * div + r;
    return (q, r);
}

// Returns q and r such that. -bound <= q < bound, 0 <= r < div and value = q * div + r.
// value < PRIME / 2 is considered positive and value > PRIME / 2 is considered negative.
//
// Assumptions:
//   0 < div <= PRIME / (rc_bound)
//   bound <= rc_bound / 2.
// Prover assumption:   -bound <= value / div < bound.
//
// The values of div and bound are restricted to make sure there is no overflow.
// q * div + r <  (q + 1) * div <=  rc_bound / 2 * (PRIME / rc_bound)
// q * div + r >=  q * div      >= -rc_bound / 2 * (PRIME / rc_bound).
func signed_div_rem{range_check_ptr}(value, div, bound) -> (q: felt, r: felt) {
    let r = [range_check_ptr];
    let biased_q = [range_check_ptr + 1];  // == q + bound.
    let range_check_ptr = range_check_ptr + 2;
    %{
        from starkware.cairo.common.math_utils import as_int, assert_integer

        assert_integer(ids.div)
        assert 0 < ids.div <= PRIME // range_check_builtin.bound, \
            f'div={hex(ids.div)} is out of the valid range.'

        assert_integer(ids.bound)
        assert ids.bound <= range_check_builtin.bound // 2, \
            f'bound={hex(ids.bound)} is out of the valid range.'

        int_value = as_int(ids.value, PRIME)
        q, ids.r = divmod(int_value, ids.div)

        assert -ids.bound <= q < ids.bound, \
            f'{int_value} / {ids.div} = {q} is out of the range [{-ids.bound}, {ids.bound}).'

        ids.biased_q = q + ids.bound
    %}
    let q = biased_q - bound;
    assert value = q * div + r;
    assert_le(r, div - 1);
    assert_le(biased_q, 2 * bound - 1);
    return (q, r);
}

// Splits the given (unsigned) value into n "limbs", where each limb is in the range [0, bound),
// as follows:
//   value = x[0] + x[1] * base + x[2] * base**2 + ... + x[n - 1] * base**(n - 1).
// bound must be less than the range check bound (2**128).
// Note that bound may be smaller than base, in which case the function will fail if there is a
// limb which is >= bound.
// Assumptions:
//   1 < bound <= base
//   base**n < field characteristic.
func split_int{range_check_ptr}(value, n, base, bound, output: felt*) {
    if (n == 0) {
        %{ assert ids.value == 0, 'split_int(): value is out of range.' %}
        assert value = 0;
        return ();
    }

    %{
        memory[ids.output] = res = (int(ids.value) % PRIME) % ids.base
        assert res < ids.bound, f'split_int(): Limb {res} is out of range.'
    %}
    tempvar low_part = [output];
    assert_nn_le(low_part, bound - 1);

    return split_int(
        value=(value - low_part) / base, n=n - 1, base=base, bound=bound, output=output + 1
    );
}

// Returns the floor value of the square root of the given value.
// Assumptions: 0 <= value < 2**250.
@known_ap_change
func sqrt{range_check_ptr}(value) -> felt {
    alloc_locals;
    local root: felt;

    %{
        from starkware.python.math_utils import isqrt
        value = ids.value % PRIME
        assert value < 2 ** 250, f"value={value} is outside of the range [0, 2**250)."
        assert 2 ** 250 < PRIME
        ids.root = isqrt(value)
    %}

    assert_nn_le(root, 2 ** 125 - 1);
    tempvar root_plus_one = root + 1;
    assert_in_range(value, root * root, root_plus_one * root_plus_one);

    return root;
}

// Computes the evaluation of a polynomial on the given point.
func horner_eval(n_coefficients: felt, coefficients: felt*, point: felt) -> (res: felt) {
    if (n_coefficients == 0) {
        return (res=0);
    }

    let (n_minus_one_res) = horner_eval(
        n_coefficients=n_coefficients - 1, coefficients=&coefficients[1], point=point
    );
    return (res=n_minus_one_res * point + coefficients[0]);
}

// Returns TRUE if `x` is a quadratic residue modulo the STARK prime. Returns FALSE otherwise.
// Returns TRUE on 0.
@known_ap_change
func is_quad_residue(x: felt) -> felt {
    alloc_locals;
    local y;
    %{
        from starkware.crypto.signature.signature import FIELD_PRIME
        from starkware.python.math_utils import div_mod, is_quad_residue, sqrt

        x = ids.x
        if is_quad_residue(x, FIELD_PRIME):
            ids.y = sqrt(x, FIELD_PRIME)
        else:
            ids.y = sqrt(div_mod(x, 3, FIELD_PRIME), FIELD_PRIME)
    %}
    // Relies on the fact that 3 is not a quadratic residue modulo the prime, so for every field
    // element x, either:
    //   * x is a quadratic residue and there exists y such that y^2 = x.
    //   * x is not a quadratic residue and there exists y such that 3 * y^2 = x.
    tempvar y_squared = y * y;
    if (y_squared == x) {
        ap += 1;
        return TRUE;
    } else {
        assert 3 * y_squared = x;
        return FALSE;
    }
}
