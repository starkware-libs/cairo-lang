from starkware.cairo.builtin_selection.inner_select_builtins import inner_select_builtins

// A wrapper for 'inner_select_builtins' function (see its documentation).
func select_builtins(
    n_builtins,
    all_encodings: felt*,
    all_ptrs: felt*,
    n_selected_builtins,
    selected_encodings: felt*,
    selected_ptrs: felt*,
) {
    %{ vm_enter_scope({'n_selected_builtins': ids.n_selected_builtins}) %}
    let (selected_encodings_end) = inner_select_builtins(
        all_encodings=all_encodings,
        all_ptrs=all_ptrs,
        selected_encodings=selected_encodings,
        selected_ptrs=selected_ptrs,
        n_builtins=n_builtins,
    );
    %{ vm_exit_scope() %}
    // Assert that the correct number of builtins was selected.
    assert n_selected_builtins = selected_encodings_end - selected_encodings;

    return ();
}
