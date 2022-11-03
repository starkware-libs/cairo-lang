full_python_test(cairo_run_builtins_range_check_test
    PREFIX starkware/cairo/lang/builtins/range_check
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/cairo/lang/builtins/range_check

    FILES
    range_check_builtin_runner_test.py

    LIBS
    cairo_run_builtins_test_utils_lib
    cairo_vm_lib
    pip_pytest
)
