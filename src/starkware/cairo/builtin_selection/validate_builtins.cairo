// Validates that the builtin pointer of a single builtin was advanced correctly.
// The inputs are:
//   The previous builtin pointer.
//   The new builtin pointer.
//   The size of the builtin instances.
// The function validates that the difference between the new builtin pointer and the old builtin
// pointer is a positive integer divisible by the given builtin instance size.
//
// The function consumes 1 range check instance starting at range_check_ptr and returns the
// updated range check pointer.
func validate_builtin{range_check_ptr}(
    prev_builtin_ptr: felt*, new_builtin_ptr: felt*, builtin_instance_size: felt
) {
    // Check that the difference is positive and divisible by builtin_instance_size by checking that
    // 0 <= div_res < RANGE_CHECK_BOUND and diff = div_res * builtin_instance_size.
    tempvar diff = new_builtin_ptr - prev_builtin_ptr;
    tempvar div_res = diff / builtin_instance_size;
    div_res = [range_check_ptr];
    let range_check_ptr = range_check_ptr + 1;
    return ();
}

// Validates that the builtin pointers were advanced correctly.
//
// The inputs are:
//   The previous list of builtin pointers.
//   The new list of builtin pointers.
//   The sizes of the builtin instances.
//   The number of builtins.
//
// For each builtin the function validates that the difference between the new builtin pointer and
// the old builtin pointer is a nonnegative integer divisible by the corresponding builtin
// instance size.
//
// The function consumes n_builtins range check instances starting at range_check_ptr and returns
// the updated range check pointer.
func validate_builtins{range_check_ptr}(
    prev_builtin_ptrs: felt*, new_builtin_ptrs: felt*, builtin_instance_sizes: felt*, n_builtins
) {
    if (n_builtins == 0) {
        return ();
    }

    validate_builtin(
        prev_builtin_ptr=cast([prev_builtin_ptrs], felt*),
        new_builtin_ptr=cast([new_builtin_ptrs], felt*),
        builtin_instance_size=[builtin_instance_sizes],
    );

    return validate_builtins(
        prev_builtin_ptrs=prev_builtin_ptrs + 1,
        new_builtin_ptrs=new_builtin_ptrs + 1,
        builtin_instance_sizes=builtin_instance_sizes + 1,
        n_builtins=n_builtins - 1,
    );
}
