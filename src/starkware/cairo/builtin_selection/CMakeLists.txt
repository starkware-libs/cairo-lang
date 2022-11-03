python_lib(cairo_builtin_selection_lib
    PREFIX starkware/cairo/builtin_selection

    FILES
    inner_select_builtins.cairo
    select_builtins.cairo
    select_input_builtins.cairo
    validate_builtins.cairo
)

full_python_test(cairo_builtin_selection_test
    PREFIX starkware/cairo/builtin_selection
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/cairo/builtin_selection

    FILES
    select_input_builtins_test.py
    validate_builtins_test.py

    LIBS
    cairo_builtin_selection_lib
    cairo_common_lib
    cairo_common_test_utils_lib
    cairo_compile_lib
    cairo_test_utils
    cairo_vm_lib
    starkware_crypto_lib
    starkware_python_utils_lib
    pip_pytest
)
