from starkware.cairo.common.math import assert_le_felt, assert_lt_felt

const RC_BOUND = 2 ** 128;

// Returns 1 if value != 0. Returns 0 otherwise.
@known_ap_change
func is_not_zero(value) -> felt {
    if (value == 0) {
        return 0;
    }

    return 1;
}

// Returns 1 if a >= 0 (or more precisely 0 <= a < RANGE_CHECK_BOUND).
// Returns 0 otherwise.
@known_ap_change
func is_nn{range_check_ptr}(a) -> felt {
    %{ memory[ap] = 0 if 0 <= (ids.a % PRIME) < range_check_builtin.bound else 1 %}
    jmp out_of_range if [ap] != 0, ap++;
    [range_check_ptr] = a;
    ap += 20;
    let range_check_ptr = range_check_ptr + 1;
    return 1;

    out_of_range:
    %{ memory[ap] = 0 if 0 <= ((-ids.a - 1) % PRIME) < range_check_builtin.bound else 1 %}
    jmp need_felt_comparison if [ap] != 0, ap++;
    assert [range_check_ptr] = (-a) - 1;
    ap += 17;
    let range_check_ptr = range_check_ptr + 1;
    return 0;

    need_felt_comparison:
    assert_le_felt(RC_BOUND, a);
    return 0;
}

// Returns 1 if a <= b (or more precisely 0 <= b - a < RANGE_CHECK_BOUND).
// Returns 0 otherwise.
@known_ap_change
func is_le{range_check_ptr}(a, b) -> felt {
    return is_nn(b - a);
}

// Returns 1 if 0 <= a <= b < RANGE_CHECK_BOUND.
// Returns 0 otherwise.
//
// Assumption: b < RANGE_CHECK_BOUND.
@known_ap_change
func is_nn_le{range_check_ptr}(a, b) -> felt {
    let res = is_nn(a);
    if (res == 0) {
        ap += 25;
        return res;
    }
    return is_nn(b - a);
}

// Returns 1 if value is in the range [lower, upper).
// Returns 0 otherwise.
// Assumptions:
//   upper - lower <= RANGE_CHECK_BOUND.
@known_ap_change
func is_in_range{range_check_ptr}(value, lower, upper) -> felt {
    let res = is_le(lower, value);
    if (res == 0) {
        ap += 26;
        return res;
    }
    return is_nn(upper - 1 - value);
}

// Checks if the unsigned integer lift (as a number in the range [0, PRIME)) of a is lower than
// or equal to that of b.
// See split_felt() for more details.
// Returns 1 if true, 0 otherwise.
@known_ap_change
func is_le_felt{range_check_ptr}(a, b) -> felt {
    %{ memory[ap] = 0 if (ids.a % PRIME) <= (ids.b % PRIME) else 1 %}
    jmp not_le if [ap] != 0, ap++;
    ap += 6;
    assert_le_felt(a, b);
    return 1;

    not_le:
    assert_lt_felt(b, a);
    return 0;
}
