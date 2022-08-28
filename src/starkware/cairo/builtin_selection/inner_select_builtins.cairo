// An helper function to extract selected_ptrs from all_ptrs according to the builtin encodings
// that appear in the selected_encodings list.
// The caller needs to pass n_selected_builtins as a hint.
// Returns a pointer to the next memory slot after the selected_encodings list, see "Assumptions".
//
// For example, given the following setup:
//   - all_encodings points to ["output", "pedersen", "range-check"].
//   - selected_encodings points to ["output", "range-check"]
//   - all_ptrs points to [output_ptr, pedersen_ptr, range_check_ptr]
//   - The caller asserts that the return value is selected_encodings + n_selected_builtins(2).
// The function will check that selected_encodings points to [output_ptr, range_check_ptr].
//
// n_builtins is the length of the list of *all pointers*.
// Assumptions:
// * The caller has to check that n_selected_builtins = selected_encodings_end - selected_encodings.
// * All lists are sorted according to the order of builtins input in Cairo programs.
// * len(selected_encodings) <= len(all_encodings) == len(all_ptrs).
func inner_select_builtins(
    all_encodings: felt*,
    all_ptrs: felt*,
    selected_encodings: felt*,
    selected_ptrs: felt*,
    n_builtins,
) -> (selected_encodings_end: felt*) {
    // Number of memory cells used when n_builtins = 0.
    const FUNC_MEMORY_NO_BUILTINS = 1;
    // Number of memory cells used *in a single iteration* when n_builtins > 0.
    const FUNC_MEMORY_WITH_BUILTINS = 10;

    if (n_builtins == 0) {
        // Return a pointer to the end of the selected_encodings list.
        return (selected_encodings_end=selected_encodings);
    }

    alloc_locals;
    // select_builtin equals 1 if the first builtin should be selected and 0 otherwise.
    local select_builtin;
    %{
        # A builtin should be selected iff its encoding appears in the selected encodings list
        # and the list wasn't exhausted.
        # Note that testing inclusion by a single comparison is possible since the lists are sorted.
        ids.select_builtin = int(
          n_selected_builtins > 0 and memory[ids.selected_encodings] == memory[ids.all_encodings])
        if ids.select_builtin:
          n_selected_builtins = n_selected_builtins - 1
    %}
    // Verify that select_builtin is a bit.
    select_builtin = select_builtin * select_builtin;

    local curr_builtin_encoding = [all_encodings];
    local curr_builtin_ptr = [all_ptrs];

    if (select_builtin != 0) {
        // Verify that the current builtin is indeed selected, by asserting that its encoding
        // appears in the selected encodings list.
        curr_builtin_encoding = [selected_encodings];
        // Copy the current builtin pointer between selected_ptrs and all_ptrs.
        curr_builtin_ptr = [selected_ptrs];
    }

    // Advance all list pointers accordingly and continue selection by calling inner_select_builtins
    // recursively.
    // Lists of selected builtins/encodings should advance only if the current builtin was selected.
    return inner_select_builtins(
        all_encodings=all_encodings + 1,
        all_ptrs=all_ptrs + 1,
        selected_encodings=selected_encodings + select_builtin,
        selected_ptrs=selected_ptrs + select_builtin,
        n_builtins=n_builtins - 1,
    );
}
