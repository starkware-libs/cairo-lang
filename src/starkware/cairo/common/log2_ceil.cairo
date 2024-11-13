from starkware.cairo.common.math import assert_in_range, assert_not_zero
from starkware.cairo.common.pow import pow

// Returns the ceil value of the log2 of the given value.
// Enforces that 1 <= value <= RANGE_CHECK_BOUND.
func log2_ceil{range_check_ptr}(value: felt) -> felt {
    alloc_locals;
    assert_not_zero(value);
    if (value == 1) {
        return 0;
    }

    local res;
    %{
        from starkware.python.math_utils import log2_ceil
        ids.res = log2_ceil(ids.value)
    %}

    // Verify that 1 <= 2**(res - 1) < value <= 2**res <= RANGE_CHECK_BOUND.
    // The RANGE_CHECK_BOUND bound is required by the `assert_in_range` function.
    assert_in_range(res, 1, 128 + 1);
    let (lower_bound) = pow(2, res - 1);
    let min = lower_bound + 1;
    let max = 2 * lower_bound;
    assert_in_range(value, min, max + 1);

    return res;
}
