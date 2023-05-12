import os

import pytest

from starkware.cairo.common.cairo_function_runner import CairoFunctionRunner
from starkware.cairo.lang.builtins.all_builtins import ALL_BUILTINS
from starkware.cairo.lang.cairo_constants import DEFAULT_PRIME
from starkware.python.utils import from_bytes


@pytest.mark.parametrize(
    "builtin_selection_indicators",
    [
        [True, True, True, True, True],
        [False, False, False, False, False],
        [True, False, False, True, False],
    ],
    ids=["select_all_builtins", "do_not_select_any_builtin", "select_output_and_ecdsa_builtins"],
)
def test_select_input_builtins(builtin_selection_indicators):
    """
    Tests the select_input_builtins Cairo function: calls the function with different builtins
    selection and checks that the function returns the expected builtin pointers.
    """
    # Setup runner.
    cairo_file = os.path.join(os.path.dirname(__file__), "select_input_builtins.cairo")
    runner = CairoFunctionRunner.from_file(cairo_file, DEFAULT_PRIME)
    runner.initialize_segments()
    builtin_bases = [runner.segments.add() for builtin in ALL_BUILTINS]

    # Setup function.
    builtins_encoding = {builtin: from_bytes(builtin.encode("ascii")) for builtin in ALL_BUILTINS}

    selected_builtin_encodings = [
        builtin_encoding
        for builtin_encoding, is_builtin_selected in zip(
            builtins_encoding.values(), builtin_selection_indicators
        )
        if is_builtin_selected
    ]

    all_encodings = list(builtins_encoding.values())
    n_selected_builtins = len(selected_builtin_encodings)

    runner.run(
        "select_input_builtins",
        all_encodings=all_encodings,
        all_ptrs=builtin_bases,
        n_all_builtins=len(all_encodings),
        selected_encodings=selected_builtin_encodings,
        n_selected_builtins=n_selected_builtins,
    )

    # Check result.
    # 'select_input_builtins' should return the pointers to the selected builtins.
    expected_selected_builtins = [
        builtin
        for builtin, is_builtin_selected in zip(builtin_bases, builtin_selection_indicators)
        if is_builtin_selected
    ]
    assert expected_selected_builtins == runner.get_return_values(n_ret=n_selected_builtins)
