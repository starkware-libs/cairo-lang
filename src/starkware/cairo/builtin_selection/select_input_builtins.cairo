from starkware.cairo.builtin_selection.inner_select_builtins import inner_select_builtins
from starkware.cairo.common.registers import get_fp_and_pc

// A wrapper for 'inner_select_builtins' function (see its documentation).
// Returns the selected builtin pointers (e.g., if n_selected_builtins=2, returns two values).
func select_input_builtins(
    all_encodings: felt*,
    all_ptrs: felt*,
    n_all_builtins: felt,
    selected_encodings: felt*,
    n_selected_builtins,
) {
    // Number of memory cells used, without taking the inner function memory into account.
    const FUNC_MEMORY_WITHOUT_INNER_FUNC = 11;
    const INNER_FUNC_MEMORY_PER_ITERATION = inner_select_builtins.FUNC_MEMORY_WITH_BUILTINS;
    const INNER_FUNC_MEMORY_FINAL_ITERATION = inner_select_builtins.FUNC_MEMORY_NO_BUILTINS;
    // 'inner_select_builtins' has n_all_builtins iterations, until the final halting one, when
    // called with n_builtins = n_all_builtins.
    let inner_func_memory = n_all_builtins * INNER_FUNC_MEMORY_PER_ITERATION +
        INNER_FUNC_MEMORY_FINAL_ITERATION;
    let total_func_memory = inner_func_memory + FUNC_MEMORY_WITHOUT_INNER_FUNC;

    let frame = call get_fp_and_pc;
    // The selected builtin pointers are the return values at the end of the function memory.
    let selected_ptrs = frame.fp_val + total_func_memory;
    %{ vm_enter_scope({'n_selected_builtins': ids.n_selected_builtins}) %}
    let inner_ret = inner_select_builtins(
        all_encodings=all_encodings,
        all_ptrs=all_ptrs,
        selected_encodings=selected_encodings,
        selected_ptrs=selected_ptrs,
        n_builtins=n_all_builtins,
    );
    %{ vm_exit_scope() %}
    // Assert that the correct number of builtins was selected.
    n_selected_builtins = inner_ret.selected_encodings_end - selected_encodings;

    ap += n_selected_builtins;
    ret;
}
