import os

import pytest

from starkware.cairo.common.test_utils import create_memory_struct
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.cairo.lang.vm.cairo_runner import CairoRunner


@ pytest.mark.parametrize(
    'builtin_selection_indicators', [
        [True, True, True, True], [False, False, False, False], [True, False, False, True]],
    ids=['select_all_builtins', 'do_not_select_any_builtin', 'select_output_and_ecdsa_builtins'])
def test_select_input_builtins(builtin_selection_indicators):
    """
    Tests the select_input_builtins Cairo function: calls the function with different builtins
    selection and checks that the function returns the expected builtin pointers.
    """
    # Setup runner.
    cairo_file = os.path.join(os.path.dirname(__file__), 'select_input_builtins.cairo')
    runner = CairoRunner.from_file(cairo_file, DEFAULT_PRIME)
    runner.initialize_segments()

    output_base = runner.segments.add()
    hash_base = runner.segments.add()
    range_check_base = runner.segments.add()
    signature_base = runner.segments.add()

    # Setup function.
    builtins_encoding = {
        builtin: int.from_bytes(builtin.encode('ascii'), 'big')
        for builtin in ['output', 'pedersen', 'range_check', 'ecdsa']}
    all_builtins = [output_base, hash_base, range_check_base, signature_base]

    selected_builtin_encodings = [
        builtin_encoding for builtin_encoding, is_builtin_selected in zip(
            builtins_encoding.values(), builtin_selection_indicators)
        if is_builtin_selected]

    selected_builtins = [
        builtin for builtin, is_builtin_selected in zip(all_builtins, builtin_selection_indicators)
        if is_builtin_selected]

    all_encodings = create_memory_struct(runner, builtins_encoding.values())
    selected_encodings = create_memory_struct(runner, selected_builtin_encodings)
    all_ptrs = create_memory_struct(runner, all_builtins)
    n_builtins = len(selected_builtin_encodings)

    args = [all_encodings, all_ptrs, selected_encodings, n_builtins]
    end = runner.initialize_function_entrypoint('select_input_builtins', args)

    # Setup context.
    runner.initialize_vm(hint_locals={})
    runner.run_until_pc(end)
    runner.end_run()

    # Check result.
    context = runner.vm.run_context

    # 'select_input_builtins' should return the pointers to the selected builtins.
    return_values_addr = context.ap - n_builtins
    assert [
        context.memory[return_values_addr + i] for i in range(len(selected_builtins))] == \
        selected_builtins
