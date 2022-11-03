full_python_test(cairo_run_builtins_signature_test
    PREFIX starkware/cairo/lang/builtins/signature
    PYTHON ${PYTHON_COMMAND}
    TESTED_MODULES starkware/cairo/lang/builtins/signature

    FILES
    signature_builtin_runner_test.py

    LIBS
    cairo_run_builtins_test_utils_lib
    cairo_vm_lib
    starkware_python_test_utils_lib
    pip_pytest
)
